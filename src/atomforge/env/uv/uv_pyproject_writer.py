from atomforge.env.base.pyproject_writer import PyprojectWriter

class UVPyprojectWriter(PyprojectWriter):
    
    def _extras_string(self) -> str:
        extras = ""
        uv_sources = [dep for dep in self.dependencies if dep.exact and dep.url and dep.url.startswith("file://")]
        if uv_sources:
            extras += "[tool.uv.sources]\n"
            for dep in uv_sources:
                package_name = dep.name.replace("_", "-")
                extras += f'{package_name} = {{ path = "{dep.url[7:]}", editable=true }}\n'
        return extras
