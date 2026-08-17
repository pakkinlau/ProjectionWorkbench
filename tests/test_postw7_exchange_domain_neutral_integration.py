from scripts.run_f2_w8_b2_postw7_integration import run


def test_postw7_repairs_coexist_with_compatibility_model():
    result = run()
    assert result["passed"]
    assert result["terminal"] == "POST_W7_EXCHANGE_DOMAIN_NEUTRAL_INTEGRATION_PASS"
    assert all(result["checks"].values())
