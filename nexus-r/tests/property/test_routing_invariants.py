from __future__ import annotations

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck

from nexus_r.events import IntentResult, PermissionTier


class TestIntentResultInvariants:
    @given(
        raw=st.text(min_size=1, max_size=1000),
        normalized=st.text(min_size=1, max_size=1000),
        task_type=st.sampled_from([
            "general_llm", "code", "analysis", "creative", "vision"
        ]),
        complexity=st.floats(min_value=0.0, max_value=1.0),
        confidence=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_intent_result_accepts_valid_parameters(
        self,
        raw: str,
        normalized: str,
        task_type: str,
        complexity: float,
        confidence: float,
    ) -> None:
        intent = IntentResult(
            raw_input=raw,
            normalized_input=normalized,
            task_type=task_type,
            complexity=complexity,
            confidence=confidence,
            parameters={},
            suggested_tier=PermissionTier.T3,
        )
        assert intent.complexity == complexity
        assert 0.0 <= intent.complexity <= 1.0
        assert 0.0 <= intent.confidence <= 1.0

    @given(
        complexity=st.floats(min_value=0.0, max_value=1.0),
    )
    def test_complexity_always_within_bounds(self, complexity: float) -> None:
        assert 0.0 <= complexity <= 1.0


class TestPermissionTierOrdering:
    def test_tier_ordering_is_strict(self) -> None:
        assert PermissionTier.T1 < PermissionTier.T2
        assert PermissionTier.T2 < PermissionTier.T3
        assert PermissionTier.T3 < PermissionTier.T4
        assert PermissionTier.T4 < PermissionTier.T5

    @given(
        tier_val=st.integers(min_value=1, max_value=5),
    )
    def test_tier_from_int_roundtrip(self, tier_val: int) -> None:
        tier = PermissionTier(tier_val)
        assert tier.value == tier_val


class TestRoutingInvariants:
    @given(
        st.lists(
            st.tuples(
                st.floats(min_value=0.0, max_value=1.0),
                st.sampled_from(list(PermissionTier)),
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=50)
    def test_higher_complexity_never_maps_to_lower_tier(
        self, cases: list[tuple[float, PermissionTier]],
    ) -> None:
        sorted_cases = sorted(cases, key=lambda x: x[0])
        for i in range(len(sorted_cases) - 1):
            complexity_a, tier_a = sorted_cases[i]
            complexity_b, tier_b = sorted_cases[i + 1]
            if complexity_b > complexity_a:
                assert tier_b.value >= tier_a.value - 1
