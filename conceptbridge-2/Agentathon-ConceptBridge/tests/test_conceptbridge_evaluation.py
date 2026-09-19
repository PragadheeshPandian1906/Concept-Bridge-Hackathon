from demo.conceptbridge.evaluation import evaluate_outcome


def test_effective_and_ineffective_gain():
    effective = evaluate_outcome("m", [("a", "SQL", .35, .75)])
    ineffective = evaluate_outcome("m", [("a", "SQL", .35, .38)])
    assert effective.outcomes[0].gain == .4
    assert effective.effective is True
    assert ineffective.outcomes[0].gain == .03
    assert ineffective.effective is False