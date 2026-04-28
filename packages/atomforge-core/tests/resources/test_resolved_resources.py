from atomforge_core.resources.resource_models import ExecutionResources, ResolvedResources


def test_resolved_resources_init():
    resources = ResolvedResources(accelerator="gpu", precision="f32")
    assert resources is not None


def test_resolved_resources_attributes():
    allowed_attributes = list(ExecutionResources.model_fields.keys())
    allowed_attributes.remove("strict")
    allowed_attributes.append("messages")

    for attribute in ResolvedResources.model_fields.keys():
        assert attribute in allowed_attributes, (
            f"Unexpected attribute '{attribute}' found in ResolvedResources"
        )

    for attribute in allowed_attributes:
        assert attribute in ResolvedResources.model_fields.keys(), (
            f"Expected attribute '{attribute}' not found in ResolvedResources"
        )

