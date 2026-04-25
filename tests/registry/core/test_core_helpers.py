from atomforge_runtime.registry.helpers import (
    load_symbol,
    normalize_distribution_name,
    resolve_distribution,
)


def test_normalize_distribution_name_equivalence():
    assert normalize_distribution_name("my-plugin") == "my-plugin"
    assert normalize_distribution_name("my_plugin") == "my-plugin"
    assert normalize_distribution_name("my.plugin") == "my-plugin"
    assert normalize_distribution_name("My.Plugin_Name") == "my-plugin-name"


def test_resolve_distribution_returns_install_requirement():
    requirement = resolve_distribution("atomforge")

    assert isinstance(requirement, str)
    assert requirement.startswith("atomforge")


def test_load_symbol_loads_existing_symbol():
    symbol = load_symbol("atomforge_core.registry.task_manifest:TaskManifest")

    assert symbol.__name__ == "TaskManifest"
