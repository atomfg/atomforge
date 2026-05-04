import rich_click as click
from rich.console import Console
from rich.table import Table

from atomforge.cli.model.main import model_cli
from enum import Enum


class TableColumn(Enum):
    KIND = "k"
    SUPPORTED_PROPERTIES = "s"
    FAMILY = "f"
    ACCELERATOR = "a"
    DEPENDENCIES = "d"
    PLUGIN_SOURCE = "p"


class TableWriter:
    def __init__(self, columns: str, *, strict: bool = False):
        self.strict = strict
        self.columns = self._parse_columns(columns)
        self.table = self._setup_table()

    def _parse_columns(self, columns: str) -> list[TableColumn]:
        column_converter = {
            TableColumn.SUPPORTED_PROPERTIES.value: "supported_properties",
            TableColumn.FAMILY.value: "family",
            TableColumn.ACCELERATOR.value: "accelerator",
            TableColumn.DEPENDENCIES.value: "dependencies",
            TableColumn.PLUGIN_SOURCE.value: "plugin_source",
        }

        if columns == "all":
            columns = [column.value for column in TableColumn]
        else:
            chars = columns
            for c in chars:
                if c not in column_converter:
                    raise ValueError(
                        f"Invalid column identifier '{c}'. Valid identifiers are: {', '.join(column_converter.keys())}"
                    )
            columns = [
                column.value for column in TableColumn if column.value in columns
            ]
            columns = [
                TableColumn.KIND.value
            ] + columns  # Ensure 'kind' is always included

        return columns

    def _setup_table(self):
        table = Table(title="Atomforge Models", show_lines=True)
        table.add_column("Kind", style="cyan", no_wrap=True)
        if self.strict:
            table.add_column("Strict", style="white")

        if TableColumn.SUPPORTED_PROPERTIES.value in self.columns:
            table.add_column("Supported Properties", style="magenta")
        if TableColumn.FAMILY.value in self.columns:
            table.add_column("Family", style="green")
        if TableColumn.ACCELERATOR.value in self.columns:
            table.add_column("Accelerator", style="yellow")
        if TableColumn.DEPENDENCIES.value in self.columns:
            table.add_column("Dependencies", style="red")
        if TableColumn.PLUGIN_SOURCE.value in self.columns:
            table.add_column("Plugin Source", style="blue")

        return table

    def _kind_to_str(self, kind):
        return kind

    def _supported_properties_to_str(self, model_registration):
        properties = model_registration.load_supported_properties()
        if properties:
            return ", ".join(p.value for p in properties)
        else:
            return "N/A"

    def _family_to_str(self, model_registration):
        method_family = model_registration.load_metadata().method_family
        return method_family if method_family else "N/A"

    def _accelerator_to_str(self, model_registration):
        accelerators = model_registration.load_resource_capabilities().accelerator
        return ", ".join(accelerators) if accelerators else "N/A"

    def _dependencies_to_str(self, model_registration):
        dependencies = model_registration.load_environment_factory().dependency_summary
        dep_str = (
            ", ".join(dependencies.base_requirements)
            if dependencies and dependencies.base_requirements
            else "N/A"
        )
        return dep_str

    def _plugin_source_to_str(self, model_registration):
        sources = model_registration.source
        return ", ".join(sources) if sources else "N/A"

    def _failed_value_for_column(self, column, model_registration):
        if column == TableColumn.PLUGIN_SOURCE.value:
            return self._plugin_source_to_str(model_registration)
        return "N/A"

    def _strict_status_to_str(self, strict_result):
        if strict_result is None:
            return ""

        is_valid, message = strict_result
        if is_valid:
            return "[green]PASS[/green]"

        return f"[red]FAIL[/red]: {message}"

    def add_row(self, kind, model_registration, strict_result=None):
        row = [self._kind_to_str(kind)]
        if self.strict:
            row.append(self._strict_status_to_str(strict_result))

        strict_failed = strict_result is not None and not strict_result[0]
        for column in self.columns:
            match column:
                case TableColumn.KIND.value:
                    continue
                case TableColumn.SUPPORTED_PROPERTIES.value:
                    if strict_failed:
                        row.append(self._failed_value_for_column(column, model_registration))
                        continue
                    row.append(self._supported_properties_to_str(model_registration))
                case TableColumn.FAMILY.value:
                    if strict_failed:
                        row.append(self._failed_value_for_column(column, model_registration))
                        continue
                    row.append(self._family_to_str(model_registration))
                case TableColumn.ACCELERATOR.value:
                    if strict_failed:
                        row.append(self._failed_value_for_column(column, model_registration))
                        continue
                    row.append(self._accelerator_to_str(model_registration))
                case TableColumn.DEPENDENCIES.value:
                    if strict_failed:
                        row.append(self._failed_value_for_column(column, model_registration))
                        continue
                    row.append(self._dependencies_to_str(model_registration))
                case TableColumn.PLUGIN_SOURCE.value:
                    row.append(self._failed_value_for_column(column, model_registration))

        self.table.add_row(*row)


@model_cli.command(
    name="list",
    help="List all registered models with optional filtering and column selection.",
)
@click.option(
    "--columns",
    "-c",
    type=str,
    required=False,
    default="all",
    help="Columns to display (k=kind, s=supported properties, f=family, a=accelerator, d=dependencies, p=plugin source). Use 'all' to display all columns.",
)
@click.option(
    "--family", "-f", type=str, required=False, help="Filter models by method family."
)
@click.option(
    "--strict",
    is_flag=True,
    help="Load the model registry in strict mode and validate all lazy fields.",
)
def list_command(columns: str, family: str, strict: bool):
    from atomforge_runtime.registry.model.model_registry import ModelRegistry

    console = Console()
    registry = ModelRegistry.default()
    table_writer = TableWriter(columns, strict=strict)

    for kind, handle in registry:
        strict_result = None
        if strict:
            try:
                handle.validate_strict()
                strict_result = (True, "")
            except Exception as exc:
                strict_result = (False, str(exc))

        if family:
            try:
                if handle.load_metadata().method_family != family:
                    continue
            except Exception:
                if not strict:
                    raise

        if strict_result is not None and not strict_result[0]:
            table_writer.add_row(kind, handle, strict_result=strict_result)
            continue
        table_writer.add_row(kind, handle, strict_result=strict_result)
    console.print(table_writer.table)
