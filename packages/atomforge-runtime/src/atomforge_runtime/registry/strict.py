from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrictValidationFailure:
    kind_label: str
    registration_kind: str
    field_name: str
    path: str | None
    message: str


class RegistryStrictValidationError(Exception):
    def __init__(self, failures: list[StrictValidationFailure]) -> None:
        self.failures = failures
        super().__init__(self._build_message())

    def _build_message(self) -> str:
        lines = ["Strict registry validation failed:"]
        for failure in self.failures:
            path = f" path='{failure.path}'" if failure.path is not None else ""
            lines.append(
                f"- {failure.kind_label} '{failure.registration_kind}' field='{failure.field_name}'{path}: {failure.message}"
            )
        return "\n".join(lines)
