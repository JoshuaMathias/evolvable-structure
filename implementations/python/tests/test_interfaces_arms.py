"""The arms of esoi's own interfaces reach the modules the records say they build on; nothing here calls a model or the network."""
from esoi.optimization.keep_metric_record.interface import LibraryModules
from esoi.optimization.measurement_harness.interface import ComponentHarness
from esoi.understanding.the_standard import scaffold


def project(tmp_path):
    scaffold.init(tmp_path, say=lambda *a, **k: None)
    return str(tmp_path)


def test_apply_esoi_reports_every_container_in_order(tmp_path):
    import esoi
    report = esoi.run("apply-esoi", project(tmp_path))
    assert list(report) == ["understanding", "structure", "optimization", "runtime"]
    assert report["structure"]["structure-check"]["problems"] >= 0


def test_the_harness_reports_stale_rows_per_rule_and_the_public_evidence_it_holds(tmp_path):
    arm = ComponentHarness()
    path = project(tmp_path)
    assert all(isinstance(rows, dict) for rows in arm.stale(path).values())
    assert arm.public_evidence(path) >= 0


def test_the_metric_record_arm_reads_the_slice_of_the_index(tmp_path):
    arm = LibraryModules()
    assert isinstance(arm.slice_of(project(tmp_path), "greeting"), list)
