from atomforge.env.base.pyproject_writer import PyprojectWriter


class UVPyprojectWriter(PyprojectWriter):
    def _extras_string(self) -> str:
        extras = ""
        find_links = self.extras.get("uv.find-links")
        if find_links is not None:
            extras += "[tool.uv]\n"
            extras += f"find-links = {find_links}\n\n"

        uv_sources = [dep for dep in self.dependencies if dep.exact and dep.url and dep.url.startswith("file://")]
        if uv_sources:
            extras += "[tool.uv.sources]\n"
            for dep in uv_sources:
                package_name = dep.name.replace("_", "-")
                extras += f'{package_name} = {{ path = "{dep.url[7:]}", editable=true }}\n'
            extras += "\n"

        extra_build_dependencies = {
            key.removeprefix("uv.extra-build-dependencies."): value
            for key, value in self.extras.items()
            if key.startswith("uv.extra-build-dependencies.")
        }
        if extra_build_dependencies:
            extras += "[tool.uv.extra-build-dependencies]\n"
            for package_name, requirement_list in sorted(
                extra_build_dependencies.items()
            ):
                extras += f'{package_name} = {requirement_list}\n'
        return extras
