"""The arms of esoi's own interfaces reach the modules the records say they build on; nothing here calls a model or the network."""
from esoi import interfaces, scaffold


def project(tmp_path):
    scaffold.init(tmp_path, say=lambda *a, **k: None)
    return str(tmp_path)


def test_apply_esoi_finds_the_records_a_request_concerns_through_spec_search(tmp_path):
    arm = interfaces.DocumentsTemplatesAndTools(interfaces.RuleScript())
    found = arm.find(project(tmp_path), "greeting")
    assert isinstance(found, list) and all(isinstance(key, str) for key in found)


def test_the_harness_reports_stale_rows_per_rule_and_the_public_evidence_it_holds(tmp_path):
    arm = interfaces.ComponentHarness()
    path = project(tmp_path)
    assert all(isinstance(rows, dict) for rows in arm.stale(path).values())
    assert arm.public_evidence(path) >= 0


def test_the_metric_record_arm_reads_the_slice_of_the_index(tmp_path):
    arm = interfaces.LibraryModules()
    assert isinstance(arm.slice_of(project(tmp_path), "greeting"), list)
