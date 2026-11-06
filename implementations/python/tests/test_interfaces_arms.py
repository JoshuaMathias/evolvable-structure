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


def test_apply_esoi_contract_the_two_arms_agree_on_understanding(tmp_path):
    from esoi.apply_esoi import ApplyingEsoi, DocumentsOnly, ThroughTheFourContainers
    import esoi
    path = project(tmp_path)
    full, hand = esoi.run("apply-esoi", path), esoi.run("apply-esoi", path, arms={"apply-esoi": "documents-only"})
    assert ThroughTheFourContainers.review is not DocumentsOnly.review and ApplyingEsoi is not None
    assert list(hand) == ["understanding"] and hand["understanding"] == full["understanding"]


def test_the_standard_contract_every_arm_describes_the_project_in_counts(tmp_path):
    from esoi.understanding.the_standard.interface import DocumentationFolder, StandardDocument, TheStandard
    path = project(tmp_path)
    for arm in (StandardDocument(), DocumentationFolder()):
        assert isinstance(arm, TheStandard)
        counts = arm.describe(path)
        assert counts and all(isinstance(n, int) and n >= 0 for n in counts.values())
