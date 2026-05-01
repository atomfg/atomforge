from atomforge_core.task.result import TaskResult
from pydantic import model_validator

class AtomicDescriptorResult(TaskResult):
    descriptor: list[list[float]]
    natoms: int

    @model_validator(mode="after")
    def validate_descriptor(self):
        if len(self.descriptor) != self.natoms:
            raise ValueError(
                f"descriptor must have {self.natoms} rows when natoms is {self.natoms}, "
                f"but got {len(self.descriptor)}"
            )

        if self.descriptor:
            width = len(self.descriptor[0])
            if any(len(row) != width for row in self.descriptor):
                raise ValueError(
                    "all rows in descriptor must have the same number of features"
                )

        return self
    
if __name__ == "__main__":
    # Example usage
    result = AtomicDescriptorResult(
        descriptor=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]],
        natoms=3
    )
    print(result)


