from scripts.run_f2_w6_b2_privacy_requalification import run


def test_rt01_rt20_all_pass():
    result = run()
    assert result["test_count"] == 20
    assert result["pass_count"] == 20
    assert result["finding_count"] == 0
    assert result["terminal"] == "QUALIFIED_AT_CONTROLLED_LOCAL_CEILING"
