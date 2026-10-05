"""
Behavioral engine calibration tests — spec.88 (Interview calibration / benchmark answers).

Tests the STAR detection engine against a golden corpus of STRONG / WEAK / PARTIAL answers.
These are fully deterministic (rule-based regex, no LLM) and run in every CI pass.

Each test case specifies:
  - answer text
  - which STAR components must be detected
  - which components must NOT be detected (to catch false positives)
  - expected completeness_score range
"""
import pytest
from backend.app.services.behavioral_engine import detect_star_components, generate_star_feedback


# ── Golden answer corpus ───────────────────────────────────────────────────────

STRONG_STAR_ANSWERS = [
    {
        "id": "strong_001",
        "label": "Complete STAR with quantified result",
        "text": (
            "At my previous company, we were losing 20% of checkout completions due to slow page loads. "
            "My task was to reduce the p99 latency below 500ms. "
            "I decided to implement Redis caching for product lookups and rewrote the SQL queries to use covering indexes. "
            "As a result, we reduced p99 latency by 65% and checkout completions improved by 18% within 2 weeks."
        ),
        "expect_present": ["situation", "task", "action", "result"],
        "expect_absent": [],
        "min_completeness": 1.0,
        "expect_quantified_result": True,
    },
    {
        "id": "strong_002",
        "label": "Leadership example with team context",
        "text": (
            "When I was leading a team of 5 engineers, we needed to migrate a monolith to microservices "
            "before a major product launch. My responsibility was to coordinate the migration without "
            "disrupting the existing service. So I organized daily standups, created a migration runbook, "
            "and we were responsible for deploying each service independently. "
            "This resulted in a 40% reduction in deployment time and zero downtime during the transition."
        ),
        "expect_present": ["situation", "task", "action", "result"],
        "expect_absent": [],
        "min_completeness": 1.0,
        "expect_quantified_result": True,
    },
    {
        "id": "strong_003",
        "label": "Conflict resolution with outcome",
        "text": (
            "During my last project, our team had a conflict with the product manager about sprint priorities. "
            "My task was to align both teams without derailing the timeline. "
            "I decided to schedule a structured meeting, presented data on engineering cost versus business value, "
            "and we reached agreement on a revised priority order. "
            "As a result, we shipped the feature 2 weeks earlier and the PM's key metric improved by 30%."
        ),
        "expect_present": ["situation", "task", "action", "result"],
        "expect_absent": [],
        "min_completeness": 1.0,
        "expect_quantified_result": True,
    },
]

WEAK_STAR_ANSWERS = [
    {
        "id": "weak_001",
        "label": "No concrete result — generic",
        "text": "I worked on a project once and everything went well in the end. The team was happy.",
        "expect_present": [],
        "expect_absent": ["situation", "task", "action", "result"],
        "max_completeness": 0.26,
    },
    {
        "id": "weak_002",
        "label": "Has situation but no action or result",
        "text": (
            "At my previous company, we were dealing with a lot of technical debt. "
            "The situation was really challenging and the context was hard."
        ),
        "expect_present": ["situation"],
        "expect_absent": ["action", "result"],
        "max_completeness": 0.51,
    },
    {
        "id": "weak_003",
        "label": "Action without setup or result",
        "text": "I implemented a caching layer and rewrote the database queries. That was it.",
        "expect_present": ["action"],
        "expect_absent": ["task", "result"],
        "max_completeness": 0.51,
    },
]

PARTIAL_STAR_ANSWERS = [
    {
        "id": "partial_001",
        "label": "Missing task component",
        "text": (
            "When I was at my previous company, we were struggling with slow deployments. "
            "I decided to implement a CI/CD pipeline using GitHub Actions. "
            "As a result, deployment time dropped from 2 hours to 15 minutes."
        ),
        "expect_present": ["situation", "action", "result"],
        "expect_absent": [],
        "min_completeness": 0.5,
        "max_completeness": 0.76,
    },
    {
        "id": "partial_002",
        "label": "Non-quantified result — still counts",
        "text": (
            "During a critical production incident at my last job, "
            "my task was to coordinate the on-call response. "
            "So I paged the database team, implemented a query optimization, "
            "and the outcome was that we restored service."
        ),
        "expect_present": ["situation", "task", "action", "result"],
        "expect_absent": [],
        "min_completeness": 1.0,
        "expect_quantified_result": False,
    },
]


# ── Test helpers ──────────────────────────────────────────────────────────────

def _run_assertion(case: dict) -> None:
    result = detect_star_components(case["text"])

    for component in case.get("expect_present", []):
        assert result[component]["present"], (
            f"[{case['id']}] Expected '{component}' to be DETECTED but was NOT.\n"
            f"Answer: {case['text'][:100]}..."
        )

    for component in case.get("expect_absent", []):
        assert not result[component]["present"], (
            f"[{case['id']}] Expected '{component}' to be ABSENT but was DETECTED.\n"
            f"Answer: {case['text'][:100]}..."
        )

    if "min_completeness" in case:
        assert result["completeness_score"] >= case["min_completeness"], (
            f"[{case['id']}] completeness_score {result['completeness_score']:.2f} < "
            f"expected minimum {case['min_completeness']}"
        )

    if "max_completeness" in case:
        assert result["completeness_score"] <= case["max_completeness"], (
            f"[{case['id']}] completeness_score {result['completeness_score']:.2f} > "
            f"expected maximum {case['max_completeness']}"
        )

    if "expect_quantified_result" in case:
        assert result["result"]["quantified"] == case["expect_quantified_result"], (
            f"[{case['id']}] quantified_result expected={case['expect_quantified_result']}, "
            f"got={result['result']['quantified']}"
        )


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestStrongStarAnswers:
    @pytest.mark.parametrize("case", STRONG_STAR_ANSWERS, ids=[c["id"] for c in STRONG_STAR_ANSWERS])
    def test_strong_answer_detected_correctly(self, case):
        _run_assertion(case)

    def test_strong_answer_completeness_is_1(self):
        for case in STRONG_STAR_ANSWERS:
            result = detect_star_components(case["text"])
            assert result["all_present"], (
                f"[{case['id']}] Strong STAR answer should have all_present=True, "
                f"completeness={result['completeness_score']}"
            )


class TestWeakStarAnswers:
    @pytest.mark.parametrize("case", WEAK_STAR_ANSWERS, ids=[c["id"] for c in WEAK_STAR_ANSWERS])
    def test_weak_answer_not_overcredited(self, case):
        _run_assertion(case)


class TestPartialStarAnswers:
    @pytest.mark.parametrize("case", PARTIAL_STAR_ANSWERS, ids=[c["id"] for c in PARTIAL_STAR_ANSWERS])
    def test_partial_answer_scored_correctly(self, case):
        _run_assertion(case)


class TestStarFeedbackGeneration:
    def test_feedback_for_missing_result_mentions_quantification(self):
        weak_text = "At my previous job, my task was to improve performance. I rewrote the database queries."
        star = detect_star_components(weak_text)
        feedback = generate_star_feedback(star, weak_text)
        # Must give concrete guidance, not empty
        assert len(feedback) > 20, "Feedback should be substantive"
        # Should reference result since it's missing
        assert "result" in feedback.lower() or "outcome" in feedback.lower() or "impact" in feedback.lower()

    def test_feedback_for_complete_star_is_positive(self):
        good_text = (
            "When I was at my previous company, we needed to scale our infrastructure. "
            "My task was to lead the migration to Kubernetes. "
            "I implemented the migration plan over 3 sprints, coordinating with 4 teams. "
            "As a result, deployment frequency improved by 300% and costs reduced by 40%."
        )
        star = detect_star_components(good_text)
        assert star["all_present"], "Setup text should have all STAR components"
        feedback = generate_star_feedback(star, good_text)
        # Should be positive/constructive, not a list of missing items
        assert len(feedback) > 0

    def test_no_false_strong_score_for_empty_answer(self):
        star = detect_star_components("")
        assert star["completeness_score"] == 0.0
        assert not star["all_present"]

    def test_single_word_answer_does_not_crash(self):
        star = detect_star_components("Nothing.")
        assert isinstance(star["completeness_score"], float)
        assert 0.0 <= star["completeness_score"] <= 1.0


class TestCalibrationStatistics:
    """Aggregate statistics to catch evaluator drift over time."""

    def test_strong_answers_average_completeness_above_0_9(self):
        scores = [
            detect_star_components(c["text"])["completeness_score"]
            for c in STRONG_STAR_ANSWERS
        ]
        avg = sum(scores) / len(scores)
        assert avg >= 0.9, (
            f"Strong answers average completeness {avg:.2f} dropped below 0.90. "
            "Check STAR detection regex for regression."
        )

    def test_weak_answers_average_completeness_below_0_5(self):
        scores = [
            detect_star_components(c["text"])["completeness_score"]
            for c in WEAK_STAR_ANSWERS
        ]
        avg = sum(scores) / len(scores)
        assert avg < 0.5, (
            f"Weak answers average completeness {avg:.2f} is unexpectedly high ({avg:.2f} >= 0.50). "
            "Check for false positive STAR detection."
        )
