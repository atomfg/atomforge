import pytest

from atomforge_core.env.env import parse_requirement


@pytest.mark.parametrize(
    "requirement",
    [
        ("package", "package", None),
        ("package==1.0.0", "package", "==1.0.0"),
        ("package>=1.0.0", "package", ">=1.0.0"),
        ("package<=1.0.0", "package", "<=1.0.0"),
        ("package!=1.0.0", "package", "!=1.0.0"),
        ("package>1.0.0", "package", ">1.0.0"),
        ("package<1.0.0", "package", "<1.0.0"),
        ("package~=1.0.0", "package", "~=1.0.0"),
        ("package[extra]", "package[extra]", None),
        (
            "package @ git+https://github.com/user/repo.git",
            "package",
            "@ git+https://github.com/user/repo.git",
        ),
    ],
)
def test_parse_requirement(requirement):
    package, version = parse_requirement(requirement[0])
    assert package == requirement[1]
    assert version == requirement[2]

