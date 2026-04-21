import rich_click as click
from rich.console import Console
from rich.table import Table

from atomforge.cli.model.main import model
from enum import Enum


class TableColumn(Enum):
    KIND = "k"
    SUPPORTED_PROPERTIES = "s"
    FAMILY = "f"
    ACCELERATOR = "a"
    DEPENDENCIES = "d"
    PLUGIN_SOURCE = "p"


class TableWriter:
    def __init__(self, columns: str):
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
            columns = [column.value for column in TableColumn if column.value in columns]
            columns = [TableColumn.KIND.value] + columns  # Ensure 'kind' is always included

        return columns

    def _setup_table(self):
        table = Table(title="Atomforge Models")
        table.add_column("Kind", style="cyan", no_wrap=True)

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
        properties = model_registration.supported_properties
        if properties:
            return ", ".join(p.value for p in properties)
        else:
            return "N/A"
        
    def _family_to_str(self, model_registration):
        method_family = model_registration.metadata.method_family
        return method_family if method_family else "N/A"
    
    def _accelerator_to_str(self, model_registration):
        accelerators = model_registration.resource_capabilities.accelerator
        return ", ".join(accelerators) if accelerators else "N/A"
    
    def _dependencies_to_str(self, model_registration):
        dependencies = model_registration.environment_factory.dependency_summary
        dep_str = (
            ", ".join(dependencies.base_requirements)
            if dependencies and dependencies.base_requirements
            else "N/A"
        )
        return dep_str

    def _plugin_source_to_str(self, model_registration):
        sources = model_registration.source
        return ", ".join(sources) if sources else "N/A"

    def add_row(self, kind, model_registration):
        row = []
        for column in self.columns:
            match column:
                case TableColumn.KIND.value:
                    row.append(self._kind_to_str(kind))
                case TableColumn.SUPPORTED_PROPERTIES.value:
                    row.append(self._supported_properties_to_str(model_registration))
                case TableColumn.FAMILY.value:
                    row.append(self._family_to_str(model_registration))
                case TableColumn.ACCELERATOR.value:
                    row.append(self._accelerator_to_str(model_registration))
                case TableColumn.DEPENDENCIES.value:
                    row.append(self._dependencies_to_str(model_registration))
                case TableColumn.PLUGIN_SOURCE.value:
                    row.append(self._plugin_source_to_str(model_registration))

        self.table.add_row(*row)



@model.command(name="list")
@click.option("--columns", "-c", type=str, required=False, default="all", help="Columns to display (k=kind, s=supported properties, f=family, a=accelerator, d=dependencies, p=plugin source). Use 'all' to display all columns.")
@click.option("--family", "-f", type=str, required=False, help="Filter models by method family.")
def list_command(columns: str, family: str):
    from atomforge.registry.model.registry import ModelRegistry


    registry = ModelRegistry.default()
    console = Console()

    table_writer = TableWriter(columns)

    for kind, handle in registry:
        if family and handle.metadata.method_family != family:
            continue
        table_writer.add_row(kind, handle)
    console.print(table_writer.table)
