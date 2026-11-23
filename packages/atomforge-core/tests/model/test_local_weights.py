"""Acceptance tests for `LocalWeights` ("Variants, settings and local weights
in the spec, design" in the engineering log): parameters outside a provider's
catalogue, identified by their contents."""

import hashlib

import pytest

from atomforge_core.model.weights import LocalWeights


@pytest.fixture
def weights_file(tmp_path):
    path = tmp_path / "fine-tuned.model"
    path.write_bytes(b"fine-tuned parameters")
    return path


def test_the_path_is_made_absolute(weights_file, monkeypatch):
    monkeypatch.chdir(weights_file.parent)

    weights = LocalWeights(weights_file.name)

    assert weights.path.is_absolute()
    assert weights.path == weights_file


def test_a_file_hashes_to_the_sha256_of_its_contents(weights_file):
    weights = LocalWeights(weights_file)

    assert weights.sha256 == hashlib.sha256(b"fine-tuned parameters").hexdigest()


def test_the_same_file_at_two_paths_has_one_hash(weights_file, tmp_path):
    copy = tmp_path / "copy.model"
    copy.write_bytes(weights_file.read_bytes())

    assert LocalWeights(weights_file).sha256 == LocalWeights(copy).sha256


def test_two_files_at_one_path_have_two_hashes(weights_file):
    first = LocalWeights(weights_file)
    weights_file.write_bytes(b"other parameters")
    second = LocalWeights(weights_file)

    assert first.sha256 != second.sha256


def _write_tree(root, files):
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return root


def test_a_directory_hashes_by_relative_paths_and_contents(tmp_path):
    files = {"saved_model.pb": b"graph", "variables/variables.data": b"values"}
    first = _write_tree(tmp_path / "first", files)
    second = _write_tree(tmp_path / "second", files)
    renamed = _write_tree(
        tmp_path / "renamed",
        {"saved_model.pb": b"graph", "variables/other.data": b"values"},
    )
    changed = _write_tree(
        tmp_path / "changed",
        {"saved_model.pb": b"graph", "variables/variables.data": b"VALUES"},
    )

    assert LocalWeights(first).sha256 == LocalWeights(second).sha256
    assert LocalWeights(first).sha256 != LocalWeights(renamed).sha256
    assert LocalWeights(first).sha256 != LocalWeights(changed).sha256


def test_verify_passes_for_an_unchanged_file(weights_file):
    weights = LocalWeights(weights_file)

    assert weights.verify() == weights_file


def test_verify_rejects_a_changed_file(weights_file):
    weights = LocalWeights(weights_file)
    weights_file.write_bytes(b"overwritten by a later fine-tune")

    with pytest.raises(ValueError, match="sha256"):
        weights.verify()


def test_verify_rejects_a_missing_file(weights_file):
    weights = LocalWeights(weights_file)
    weights_file.unlink()

    with pytest.raises((ValueError, FileNotFoundError)):
        weights.verify()


def test_a_given_hash_is_kept_and_checked_by_verify(weights_file):
    weights = LocalWeights(weights_file, sha256="0" * 64)

    assert weights.sha256 == "0" * 64
    with pytest.raises(ValueError):
        weights.verify()


def test_label_and_provider_version_are_kept(weights_file):
    weights = LocalWeights(
        weights_file, label="my-fine-tune", provider_version="mace-torch==0.3.14"
    )

    assert weights.label == "my-fine-tune"
    assert weights.provider_version == "mace-torch==0.3.14"


def test_weights_round_trip_through_json_without_rehashing(weights_file):
    weights = LocalWeights(weights_file)

    restored = LocalWeights.model_validate_json(weights.model_dump_json())

    assert restored == weights
    # A spec reaches the worker as JSON; the hash travels with it, so a file
    # changed in between is caught by verify(), not silently rehashed.
    weights_file.write_bytes(b"changed")
    restored = LocalWeights.model_validate_json(weights.model_dump_json())
    assert restored.sha256 == weights.sha256
