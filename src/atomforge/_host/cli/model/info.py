from atomforge._host.cli.model.main import model
import rich_click as click
from rich.console import Console
from rich.panel import Panel
from collections import OrderedDict


def _get_description(model_registration):
    description = model_registration.metadata.description
    if description:
        return description + "\n"
    else:
        return "No description available." + "\n"


def _get_references(model_registration):
    references = model_registration.metadata.references
    if references:
        ref_str = "\n".join(
            f"- [blue]{ref.label}[/blue]: {ref.url}" for ref in references
        )
    else:
        ref_str = "No references available."

    return ref_str + "\n"


def _get_source(model_registration):
    sources = model_registration.source
    if sources:
        return "\n".join(f"- [blue]{source}[/blue]" for source in sources) + "\n"
    else:
        return "No source information available." + "\n"


def _get_accelerators(model_registration):
    accelerators = model_registration.resource_capabilities.accelerator
    if accelerators:
        return "\n".join(f"- [blue]{accel}[/blue]" for accel in accelerators) + "\n"
    else:
        return "No accelerator information available." + "\n"


def _get_parameters(model_registration):
    model_fields = model_registration.model_spec.model_fields
    if model_fields:
        parameters_str = ""
        for key, field in model_fields.items():
            if key in ["kind"]:
                continue  # Skip these fields as they are not user-settable parameters
            type_str = (
                field.annotation.__name__
                if hasattr(field.annotation, "__name__")
                else str(field.annotation)
            )
            default_str = (
                f" (default: {field.default})" if field.default is not None else ""
            )
            parameters_str += (
                f"- [blue]{key}[/blue]: [green]{type_str}[/green]{default_str}\n"
            )
        return parameters_str
    else:
        return "No parameters available."


def _get_dependencies(model_registration):
    dependencies = model_registration.environment_factory.dependency_summary
    if dependencies:
        dep_str = ""
        if dependencies.base_requirements:
            dep_str += "- Base Requirements: "
            for req in dependencies.base_requirements:
                dep_str += f"[blue]{req}[/blue], "

        if dependencies.possible_requirements:
            dep_str += "\n- Possible Requirements: "
            for req in dependencies.possible_requirements:
                dep_str += f"[blue]{req}[/blue], "

        if dependencies.python:
            dep_str += "\n"
            dep_str += f"- Python Version: [blue]{dependencies.python}[/blue]"
        return dep_str + "\n"
    else:
        return "No dependency information available." + "\n"


def get_supported_properties(model_registration):
    properties = model_registration.supported_properties
    if properties:
        return "\n".join(f"- [blue]{prop.value}[/blue]" for prop in properties) + "\n"
    else:
        return "No supported properties information available." + "\n"


def get_basic_info(model_registration):
    metadata = model_registration.metadata
    basic_info = f"Name: [blue]{metadata.name}[/blue]\n"
    basic_info += f"Kind: [blue]{metadata.id}[/blue]\n"
    basic_info += f"Method Family: [blue]{metadata.method_family}[/blue]\n"
    return basic_info


@model.command(
    name="info", help="Show detailed information about a specific model kind."
)
@click.argument("model_kind")
def info_command(model_kind: str):
    from atomforge._runtime.registry.model.model_registry import ModelRegistry

    registry = ModelRegistry.default()
    try:
        handle = registry.get(model_kind)
    except KeyError:
        console = Console()
        console.print(f"[red]Model kind '{model_kind}' not found in registry.[/red]")
        return

    metadata = handle.metadata
    console = Console()

    panel_elements = OrderedDict(
        [
            ("Description", _get_description(handle)),
            ("Basic Info", get_basic_info(handle)),
            ("Supported Properties", get_supported_properties(handle)),
            ("Parameters", _get_parameters(handle)),
            ("Accelerator Options", _get_accelerators(handle)),
            ("References", _get_references(handle)),
            ("Plugin Source", _get_source(handle)),
            ("Dependencies", _get_dependencies(handle)),
        ]
    )

    renderable = "\n".join(
        f"[bold]{key}:[/bold]\n{value}" for key, value in panel_elements.items()
    )

    panel = Panel(title=f"Model Info: {metadata.name}", renderable=renderable)
    console.print(panel)
