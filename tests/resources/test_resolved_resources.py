from atomforge_core.resources.resource_models import ResolvedResources, ExecutionResources


def test_resolved_resources_init():
    resources = ResolvedResources(accelerator="gpu", precision="f32")
    assert resources is not None


def test_resolved_resources_attributes():
    # Get the allowed attributes from the ExecutionResources model
    # The set of resources should be the same as ExecutionResources, with the addition of 'messages' and the removal of 'strict'.
    allowed_attributes = list(ExecutionResources.model_fields.keys())
    allowed_attributes.remove(
        "strict"
    )  # Remove 'strict' from the allowed attributes since it's not part of ResolvedResources
    allowed_attributes.append(
        "messages"
    )  # Add 'messages' to the allowed attributes since it's part of ResolvedResources

    # Check that only the allowed attributes are present in the ResolvedResources instance
    for attribute in ResolvedResources.model_fields.keys():
        assert attribute in allowed_attributes, (
            f"Unexpected attribute '{attribute}' found in ResolvedResources"
        )

    # Check that all allowed attributes are present
    for attribute in allowed_attributes:
        assert attribute in ResolvedResources.model_fields.keys(), (
            f"Expected attribute '{attribute}' not found in ResolvedResources"
        )
