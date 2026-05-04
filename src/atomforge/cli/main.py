import rich_click as click
from atomforge.cli.model import model_cli
from atomforge.cli.plugin import plugin_cli
from atomforge.cli.task import task_cli


@click.group(name="atomforge")
def main():
    pass


main.add_command(model_cli)
main.add_command(task_cli)
main.add_command(plugin_cli)
