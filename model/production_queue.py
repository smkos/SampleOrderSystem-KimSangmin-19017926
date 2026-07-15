import math

from model.order import Order, OrderStatus


def calculate_shortage(quantity: int, stock_qty: int) -> int:
    return max(0, quantity - stock_qty)


def calculate_actual_production_qty(shortage: int, yield_rate: float) -> int:
    return math.ceil(shortage / yield_rate)


def calculate_total_production_time_min(avg_production_time_min: float, actual_production_qty: int) -> float:
    return avg_production_time_min * actual_production_qty


def sort_production_queue(orders: list[Order]) -> list[Order]:
    producing_orders = [order for order in orders if order.status == OrderStatus.PRODUCING]
    return sorted(producing_orders, key=lambda order: order.created_at)
