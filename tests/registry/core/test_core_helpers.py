from atomforge.env.base.env import EnvironmentSpec
from atomforge.registry.core.helpers import (
    load_symbol,
    normalize_distribution_name,
    resolve_distribution,
    wrap_environment_factory,
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


def test_wrap_environment_factory_adds_provider_requirement():
    def environment_factory(_spec):
        return EnvironmentSpec(name="test", requirements=("ase",))

    wrapped = wrap_environment_factory(environment_factory, ["atomforge==0.1.0"])
    env_spec = wrapped(object())

    assert env_spec.provider_requirements == ("atomforge==0.1.0",)


def test_load_symbol_loads_existing_symbol():
    symbol = load_symbol("atomforge.registry.task.manifest:TaskManifest")

    assert symbol.__name__ == "TaskManifest"
