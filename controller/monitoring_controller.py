from model import monitoring
from model.order import OrderStatus
from model.order_registry import OrderRegistry
from model.sample_registry import SampleRegistry


class MonitoringController:
    """OrderRegistry와 SampleRegistry를 연결해 모니터링 집계를 수행한다."""

    def __init__(self, order_registry: OrderRegistry, sample_registry: SampleRegistry):
        self._order_registry = order_registry
        self._sample_registry = sample_registry

    def count_orders_by_status(self) -> dict[OrderStatus, int]:
        return monitoring.count_orders_by_status(self._order_registry.list_all())

    def stock_status_by_sample(self) -> dict[str, str]:
        orders = self._order_registry.list_all()
        labels = {}
        for sample in self._sample_registry.list_all():
            pending_qty = monitoring.sum_pending_order_qty(orders, sample.sample_id)
            labels[sample.sample_id] = monitoring.calculate_stock_status_label(sample.stock_qty, pending_qty)
        return labels
