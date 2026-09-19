from demo.conceptbridge.evaluation import evaluate_outcome
from demo.conceptbridge.profiling import build_profiles


def test_student_instruction_is_data_not_control():
    profiles = build_profiles("demo/conceptbridge/data/quiz.csv", "demo/conceptbridge/data/question_concepts.csv")
    ananya = next(profile for profile in profiles if profile.student_id == "ananya")
    assert all(item.score <= 1 for item in ananya.concepts)
    assert evaluate_outcome("m", [("ananya", "SQL Joins", .35, .38)]).effective is False