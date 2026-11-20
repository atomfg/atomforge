from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray


@dataclass(slots=True)
class ModelResult:
    """What a model executor's ``compute`` returns.

    Not validated at runtime (it is on the hot path); the result types
    contract in atomforge-testing checks it instead. Whatever precision the
    model ran in:

    - ``energy`` is a ``float`` (``np.float64`` qualifies, ``np.float32``
      does not);
    - ``forces`` is a float64 array of shape ``(n_atoms, 3)``;
    - ``stress`` is a float64 array of shape ``(3, 3)``;
    - ``energies`` and ``magmoms`` are float64 arrays of shape ``(n_atoms,)``.

    Arrays must not share memory with state the model reuses: a later call
    must not change a result returned earlier. Properties that were not
    computed are ``None``.
    """

    energy: float | None = None
    forces: NDArray[np.float64] | None = None
    stress: NDArray[np.float64] | None = None
    magmoms: NDArray[np.float64] | None = None
    energies: NDArray[np.float64] | None = None
    extras: dict[str, object] = field(default_factory=dict)
    metadata: dict[str, str] = field(default_factory=dict)
