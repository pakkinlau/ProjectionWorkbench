from scripts.run_f2_w7_b2_mapping_waist_repair import run


def test_rt01_rt13_all_match():
    result = run()
    assert result["case_count"] == 13
    assert result["passed"] == 13
    assert result["failed"] == 0
    assert result["terminal"] == "VIEW_MAPPING_AND_EXCHANGE_WAIST_REPAIR_PASS"
