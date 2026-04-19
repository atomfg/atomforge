from rich import print
from importlib.metadata import entry_points

eps = entry_points(group="atomforge", name="tasks")

for ep in eps:
    print(f"Loading entry point: {ep.name} -> {ep.value}")
    manifest = ep.load()
    print(manifest)