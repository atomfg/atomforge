import rich_click as click
from pydantic import ValidationError
from rich.console import Console

from atomforge.cli.env._provider import provider_from_settings
from atomforge.env.base.provider import InstallPathNotWritable
from atomforge.cli.env.main import env_cli


def _model_spec(model_registry, argument: str):
    kind, _, profile = argument.partition(":")
    try:
        handle = model_registry.get(kind)
    except KeyError:
        raise click.ClickException(f"Unknown model kind '{kind}'.") from None
    if not profile:
        return handle.model_spec()
    try:
        return handle.model_spec(environment_profile=profile)
    except ValidationError:
        raise click.ClickException(
            f"Model kind '{kind}' has no environment profile '{profile}'."
        ) from None


def _task_environment(task_registry, kind: str):
    """The environment of a task kind, built from a task spec without inputs.
    A task whose environment depends on its inputs cannot be preloaded."""
    try:
        registration = task_registry.get(kind)
    except KeyError:
        raise click.ClickException(f"Unknown task kind '{kind}'.") from None
    spec = registration.spec_model.model_construct()
    try:
        return registration.load_environment_factory()(spec)
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise click.ClickException(
            f"The environment of task '{kind}' depends on the task's inputs, "
            f"so it cannot be preloaded ({error})."
        ) from None


@env_cli.command(
    name="preload",
    help=(
        "Build the worker environments for running TASKs with each MODEL, "
        "in the install path (ATOMFORGE_ENV_INSTALL_PATH). A MODEL is a kind, "
        "optionally with an environment profile: 'orb-v3' or 'orb-v3:latest'. "
        "Environments that already exist are left as they are."
    ),
)
@click.argument("models", nargs=-1, required=True, metavar="MODEL...")
@click.option(
    "--task",
    "tasks",
    multiple=True,
    default=("single_point",),
    show_default=True,
    help="Task kind to build for; repeat for several.",
)
def preload_command(models: tuple[str, ...], tasks: tuple[str, ...]):
    from atomforge.backend.subprocess._environment import setup_environment
    from atomforge_runtime.registry.model.model_registry import ModelRegistry
    from atomforge_runtime.registry.task.task_registry import TaskRegistry

    model_registry = ModelRegistry.default()
    task_registry = TaskRegistry.default()

    # Check every argument before building anything.
    model_specs = [_model_spec(model_registry, argument) for argument in models]
    task_envs = [_task_environment(task_registry, kind) for kind in tasks]

    provider = provider_from_settings(warn_when_building=False)
    console = Console()
    done: set[str] = set()
    for model_spec in model_specs:
        for task_env in task_envs:
            env_spec = setup_environment(
                model_spec=model_spec,
                task_env_spec=task_env,
                model_registry=model_registry,
            )
            key = provider.environment_key(env_spec)
            if key in done:
                continue
            done.add(key)
            existed = any(e.key == key for e in provider.list_environments())
            try:
                handle = provider.ensure_environment(env_spec)
            except InstallPathNotWritable as error:
                raise click.ClickException(str(error)) from None
            status = "present" if existed else "built"
            console.print(
                f"{status:8} {env_spec.name}  {key}  {handle.path}",
                soft_wrap=True,
                highlight=False,
            )
