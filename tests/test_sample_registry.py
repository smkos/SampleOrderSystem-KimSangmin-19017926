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


def test_수율이_0이면_등록을_거부한다():
    registry = SampleRegistry()
    with pytest.raises(ValueError):
        registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.0, 480))


def test_수율이_1보다_크면_등록을_거부한다():
    registry = SampleRegistry()
    with pytest.raises(ValueError):
        registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 1.5, 480))


def test_수율이_음수이면_등록을_거부한다():
    registry = SampleRegistry()
    with pytest.raises(ValueError):
        registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, -0.1, 480))


def test_수율이_1이면_등록을_허용한다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 1.0, 480))

    assert registry.list_all()[0].yield_rate == 1.0


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


def test_재고를_증가시키면_수량이_늘어난다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))

    updated = registry.increase_stock("S-001", 164)

    assert updated.stock_qty == 214


def test_존재하지_않는_시료ID의_재고를_증가시키면_예외가_발생한다():
    registry = SampleRegistry()

    with pytest.raises(ValueError):
        registry.increase_stock("S-999", 10)


def test_음수만큼_재고를_증가시키면_예외가_발생하고_수량이_바뀌지_않는다():
    registry = SampleRegistry()
    registry.register(Sample("S-001", "실리콘 웨이퍼-8인치", 0.5, 0.92, 50))

    with pytest.raises(ValueError):
        registry.increase_stock("S-001", -1)
    assert registry.search("S-001")[0].stock_qty == 50
