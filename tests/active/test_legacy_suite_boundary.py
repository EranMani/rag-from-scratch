from pathlib import Path


def test_legacy_gate_tests_remain_outside_active_pytest_path():
    root_tests = Path("tests")

    assert (root_tests / "test_assess_node.py").exists()
    assert (root_tests / "active").exists()
