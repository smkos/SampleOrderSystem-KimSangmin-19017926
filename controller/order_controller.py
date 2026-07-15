from model.order import Order
from model.order_registry import OrderRegistry
from model.sample_registry import SampleRegistry
from storage.order_repository import OrderRepository
from storage.sample_repository import SampleRepository


class OrderController:
    """OrderRegistry와 SampleRegistry를 연결해 주문 접수를 처리한다."""

    def __init__(
        self,
        order_registry: OrderRegistry,
        sample_registry: SampleRegistry,
        order_repository: OrderRepository,
        sample_repository: SampleRepository,
    ):
        self._order_registry = order_registry
        self._sample_registry = sample_registry
        self._order_repository = order_repository
        self._sample_repository = sample_repository
        self._order_registry.restore(self._order_repository.load())

    def create_order(self, sample_id: str, customer_name: str, quantity: int) -> Order:
        if not any(sample.sample_id == sample_id for sample in self._sample_registry.list_all()):
            raise ValueError(f"존재하지 않는 시료 ID입니다: {sample_id}")
        order = self._order_registry.create(sample_id, customer_name, quantity)
        self._order_repository.save(self._order_registry.list_all())
        return order

    def approve_order(self, order_id: str) -> Order:
        order = self._order_registry.get(order_id)
        sample = next(
            sample for sample in self._sample_registry.list_all()
            if sample.sample_id == order.sample_id
        )
        stock_sufficient = order.quantity <= sample.stock_qty
        approved = self._order_registry.approve(order_id, stock_sufficient)
        if stock_sufficient:
            self._sample_registry.decrease_stock(sample.sample_id, order.quantity)
        self._order_repository.save(self._order_registry.list_all())
        if stock_sufficient:
            self._sample_repository.save(self._sample_registry.list_all())
        return approved

    def reject_order(self, order_id: str) -> Order:
        rejected = self._order_registry.reject(order_id)
        self._order_repository.save(self._order_registry.list_all())
        return rejected

    def release_order(self, order_id: str) -> Order:
        released = self._order_registry.release(order_id)
        self._order_repository.save(self._order_registry.list_all())
        return released

    def list_orders(self) -> list[Order]:
        return self._order_registry.list_all()
