"""Acceptance tests for resolving accelerator and precision together
(engineering log: "Accelerators by backend, and precision per accelerator,
design"). The table is the one in that entry.

The machines are fake probe results: what a torch worker reports on each.
"""

import sys
import types

import pytest

from atomforge_core.resources.resource_caps import ResourceCapabilities
from atomforge_core.resources.resource_models import ExecutionResources
from atomforge_core.resources.resource_probes import ProbeResult
from atomforge_runtime.resources import Availability, SystemResources
from atomforge_runtime.resources.resolve import resolve_resources

CAPS = ResourceCapabilities(
    accelerator=["cpu", "cuda", "mps"],
    precision={"cpu": ["f32", "f64"], "cuda": ["f32", "f64"], "mps": ["f32"]},
)

MACHINES = {
    "mac": ProbeResult(available_accelerators=frozenset({"cpu", "mps"})),
    "nvidia": ProbeResult(available_accelerators=frozenset({"cpu", "cuda"})),
    "amd": ProbeResult(available_accelerators=frozenset({"cpu", "rocm"})),
    "no-gpu": ProbeResult(available_accelerators=frozenset({"cpu"})),
}

SYSTEM = SystemResources(
    cpu_count=8,
    platform="Linux",
    architecture="x86_64",
    hostname="test-machine",
    gpu_available=Availability.UNKNOWN,
)

# (accelerator, precision) requested, machine, (accelerator, precision)
# resolved, whether a message is recorded.
TABLE = [
    (("default", "default"), "mac", ("mps", "f32"), False),
    (("default", "default"), "nvidia", ("cuda", "f64"), False),
    (("default", "default"), "no-gpu", ("cpu", "f64"), False),
    (("default", "f64"), "mac", ("cpu", "f64"), False),
    (("gpu", "default"), "mac", ("mps", "f32"), False),
    (("gpu", "default"), "nvidia", ("cuda", "f64"), False),
    (("gpu", "default"), "amd", ("cpu", "f64"), True),
    (("mps", "default"), "mac", ("mps", "f32"), False),
    (("mps", "f64"), "mac", ("cpu", "f64"), True),
    (("cuda", "f32"), "mac", ("mps", "f32"), True),
]

STRICT_ERRORS = [
    (("mps", "f64"), "mac"),
    (("cuda", "f32"), "mac"),
]


def resolve(requested, machine, *, strict=False, caps=CAPS):
    accelerator, precision = requested
    return resolve_resources(
        exec_resources=ExecutionResources(
            accelerator=accelerator, precision=precision, strict=strict
        ),
        resource_caps=caps,
        system_resources=SYSTEM,
        probe_result=MACHINES[machine],
    )


@pytest.mark.parametrize(
    ("requested", "machine", "expected", "message"),
    TABLE,
    ids=[f"{a}-{p}-on-{m}" for (a, p), m, _, _ in TABLE],
)
def test_resolution_table(requested, machine, expected, message):
    resolved = resolve(requested, machine)

    assert (resolved.accelerator, resolved.precision) == expected
    assert bool(resolved.messages) == message, resolved.messages


@pytest.mark.parametrize(
    ("requested", "machine"),
    STRICT_ERRORS,
    ids=[f"{a}-{p}-on-{m}" for (a, p), m in STRICT_ERRORS],
)
def test_strict_requests_for_unsupported_or_unavailable_pairs_raise(requested, machine):
    with pytest.raises(ValueError):
        resolve(requested, machine, strict=True)


def test_gpu_resolves_to_rocm_on_amd_when_declared():
    caps = ResourceCapabilities(
        accelerator=["cpu", "cuda", "rocm"],
        precision={"cpu": ["f64"], "cuda": ["f64"], "rocm": ["f32"]},
    )

    resolved = resolve(("gpu", "default"), "amd", caps=caps)

    assert (resolved.accelerator, resolved.precision) == ("rocm", "f32")


def test_precision_list_without_accelerators_resolves_as_before():
    caps = ResourceCapabilities(accelerator=None, precision=["f32", "f64"])

    resolved = resolve(("default", "default"), "nvidia", caps=caps)

    assert (resolved.accelerator, resolved.precision) == (None, "f64")


def test_accelerators_without_precision_resolve_as_before():
    caps = ResourceCapabilities(accelerator=["cpu", "cuda"], precision=None)

    resolved = resolve(("gpu", "default"), "nvidia", caps=caps)

    assert (resolved.accelerator, resolved.precision) == ("cuda", None)


# The torch probe


def fake_torch(*, cuda: bool, hip: str | None):
    torch = types.ModuleType("torch")
    torch.cuda = types.SimpleNamespace(is_available=lambda: cuda)
    torch.version = types.SimpleNamespace(hip=hip, cuda=None if hip else "12.8")
    mps = types.SimpleNamespace(is_built=lambda: False, is_available=lambda: False)
    torch.backends = types.SimpleNamespace(mps=mps)
    return torch


@pytest.mark.parametrize(
    ("cuda", "hip", "expected"),
    [
        (True, None, {"cpu", "cuda"}),
        (True, "6.4.0", {"cpu", "rocm"}),
        (False, None, {"cpu"}),
    ],
    ids=["nvidia", "amd", "no-gpu"],
)
def test_torch_probe_names_the_backend(monkeypatch, cuda, hip, expected):
    from atomforge_runtime.probes.torch_probe import torch_probe

    monkeypatch.setitem(sys.modules, "torch", fake_torch(cuda=cuda, hip=hip))

    assert torch_probe(None).available_accelerators == expected
