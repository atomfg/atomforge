from atomforge.env.base.provider import EnvironmentProvider
from atomforge.settings.settings import AtomforgeSettings


def provider_from_settings(*, warn_when_building: bool = True) -> EnvironmentProvider:
    """The environment provider a backend would use, from the settings in the
    environment."""
    from atomforge.env.uv import UVEnvironmentProvider

    settings = AtomforgeSettings()
    return UVEnvironmentProvider(
        search_path=settings.env_search_paths,
        install_path=settings.env_install_path,
        warn_when_building=warn_when_building,
    )
