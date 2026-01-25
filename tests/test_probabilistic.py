"""Tests for Probabilistic Verification Skipping."""

import pytest

from lloyd.utils.probabilistic import (
    ComplexityDecision,
    SkipDecision,
    calculate_skip_probability,
    get_sampling_rate,
    should_inject_learning,
    should_reassess_complexity,
    should_sample_for_verification,
    should_skip_based_on_history,
    should_skip_verification,
)


class TestSkipDecision:
    """Tests for SkipDecision dataclass."""

    def test_creation(self):
        """Creates decision correctly."""
        decision = SkipDecision(
            should_skip=True,
            reason="High success rate",
            confidence=0.95,
        )

        assert decision.should_skip is True
        assert decision.reason == "High success rate"
        assert decision.confidence == 0.95


class TestComplexityDecision:
    """Tests for ComplexityDecision dataclass."""

    def test_creation(self):
        """Creates decision correctly."""
        decision = ComplexityDecision(
            should_reassess=True,
            reason="Retry count too high",
        )

        assert decision.should_reassess is True
        assert decision.reason == "Retry count too high"


class TestShouldSkipVerification:
    """Tests for should_skip_verification function."""

    def test_never_skips_moderate(self):
        """Never skips MODERATE tasks."""
        decision = should_skip_verification(
            complexity="MODERATE",
            success_rate=0.99,
        )

        assert decision.should_skip is False
        assert "MODERATE" in decision.reason

    def test_never_skips_complex(self):
        """Never skips COMPLEX tasks."""
        decision = should_skip_verification(
            complexity="COMPLEX",
            success_rate=0.99,
        )

        assert decision.should_skip is False
        assert "COMPLEX" in decision.reason

    def test_skips_trivial_high_success(self):
        """Skips TRIVIAL with high success rate."""
        decision = should_skip_verification(
            complexity="TRIVIAL",
            success_rate=0.95,
            threshold=0.85,
        )

        assert decision.should_skip is True
        assert "95%" in decision.reason

    def test_skips_simple_high_success(self):
        """Skips SIMPLE with high success rate."""
        decision = should_skip_verification(
            complexity="SIMPLE",
            success_rate=0.90,
            threshold=0.85,
        )

        assert decision.should_skip is True

    def test_no_skip_low_success(self):
        """Doesn't skip when success rate is low."""
        decision = should_skip_verification(
            complexity="TRIVIAL",
            success_rate=0.70,
            threshold=0.85,
        )

        assert decision.should_skip is False
        assert "below threshold" in decision.reason

    def test_case_insensitive(self):
        """Complexity is case insensitive."""
        decision = should_skip_verification(
            complexity="trivial",
            success_rate=0.95,
        )

        assert decision.should_skip is True

    def test_custom_threshold(self):
        """Respects custom threshold."""
        decision = should_skip_verification(
            complexity="TRIVIAL",
            success_rate=0.75,
            threshold=0.70,
        )

        assert decision.should_skip is True


class TestShouldInjectLearning:
    """Tests for should_inject_learning function."""

    def test_injects_high_confidence(self):
        """Injects when confidence is high."""
        result = should_inject_learning(confidence=0.9, threshold=0.7)
        assert result is True

    def test_skips_low_confidence(self):
        """Skips when confidence is low."""
        result = should_inject_learning(confidence=0.5, threshold=0.7)
        assert result is False

    def test_at_threshold(self):
        """Injects at exactly the threshold."""
        result = should_inject_learning(confidence=0.7, threshold=0.7)
        assert result is True

    def test_custom_threshold(self):
        """Respects custom threshold."""
        result = should_inject_learning(confidence=0.5, threshold=0.4)
        assert result is True


class TestShouldReassessComplexity:
    """Tests for should_reassess_complexity function."""

    def test_always_reassess_on_retry(self):
        """Always reassess when retry count >= 2."""
        decision = should_reassess_complexity(
            complexity="TRIVIAL",
            retry_count=2,
        )

        assert decision.should_reassess is True
        assert "Retry count" in decision.reason

    def test_always_reassess_moderate(self):
        """Always reassess MODERATE tasks."""
        decision = should_reassess_complexity(
            complexity="MODERATE",
            retry_count=0,
        )

        assert decision.should_reassess is True

    def test_always_reassess_complex(self):
        """Always reassess COMPLEX tasks."""
        decision = should_reassess_complexity(
            complexity="COMPLEX",
            retry_count=0,
        )

        assert decision.should_reassess is True

    def test_trivial_probabilistic(self):
        """TRIVIAL uses probabilistic sampling."""
        # Force reassess
        decision = should_reassess_complexity(
            complexity="TRIVIAL",
            retry_count=0,
            _random_func=lambda: 0.1,  # Below 0.2 threshold
        )
        assert decision.should_reassess is True

        # Force skip
        decision = should_reassess_complexity(
            complexity="TRIVIAL",
            retry_count=0,
            _random_func=lambda: 0.5,  # Above 0.2 threshold
        )
        assert decision.should_reassess is False

    def test_simple_probabilistic(self):
        """SIMPLE uses probabilistic sampling."""
        # Force reassess
        decision = should_reassess_complexity(
            complexity="SIMPLE",
            retry_count=0,
            _random_func=lambda: 0.2,  # Below 0.4 threshold
        )
        assert decision.should_reassess is True

        # Force skip
        decision = should_reassess_complexity(
            complexity="SIMPLE",
            retry_count=0,
            _random_func=lambda: 0.6,  # Above 0.4 threshold
        )
        assert decision.should_reassess is False

    def test_case_insensitive(self):
        """Complexity is case insensitive."""
        decision = should_reassess_complexity(
            complexity="complex",
            retry_count=0,
        )
        assert decision.should_reassess is True


class TestCalculateSkipProbability:
    """Tests for calculate_skip_probability function."""

    def test_trivial_high_success(self):
        """TRIVIAL with high success has high skip probability."""
        prob = calculate_skip_probability(
            complexity="TRIVIAL",
            success_rate=1.0,
            retry_count=0,
        )

        assert prob >= 0.7

    def test_complex_never_skips(self):
        """COMPLEX always has 0 probability."""
        prob = calculate_skip_probability(
            complexity="COMPLEX",
            success_rate=1.0,
            retry_count=0,
        )

        assert prob == 0.0

    def test_retry_reduces_probability(self):
        """Retry count reduces skip probability."""
        prob_no_retry = calculate_skip_probability(
            complexity="TRIVIAL",
            success_rate=0.9,
            retry_count=0,
        )
        prob_with_retry = calculate_skip_probability(
            complexity="TRIVIAL",
            success_rate=0.9,
            retry_count=2,
        )

        assert prob_with_retry < prob_no_retry

    def test_low_success_reduces_probability(self):
        """Low success rate reduces probability."""
        prob_high = calculate_skip_probability(
            complexity="TRIVIAL",
            success_rate=1.0,
            retry_count=0,
        )
        prob_low = calculate_skip_probability(
            complexity="TRIVIAL",
            success_rate=0.5,
            retry_count=0,
        )

        assert prob_low < prob_high

    def test_bounded_0_to_1(self):
        """Probability is always between 0 and 1."""
        prob = calculate_skip_probability(
            complexity="TRIVIAL",
            success_rate=2.0,  # Invalid but shouldn't break
            retry_count=0,
        )

        assert 0.0 <= prob <= 1.0


class TestShouldSkipBasedOnHistory:
    """Tests for should_skip_based_on_history function."""

    def test_insufficient_history(self):
        """Returns no-skip when insufficient history."""
        decision = should_skip_based_on_history(
            task_type="coding",
            history=[
                {"task_type": "coding", "success": True},
                {"task_type": "coding", "success": True},
            ],
            min_samples=5,
        )

        assert decision.should_skip is False
        assert "Insufficient history" in decision.reason

    def test_high_success_history(self):
        """Skips with high historical success rate."""
        history = [
            {"task_type": "coding", "success": True}
            for _ in range(10)
        ]

        decision = should_skip_based_on_history(
            task_type="coding",
            history=history,
            min_samples=5,
        )

        assert decision.should_skip is True
        assert "100%" in decision.reason

    def test_low_success_history(self):
        """Doesn't skip with low historical success."""
        history = [
            {"task_type": "coding", "success": i < 5}
            for i in range(10)
        ]

        decision = should_skip_based_on_history(
            task_type="coding",
            history=history,
            min_samples=5,
        )

        assert decision.should_skip is False

    def test_filters_by_task_type(self):
        """Only considers matching task type."""
        history = [
            {"task_type": "coding", "success": True},
            {"task_type": "testing", "success": False},
            {"task_type": "coding", "success": True},
            {"task_type": "testing", "success": False},
            {"task_type": "coding", "success": True},
            {"task_type": "coding", "success": True},
            {"task_type": "coding", "success": True},
        ]

        decision = should_skip_based_on_history(
            task_type="coding",
            history=history,
            min_samples=5,
        )

        assert decision.should_skip is True  # 5/5 = 100% for coding


class TestGetSamplingRate:
    """Tests for get_sampling_rate function."""

    def test_trivial_rate(self):
        """TRIVIAL has 20% sampling rate."""
        rate = get_sampling_rate("TRIVIAL")
        assert rate == 0.2

    def test_simple_rate(self):
        """SIMPLE has 40% sampling rate."""
        rate = get_sampling_rate("SIMPLE")
        assert rate == 0.4

    def test_moderate_rate(self):
        """MODERATE has 80% sampling rate."""
        rate = get_sampling_rate("MODERATE")
        assert rate == 0.8

    def test_complex_rate(self):
        """COMPLEX has 100% sampling rate."""
        rate = get_sampling_rate("COMPLEX")
        assert rate == 1.0

    def test_unknown_defaults_to_1(self):
        """Unknown complexity defaults to 100%."""
        rate = get_sampling_rate("UNKNOWN")
        assert rate == 1.0

    def test_case_insensitive(self):
        """Complexity is case insensitive."""
        rate = get_sampling_rate("trivial")
        assert rate == 0.2


class TestShouldSampleForVerification:
    """Tests for should_sample_for_verification function."""

    def test_complex_always_samples(self):
        """COMPLEX always samples (rate=1.0)."""
        result = should_sample_for_verification(
            complexity="COMPLEX",
            _random_func=lambda: 0.99,
        )
        assert result is True

    def test_trivial_samples_20_percent(self):
        """TRIVIAL samples 20% of the time."""
        # Below rate
        result = should_sample_for_verification(
            complexity="TRIVIAL",
            _random_func=lambda: 0.1,
        )
        assert result is True

        # Above rate
        result = should_sample_for_verification(
            complexity="TRIVIAL",
            _random_func=lambda: 0.5,
        )
        assert result is False

    def test_at_rate_samples(self):
        """At exactly the rate, samples."""
        result = should_sample_for_verification(
            complexity="SIMPLE",
            _random_func=lambda: 0.4,  # Exactly at 0.4 rate
        )
        assert result is True
