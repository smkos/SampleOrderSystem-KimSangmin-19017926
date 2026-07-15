"""orders.json 로드/저장 (원자적 쓰기 + 동시성 충돌 감지). SampleRepository 패턴 이식."""
import hashlib
import json
import os
from pathlib import Path

from model.order import Order, OrderStatus


class ConflictError(Exception):
    """마지막으로 불러온 이후 파일이 외부에서 변경되어 저장을 취소할 때 발생한다."""


def _order_to_dict(order: Order) -> dict:
    return {
        "order_id": order.order_id,
        "sample_id": order.sample_id,
        "customer_name": order.customer_name,
        "quantity": order.quantity,
        "status": order.status.value,
        "created_at": order.created_at,
    }


def _order_from_dict(data: dict) -> Order:
    return Order(
        data["order_id"],
        data["sample_id"],
        data["customer_name"],
        data["quantity"],
        OrderStatus(data["status"]),
        data["created_at"],
    )


class OrderRepository:
    def __init__(self, path: Path):
        self._path = path
        self._last_loaded_hash = None
        self._loaded = False

    def _current_file_hash(self):
        if not self._path.exists():
            return None
        with self._path.open("rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def load(self) -> list[Order]:
        if not self._path.exists():
            self._last_loaded_hash = None
            self._loaded = True
            return []
        with self._path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self._last_loaded_hash = self._current_file_hash()
        self._loaded = True
        return [_order_from_dict(item) for item in data]

    def save(self, orders: list[Order]) -> None:
        if self._loaded and self._current_file_hash() != self._last_loaded_hash:
            raise ConflictError(
                "주문 파일이 마지막으로 불러온 이후 외부에서 변경되었습니다. 저장을 취소합니다."
            )

        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump([_order_to_dict(o) for o in orders], f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._path)
        except Exception:
            tmp_path.unlink(missing_ok=True)
            raise
        self._last_loaded_hash = self._current_file_hash()
