class EnvironmentError(RuntimeError):
    pass


class EnvironmentNotFoundError(EnvironmentError):
    pass


class EnvironmentCreationError(EnvironmentError):
    pass
