import enum


class OrderStatus(enum.Enum):
    RESERVED = "RESERVED"
    REJECTED = "REJECTED"
    PRODUCING = "PRODUCING"
    CONFIRMED = "CONFIRMED"
    RELEASE = "RELEASE"


class Order:
    """주문 데이터만 보관하는 Model. 검증/전이 로직은 OrderRegistry가 담당한다."""

    def __init__(self, order_id: str, sample_id: str, customer_name: str,
                 quantity: int, status: OrderStatus, created_at: str):
        self.order_id = order_id
        self.sample_id = sample_id
        self.customer_name = customer_name
        self.quantity = quantity
        self.status = status
        self.created_at = created_at
