__all__ = [
    "ModelRegistration",
    "ModelRegistry",
    "register_lennard_jones",
    "register_chgnet",
    "register_mace",
    "get_default_model_registry",
]


def __getattr__(name: str):
    if name == "ModelRegistration":
        from .registry import ModelRegistration

        return ModelRegistration
    if name == "ModelRegistry":
        from .registry import ModelRegistry

        return ModelRegistry
    if name == "register_lennard_jones":
        from .builtin import register_lennard_jones

        return register_lennard_jones
    if name == "register_chgnet":
        from .builtin import register_chgnet

        return register_chgnet
    if name == "register_mace":
        from .builtin import register_mace

        return register_mace
    if name == "get_default_model_registry":
        from .builtin import get_default_model_registry

        return get_default_model_registry
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
