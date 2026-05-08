from atomforge_core.structure import StructureData


def small_molecule() -> StructureData:
    return StructureData(
        positions=[[4.5, 0.0, 0.0], [5.5, 0.0, 0.0]],
        cell=[[10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 10.0]],
        numbers=[1, 8],
        pbc=[False, False, False],
    )


def periodic_bulk() -> StructureData:
    return StructureData(
        positions=[
            [0.0, 0.0, 0.0],
            [1.5, 1.5, 1.5],
        ],
        cell=[
            [3.0, 0.0, 0.0],
            [0.0, 3.0, 0.0],
            [0.0, 0.0, 3.0],
        ],
        numbers=[14, 14],
        pbc=[True, True, True],
    )


def isolated_atom() -> StructureData:
    return StructureData(
        positions=[[5.0, 5.0, 5.0]],
        cell=[[10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 10.0]],
        numbers=[1],
        pbc=[False, False, False],
    )
