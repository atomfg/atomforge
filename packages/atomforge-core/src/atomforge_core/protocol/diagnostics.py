from pydantic import BaseModel, ConfigDict, Field


class WorkerDiagnostics(BaseModel):
    """Side-channel information the worker captured while handling one request.

    Model libraries print, warn and log in many ways (Python ``print``,
    ``warnings``, ``logging``, and C/C++/CUDA code writing straight to file
    descriptors 1 and 2). The worker captures all of it per request so it is
    kept alongside the result instead of being discarded or corrupting the
    protocol stream.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    warnings: tuple[str, ...] = Field(
        default=(),
        description="Distinct Python warnings raised while handling the request, formatted as 'Category: message' with a repeat count when repeated.",
    )
    output: str | None = Field(
        default=None,
        description="Captured stdout/stderr output (Python- and file-descriptor-level). Truncated to the most recent characters when long.",
    )
    output_truncated: bool = Field(
        default=False,
        description="Whether `output` was truncated.",
    )
    duration_s: float | None = Field(
        default=None,
        description="Wall time spent handling the request inside the worker, in seconds.",
    )
