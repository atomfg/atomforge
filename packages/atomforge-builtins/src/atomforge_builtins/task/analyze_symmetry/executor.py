from atomforge_core.task.executability import CompatibilityCheck
from atomforge_core.task.executor import TaskExecutionContext, TaskExecutor

from atomforge_builtins.task.analyze_symmetry.result import AnalyzeSymmetryResult
from atomforge_builtins.task.analyze_symmetry.spec import AnalyzeSymmetry
from atomforge_builtins.task.bfgs.adapters import convert_to_atoms, convert_to_structure


class AnalyzeSymmetryExecutor(TaskExecutor[AnalyzeSymmetry, AnalyzeSymmetryResult]):
    @classmethod
    def check_compatibility(
        cls, spec: AnalyzeSymmetry, context: TaskExecutionContext
    ) -> CompatibilityCheck:
        if context.model_executor is not None:
            return CompatibilityCheck(
                ok=False,
                reason="AnalyzeSymmetry is model-free and does not accept a model executor",
            )
        return CompatibilityCheck(ok=True)

    def execute(
        self, spec: AnalyzeSymmetry, context: TaskExecutionContext
    ) -> AnalyzeSymmetryResult:
        from pymatgen.io.ase import AseAtomsAdaptor
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

        atoms = convert_to_atoms(spec.structure)
        pymatgen_structure = AseAtomsAdaptor.get_structure(atoms)
        analyzer = SpacegroupAnalyzer(
            pymatgen_structure,
            symprec=spec.symprec,
            angle_tolerance=spec.angle_tolerance,
        )

        primitive_structure = None
        if spec.return_primitive:
            primitive_atoms = AseAtomsAdaptor.get_atoms(
                analyzer.get_primitive_standard_structure()
            )
            primitive_structure = convert_to_structure(primitive_atoms)

        conventional_structure = None
        if spec.return_conventional:
            conventional_atoms = AseAtomsAdaptor.get_atoms(
                analyzer.get_conventional_standard_structure()
            )
            conventional_structure = convert_to_structure(conventional_atoms)

        return AnalyzeSymmetryResult(
            space_group_symbol=analyzer.get_space_group_symbol(),
            space_group_number=analyzer.get_space_group_number(),
            crystal_system=analyzer.get_crystal_system(),
            lattice_type=analyzer.get_lattice_type(),
            point_group_symbol=analyzer.get_point_group_symbol(),
            primitive_structure=primitive_structure,
            conventional_structure=conventional_structure,
        )
