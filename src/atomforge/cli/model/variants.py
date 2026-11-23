import rich_click as click
from rich.console import Console
from rich.table import Table

from atomforge.cli.model.main import model_cli


def _info_cells(variant_info, spec) -> list[str]:
    if variant_info is None:
        return []
    info = variant_info(spec)
    return [
        ", ".join(info.training_data) or "",
        info.level_of_theory or "",
        info.description or "",
    ]


@model_cli.command(
    name="variants",
    help="List the variants (trained models) of a model kind, by variant id.",
)
@click.argument("model_kind")
def variants_command(model_kind: str):
    from atomforge_runtime.registry.model.model_registry import ModelRegistry

    console = Console()
    registry = ModelRegistry.default()
    try:
        handle = registry.get(model_kind)
    except KeyError:
        console.print(f"[red]Model kind '{model_kind}' not found in registry.[/red]")
        return

    variant_info = handle.load_variant_info()
    table = Table(title=f"Variants of {model_kind}", show_lines=False)
    table.add_column("Variant id", style="cyan", no_wrap=True)
    table.add_column("Default", justify="center")
    if variant_info is not None:
        table.add_column("Training data", style="green")
        table.add_column("Level of theory", style="magenta")
        table.add_column("Description")

    try:
        default_name = handle.model_spec().variant_name
    except Exception:  # noqa: BLE001 - a spec with required fields has no default
        default_name = None
    for spec in handle.model_spec.variants():
        is_default = "*" if spec.variant_name == default_name else ""
        table.add_row(spec.variant_id, is_default, *_info_cells(variant_info, spec))

    console.print(table)
    if handle.model_spec.accepts_local_weights():
        console.print(
            f"{model_kind} also loads local weights: "
            "set weights=LocalWeights(path) on the spec."
        )
