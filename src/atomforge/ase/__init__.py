"""ASE integration for atomforge.

Requires the optional ``ase`` extra: ``uv add "atomforge[ase]"``.
"""

try:
    import ase  # noqa: F401
except ImportError as exc:  # pragma: no cover - exercised only without ase
    raise ImportError(
        "atomforge.ase requires the 'ase' package. "
        'Install it with the extra: uv add "atomforge[ase]"'
    ) from exc

from atomforge.ase._calculator import AtomforgeCalculator
from atomforge.ase._conversion import atoms_to_structure

__all__ = ["AtomforgeCalculator", "atoms_to_structure"]
