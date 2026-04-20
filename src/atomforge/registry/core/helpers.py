import json
import re
from importlib import import_module
from importlib.metadata import distribution


def normalize_distribution_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def resolve_distribution(name: str) -> str:
    dist = distribution(name)
    text = dist.read_text("direct_url.json")
    if text is not None:
        data = json.loads(text)
        editable = data.get("dir_info", {}).get("editable", False)
        url = data.get("url")
    else:
        editable = False
        url = None

    if editable:
        return f"{name} @ {url}"
    return f"{dist.metadata['Name']}=={dist.version}"


def wrap_environment_factory(factory, provider_requirements: list[str]):
    def wrapped(spec):
        env = factory(spec)
        return env.with_provider_requirement(provider_requirements)

    return wrapped


def load_symbol(dotted_path: str):
    module_name, symbol_name = dotted_path.split(":", 1)
    module = import_module(module_name)
    return getattr(module, symbol_name)
