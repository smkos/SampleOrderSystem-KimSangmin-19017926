import pytest

from controller.sample_controller import SampleController
from model.sample import Sample
from model.sample_registry import SampleRegistry
from storage.sample_repository import SampleRepository


def test_생성시_저장소의_기존_시료를_레지스트리에_불러온다(tmp_path):
    path = tmp_path / "samples.json"
    seed_repo = SampleRepository(path)
    seed_repo.save([Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480)])

    controller = SampleController(SampleRegistry(), SampleRepository(path))

    assert [s.sample_id for s in controller.list_samples()] == ["S-001"]


def test_시료_등록에_성공하면_저장소에도_반영된다(tmp_path):
    path = tmp_path / "samples.json"
    controller = SampleController(SampleRegistry(), SampleRepository(path))

    controller.register_sample(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))

    reloaded = SampleRepository(path).load()
    assert [s.sample_id for s in reloaded] == ["S-001"]


def test_등록_검증에_실패하면_저장소를_변경하지_않는다(tmp_path):
    path = tmp_path / "samples.json"
    controller = SampleController(SampleRegistry(), SampleRepository(path))
    controller.register_sample(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))

    with pytest.raises(ValueError):
        controller.register_sample(Sample("S-001", "중복된 ID", 0.3, 0.9, 100))

    reloaded = SampleRepository(path).load()
    assert len(reloaded) == 1  # 실패 이전 상태 그대로 유지
