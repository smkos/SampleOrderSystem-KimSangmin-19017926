import pytest

from model.order import Order, OrderStatus
from storage.order_repository import ConflictError, OrderRepository


def _sample_order(order_id="ORD-20260715-0001", status=OrderStatus.RESERVED):
    return Order(order_id, "S-001", "삼성전자 파운드리", 200, status, "2026-07-15T09:32:15")


def test_저장한_주문_목록을_그대로_불러온다(tmp_path):
    repo = OrderRepository(tmp_path / "orders.json")
    repo.save([_sample_order()])

    loaded = repo.load()

    assert len(loaded) == 1
    assert loaded[0].order_id == "ORD-20260715-0001"
    assert loaded[0].status == OrderStatus.RESERVED


def test_저장된_status는_문자열로_기록된다(tmp_path):
    import json

    path = tmp_path / "orders.json"
    repo = OrderRepository(path)
    repo.save([_sample_order(status=OrderStatus.PRODUCING)])

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert data[0]["status"] == "PRODUCING"


def test_파일이_없으면_빈_목록을_반환한다(tmp_path):
    repo = OrderRepository(tmp_path / "orders.json")
    assert repo.load() == []


def test_쓰기_도중_실패해도_기존_파일이_손상되지_않는다(tmp_path, mocker):
    path = tmp_path / "orders.json"
    repo = OrderRepository(path)
    repo.save([_sample_order()])

    mocker.patch("storage.order_repository.os.replace", side_effect=OSError("disk full"))
    with pytest.raises(OSError):
        repo.save([_sample_order(order_id="ORD-20260715-0002")])

    # 실패 이전 저장 내용이 그대로 남아 있어야 한다
    assert repo.load()[0].order_id == "ORD-20260715-0001"


def test_로드_이후_외부에서_파일이_변경되면_저장시_충돌을_감지한다(tmp_path):
    path = tmp_path / "orders.json"
    repo = OrderRepository(path)
    repo.save([_sample_order()])

    loaded_repo = OrderRepository(path)
    loaded_repo.load()

    # 다른 프로세스가 파일을 직접 수정한 상황을 재현
    other_repo = OrderRepository(path)
    other_repo.save([_sample_order(order_id="ORD-20260715-9999")])

    with pytest.raises(ConflictError):
        loaded_repo.save([_sample_order(order_id="ORD-20260715-0002")])


def test_로드시_파일이_없었는데_이후_외부에서_생성되면_저장시_충돌을_감지한다(tmp_path):
    path = tmp_path / "orders.json"
    repo = OrderRepository(path)
    repo.load()  # 파일이 없는 상태로 로드

    other_repo = OrderRepository(path)
    other_repo.save([_sample_order()])

    with pytest.raises(ConflictError):
        repo.save([_sample_order(order_id="ORD-20260715-0002")])
