import json

from scripts.run_f2_w9_b2_independent_postw7_qualification import run


def test_independent_postw7_candidate_qualification_passes():
    result = run()
    assert result["passed"] is True, json.dumps(result, indent=2, sort_keys=True)
    assert result["terminal"] == "POST_W7_INTEGRATED_CANDIDATE_INDEPENDENTLY_QUALIFIED"
    assert all(result["checks"].values())
    assert result["integrated_witness"]["passed"] is True
    assert result["hosted_dependency_check"]["pass"] is True
