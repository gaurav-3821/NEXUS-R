from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("nexus-r.behavior")


class BehaviorTracker:
    """Probabilistic behavioral inference engine.
    
    Captures user interaction signals and uses weighted scoring
    to infer preferences with confidence values, replacing
    brittle hard-threshold boolean heuristics.
    """

    MINIMUM_DATA_POINTS = 3
    MINIMUM_CONFIDENCE = 0.4

    def __init__(self, identity_store) -> None:
        self.identity_store = identity_store
        self._session_start = time.time()
        self._data_point_count = 0
        self.session_signals: dict[str, Any] = {
            "time_on_answer": 0.0,
            "scroll_events": 0,
            "scroll_depth_max": 0.0,
            "follow_up_types": [],
            "copied_text": [],
            "interrupted": 0,
            "regenerated": 0,
            "follow_up_latency_ms": [],
            "expand_collapse": 0,
            "messages_sent": 0,
        }
        self._confidence_accumulator: dict[str, list[float]] = {}

    def record_signal(self, signal_type: str, value: Any) -> None:
        """Record a frontend behavioral signal."""
        self._data_point_count += 1

        if signal_type == "time_on_answer":
            self.session_signals["time_on_answer"] += float(value or 0)
        elif signal_type == "scroll_event":
            self.session_signals["scroll_events"] += 1
        elif signal_type == "scroll_depth":
            depth = float(value or 0)
            if depth > self.session_signals["scroll_depth_max"]:
                self.session_signals["scroll_depth_max"] = depth
        elif signal_type == "follow_up":
            self.session_signals["follow_up_types"].append(str(value))
        elif signal_type == "copy":
            self.session_signals["copied_text"].append(str(value))
        elif signal_type == "interrupted":
            self.session_signals["interrupted"] += 1
        elif signal_type == "regenerated":
            self.session_signals["regenerated"] += 1
        elif signal_type == "follow_up_latency":
            self.session_signals["follow_up_latency_ms"].append(float(value or 0))
        elif signal_type == "expand_collapse":
            self.session_signals["expand_collapse"] += 1
        elif signal_type == "message_sent":
            self.session_signals["messages_sent"] += 1
        else:
            logger.debug("Unknown signal type: %s", signal_type)
            return

        if self._data_point_count >= self.MINIMUM_DATA_POINTS:
            self._analyze_and_infer()

    def _compute_inference_scores(self) -> dict[str, float]:
        """Compute weighted probabilistic inference scores.
        
        Returns dict of preference keys → confidence scores [0.0, 1.0].
        """
        scores: dict[str, float] = {}
        s = self.session_signals

        # --- Confusion score ---
        scroll_norm = min(s["scroll_events"] / 15.0, 1.0)
        dwell_norm = min(s["time_on_answer"] / 300.0, 1.0)
        interrupt_factor = min(s["interrupted"] / 3.0, 1.0)
        regen_factor = min(s["regenerated"] / 2.0, 1.0)
        scores["confusion"] = (
            0.25 * scroll_norm
            + 0.30 * dwell_norm
            + 0.25 * interrupt_factor
            + 0.20 * regen_factor
        )

        # --- Technical depth preference ---
        code_copies = len([
            c for c in s["copied_text"]
            if any(kw in c for kw in ["def ", "class ", "import ", "function", "=", "{", "("])
        ])
        why_count = sum(
            1 for f in s["follow_up_types"]
            if "why" in str(f).lower() or "how" in str(f).lower()
        )
        scores["technical_depth"] = min(
            code_copies * 0.20 + why_count * 0.15, 1.0
        )

        # --- Conciseness preference ---
        formula_copies = len([
            c for c in s["copied_text"]
            if any(ch in str(c) for ch in ["=", "+", "*", "^", "∫", "Σ"])
        ])
        scores["conciseness"] = min(formula_copies * 0.25, 1.0)

        # --- Engagement (positive signal) ---
        moderate_dwell = 1.0 if 30 < s["time_on_answer"] < 180 else 0.3
        low_scroll = 1.0 if s["scroll_events"] < 5 else 0.4
        expand_bonus = min(s["expand_collapse"] * 0.15, 0.3)
        scores["engagement"] = (
            0.40 * moderate_dwell + 0.40 * low_scroll + 0.20 * expand_bonus
        )

        # --- Impatience ---
        latencies = s["follow_up_latency_ms"]
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            fast_followup = 1.0 if avg_latency < 5000 else max(0.0, 1.0 - avg_latency / 30000)
        else:
            fast_followup = 0.0
        scores["impatience"] = (
            0.40 * fast_followup
            + 0.35 * interrupt_factor
            + 0.25 * regen_factor
        )

        return scores

    def _analyze_and_infer(self) -> None:
        """Analyze signals and commit high-confidence inferences."""
        scores = self._compute_inference_scores()

        # Accumulate scores for running average
        for key, score in scores.items():
            if key not in self._confidence_accumulator:
                self._confidence_accumulator[key] = []
            self._confidence_accumulator[key].append(score)

        inference_map = {
            "confusion": (
                "complexity",
                "simplify explanations — user shows signs of difficulty processing detailed content",
            ),
            "technical_depth": (
                "depth",
                "provide deep technical derivations and explanations automatically",
            ),
            "conciseness": (
                "style",
                "concise, formula-heavy responses — skip conversational filler",
            ),
            "impatience": (
                "brevity",
                "keep responses shorter and more direct — user prefers quick answers",
            ),
        }

        for score_key, (pref_key, pref_value) in inference_map.items():
            accumulated = self._confidence_accumulator.get(score_key, [])
            if len(accumulated) < 2:
                continue

            avg_confidence = sum(accumulated[-5:]) / len(accumulated[-5:])

            if avg_confidence >= self.MINIMUM_CONFIDENCE:
                try:
                    self.identity_store.add_inferred_preference(
                        pref_key, pref_value, avg_confidence
                    )
                    logger.info(
                        "Inferred preference '%s' with confidence %.2f",
                        pref_key, avg_confidence,
                    )
                except Exception as e:
                    logger.error("Failed to save inferred preference: %s", e)

    def get_session_summary(self) -> dict[str, Any]:
        """Return current session signals and computed inference scores."""
        scores = self._compute_inference_scores()
        elapsed = time.time() - self._session_start
        return {
            "session_duration_s": round(elapsed, 1),
            "data_points": self._data_point_count,
            "signals": dict(self.session_signals),
            "inference_scores": {k: round(v, 3) for k, v in scores.items()},
            "accumulated_samples": {
                k: len(v) for k, v in self._confidence_accumulator.items()
            },
        }
