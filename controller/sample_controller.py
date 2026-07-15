from model.sample import Sample
from model.sample_registry import SampleRegistry
from storage.sample_repository import SampleRepository


class SampleController:
    """SampleRegistry와 SampleRepository를 연결해 시료 등록을 영속화한다."""

    def __init__(self, registry: SampleRegistry, repository: SampleRepository):
        self._registry = registry
        self._repository = repository
        for sample in self._repository.load():
            self._registry.register(sample)

    def register_sample(self, sample: Sample):
        self._registry.register(sample)
        self._repository.save(self._registry.list_all())

    def list_samples(self) -> list[Sample]:
        return self._registry.list_all()
