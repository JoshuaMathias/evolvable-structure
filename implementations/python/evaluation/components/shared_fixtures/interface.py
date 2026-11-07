"""The one way into the shared fixtures of the evaluation components: small synthetic repositories, libraries and model arms the components build on.

The harness puts the evaluation folder on the import path, so a component writes ``from shared_fixtures.interface import repo_fixture``. Importing this module runs nothing."""
from shared_fixtures import (assemble_fixture, consumer_fixture, glance_fixture, harness_fixture, index_world, metric_record_fixture, model_arms, navigable_fixture, repo_fixture, staleness_fixture, structure_fixture, tracker_fixture, verdict_score)  # noqa: F401  (re-exported: the evaluation components use the fixtures through this interface)

__all__ = ["assemble_fixture", "consumer_fixture", "glance_fixture", "harness_fixture", "index_world", "metric_record_fixture", "model_arms", "navigable_fixture", "repo_fixture", "staleness_fixture", "structure_fixture", "tracker_fixture", "verdict_score"]
