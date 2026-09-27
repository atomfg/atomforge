from typing import Literal

from atomforge_core.model.spec import ModelSpec
from atomforge_core.protocol.session import model_session_key
from atomforge_core.resources.resource_models import ExecutionResources


class ProfiledModel(ModelSpec):
    kind: Literal["profiled"] = "profiled"
    environment_profile: Literal["tested", "latest"] = "tested"
    parameter: float = 1.0


def test_environment_profile_is_serialized_but_not_scientific():
    model = ProfiledModel(environment_profile="latest")

    assert model.model_dump()["environment_profile"] == "latest"
    assert "environment_profile" not in model.scientific_payload()


def test_environment_profile_does_not_change_model_session_identity():
    resources = ExecutionResources(accelerator="cpu", precision="f32")
    tested = ProfiledModel(environment_profile="tested")
    latest = ProfiledModel(environment_profile="latest")

    assert model_session_key(tested, resources) == model_session_key(latest, resources)


def test_scientific_setting_changes_model_session_identity():
    resources = ExecutionResources(accelerator="cpu", precision="f32")
    first = ProfiledModel(parameter=1.0)
    second = ProfiledModel(parameter=2.0)

    assert model_session_key(first, resources) != model_session_key(second, resources)
