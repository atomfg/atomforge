from atomforge.cli.task.main import task_cli
from rich import print
from rich.table import Table

@task_cli.command("list")
def list_command():
    """List all tasks."""
    from atomforge_runtime.registry.task.task_registry import TaskRegistry

    task_registry = TaskRegistry.default()

    table = Table(title="Registered Tasks", show_lines=True)
    table.add_column("Task Name", style="cyan", no_wrap=True)
    table.add_column("Required Properties", style="magenta")
    table.add_column("Optional Properties", style="yellow")
    table.add_column("Plugin Source", style="green")
    table.add_column("Dependencies", style="red")


    none_renderable = "[italic red]None[/]"

    for _, task_handle in task_registry:
        spec_name = task_handle.spec_model.__name__

        capability_spec = task_handle.load_capability_spec()

        if len(capability_spec.optional) == 0:
            optional_properties = none_renderable
        else:
            optional_properties = ", ".join(capability_spec.optional)   

        if len(capability_spec.required) == 0:
            required_properties = none_renderable
        else:
            required_properties = ", ".join(capability_spec.required)

        plugin_source = ", ".join(task_handle.source)


        env_factory = task_handle.load_environment_factory()
        dep_summary = env_factory.dependency_summary
        combined_reqs = list(dep_summary.base_requirements) + list(dep_summary.possible_requirements)
        if len(combined_reqs) == 0:
            dependencies = none_renderable
        else:
            dependencies = ", ".join(combined_reqs)



        table.add_row(spec_name, required_properties, optional_properties, plugin_source, dependencies)

    print(table)

