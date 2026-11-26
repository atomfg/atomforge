from rich.console import Console
from rich.table import Table

from atomforge.cli.env._provider import provider_from_settings
from atomforge.cli.env.main import env_cli


@env_cli.command(
    name="list",
    help=(
        "List the worker environments in the search paths. Environments in "
        "preloaded search paths (other than the install path) are read-only."
    ),
)
def list_command():
    provider = provider_from_settings()
    table = Table(title="Worker environments")
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Name", no_wrap=True)
    table.add_column("Access", no_wrap=True)
    table.add_column("Path", no_wrap=True)
    for environment in provider.list_environments():
        table.add_row(
            environment.key,
            environment.name or "",
            "read-only" if environment.read_only else "writable",
            str(environment.path),
        )
    Console().print(table)
