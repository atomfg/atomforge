from dataclasses import dataclass
from enum import Enum


class RouteKind(str, Enum):
    DEFAULT_EXECUTOR = "default_executor"
    MODEL_OVERRIDE = "model_override"


@dataclass(frozen=True)
class CompatibilityCheck:
    ok: bool
    reason: str | None = None


@dataclass(frozen=True)
class ExecutionRoute:
    route_kind: RouteKind
    task_kind: str


@dataclass(frozen=True)
class HostExecutabilityReport:
    ok: bool
    reason: str | None = None
    selected_route: ExecutionRoute | None = None
    candidate_routes: tuple[ExecutionRoute, ...] = ()

    @classmethod
    def success(cls) -> "HostExecutabilityReport":
        return cls(
            ok=True,
            reason=None,
            selected_route=None,
            candidate_routes=(),
        )

    @classmethod
    def success_with_routes(
        cls,
        candidate_routes: tuple[ExecutionRoute, ...],
    ) -> "HostExecutabilityReport":
        if not candidate_routes:
            raise ValueError("Successful host executability requires at least one route")
        return cls(
            ok=True,
            selected_route=candidate_routes[0],
            candidate_routes=candidate_routes,
        )

    @classmethod
    def failure(cls, reason: str) -> "HostExecutabilityReport":
        return cls(
            ok=False,
            reason=reason,
            selected_route=None,
            candidate_routes=(),
        )
