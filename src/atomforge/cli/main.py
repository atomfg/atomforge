import rich_click as click
from atomforge.cli.model import model

@click.group(name="atomforge")
def main():
    pass

main.add_command(model)