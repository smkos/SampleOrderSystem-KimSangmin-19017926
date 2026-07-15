import random

import pytest

from devtools.dummy_data_generator import (
    generate_dummy_order_input,
    generate_dummy_sample,
    generate_dummy_samples,
)
from model.sample import Sample


def test_동일한_시드로_생성하면_완전히_같은_시료_목록이_생성된다():
    first = generate_dummy_samples(5, [], rng=random.Random(42))
    second = generate_dummy_samples(5, [], rng=random.Random(42))

    assert [(s.sample_id, s.name, s.avg_production_time_min, s.yield_rate, s.stock_qty)
            for s in first] == \
           [(s.sample_id, s.name, s.avg_production_time_min, s.yield_rate, s.stock_qty)
            for s in second]


def test_count가_음수이면_ValueError():
    with pytest.raises(ValueError):
        generate_dummy_samples(-1, [], rng=random.Random(1))


def test_기존_시료_다음_번호부터_이어서_채번된다():
    existing = [Sample("S-001", "기존 시료", 0.5, 0.9, 100)]

    generated = generate_dummy_samples(2, existing, rng=random.Random(1))

    assert [s.sample_id for s in generated] == ["S-002", "S-003"]


def test_생성된_시료의_수율은_0보다_크고_1_이하다():
    generated = generate_dummy_samples(20, [], rng=random.Random(7))

    assert all(0 < s.yield_rate <= 1 for s in generated)


def test_생성된_시료의_재고와_생산시간은_유효_범위를_만족한다():
    generated = generate_dummy_samples(20, [], rng=random.Random(7))

    assert all(s.stock_qty >= 0 for s in generated)
    assert all(s.avg_production_time_min > 0 for s in generated)


def test_동일한_시드로_생성하면_완전히_같은_주문_입력값이_생성된다():
    samples = [Sample("S-001", "실리콘 웨이퍼-4인치", 1.0, 0.9, 100)]

    first = generate_dummy_order_input(samples, rng=random.Random(42))
    second = generate_dummy_order_input(samples, rng=random.Random(42))

    assert first == second


def test_existing_samples가_비어있으면_ValueError():
    with pytest.raises(ValueError):
        generate_dummy_order_input([], rng=random.Random(1))


def test_생성된_sample_id는_existing_samples_중_하나다():
    samples = [
        Sample("S-001", "실리콘 웨이퍼-4인치", 1.0, 0.9, 100),
        Sample("S-002", "GaN 에피택셜-6인치", 2.0, 0.8, 50),
    ]
    existing_ids = {s.sample_id for s in samples}

    result = generate_dummy_order_input(samples, rng=random.Random(7))

    assert result["sample_id"] in existing_ids


def test_생성된_quantity는_0보다_크다():
    samples = [Sample("S-001", "실리콘 웨이퍼-4인치", 1.0, 0.9, 100)]

    result = generate_dummy_order_input(samples, rng=random.Random(7))

    assert result["quantity"] > 0


def test_반환값은_sample_id_customer_name_quantity_키만_가진다():
    samples = [Sample("S-001", "실리콘 웨이퍼-4인치", 1.0, 0.9, 100)]

    result = generate_dummy_order_input(samples, rng=random.Random(7))

    assert set(result.keys()) == {"sample_id", "customer_name", "quantity"}
