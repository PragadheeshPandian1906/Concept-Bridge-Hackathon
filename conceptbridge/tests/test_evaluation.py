from tests.test_matching import make_system


def test_ineffective_session_causes_rematch(tmp_path):
    system=make_system(tmp_path); result=system.run_matching(); approved=system.approve(result["candidates"][0]["id"],"reviewer",45)
    evaluation=system.start_evaluation(approved["session"]["id"])
    concept=evaluation["questions"][0]["concept_id"]
    submitted=system.submit_evaluation(evaluation["id"],{concept:0.21})
    assert submitted["result"]["effective"] is False
    assert submitted["rematch"]["current_state"] == "WAITING_FOR_HUMAN_REVIEW"


def test_submit_all_evaluations_finishes_batch_and_rematches(tmp_path):
    system=make_system(tmp_path); system.settings.max_group_size=2
    run=system.run_matching(); batch=system.approve_all(run["id"],"reviewer",30)
    completed=system.complete_all_sessions(run["id"])
    submissions=[]
    for evaluation in completed["evaluations"]:
        submissions.append({"evaluation_id":evaluation["id"],"post_scores":{question["concept_id"]:0.0 for question in evaluation["questions"]}})
    result=system.submit_all_evaluations(run["id"],submissions)
    assert result["submitted_evaluation_count"] == len(submissions)
    assert result["rematch"]["current_state"] == "WAITING_FOR_HUMAN_REVIEW"
