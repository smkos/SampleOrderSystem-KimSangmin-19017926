import pytest

from model.sample import Sample
from model.sample_registry import SampleRegistry


def test_등록된_시료가_목록에_추가된다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    assert len(registry.list_all()) == 1


def test_중복된_sample_id는_등록을_거부한다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    with pytest.raises(ValueError):
        registry.register(Sample("S-001", "다른 시료", 0.3, 0.9, 100))


def test_공백만_있는_이름은_등록을_거부한다():
    registry = SampleRegistry()
    with pytest.raises(ValueError):
        registry.register(Sample("S-002", "   ", 0.3, 0.9, 100))
