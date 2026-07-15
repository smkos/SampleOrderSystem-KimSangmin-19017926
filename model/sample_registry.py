from model.sample import Sample


class SampleRegistry:
    """등록된 시료를 인메모리로 보관하고, 등록 시 검증을 수행한다."""

    def __init__(self):
        self._samples: list[Sample] = []

    def register(self, sample: Sample):
        if any(existing.sample_id == sample.sample_id for existing in self._samples):
            raise ValueError(f"이미 등록된 시료 ID입니다: {sample.sample_id}")
        if not sample.name.strip():
            raise ValueError("시료명은 공백일 수 없습니다.")
        self._samples.append(sample)

    def list_all(self) -> list[Sample]:
        return list(self._samples)
