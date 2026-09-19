from demo.conceptbridge.matching import find_candidates
from demo.conceptbridge.schema import ConceptScore, StudentProfile


def profile(student_id, values):
    return StudentProfile(student_id=student_id, student_name=student_id, concepts=[ConceptScore(concept=k, score=v) for k, v in values.items()])


def test_reciprocal_pair_and_non_reciprocal_pair():
    a = profile("a", {"Recursion": .9, "SQL": .3})
    b = profile("b", {"Recursion": .4, "SQL": .9})
    assert find_candidates([a, b]).items[0].a_teaches == ["Recursion"]
    assert find_candidates([a, b]).items[0].b_teaches == ["SQL"]
    assert find_candidates([profile("x", {"A": .9, "B": .9}), profile("y", {"A": .8, "B": .8})]).items == []


def test_rejected_match_is_excluded():
    a = profile("a", {"A": .9, "B": .3, "C": .3})
    b = profile("b", {"A": .3, "B": .9, "C": .3})
    c = profile("c", {"A": .3, "B": .3, "C": .9})
    candidates = find_candidates([a, b, c], {"a-b"})
    assert all(item.match_id != "a-b" for item in candidates.items)