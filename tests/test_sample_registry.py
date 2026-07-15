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


def test_이름에_검색어가_포함된_시료만_반환한다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    registry.register(Sample("S-002", "GaN 에피택셜-4인치", 0.3, 0.78, 220))

    result = registry.search("웨이퍼")

    assert [s.sample_id for s in result] == ["S-001"]


def test_시료_ID에_검색어가_포함된_시료도_반환한다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))
    registry.register(Sample("S-002", "GaN 에피택셜-4인치", 0.3, 0.78, 220))

    result = registry.search("S-002")

    assert [s.sample_id for s in result] == ["S-002"]


def test_검색어가_대소문자를_구분하지_않는다():
    registry = SampleRegistry()
    registry.register(Sample("S-002", "GaN 에피택셜-4인치", 0.3, 0.78, 220))

    result = registry.search("gan")

    assert [s.sample_id for s in result] == ["S-002"]


def test_일치하는_시료가_없으면_빈_목록을_반환한다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))

    assert registry.search("존재하지않음") == []


def test_공백만_있는_검색어는_빈_목록을_반환한다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 480))

    assert registry.search("   ") == []
