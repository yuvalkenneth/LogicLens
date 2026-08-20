from .repository import OrderRepository
from .service import OrderService


def build_service() -> OrderService:
    repository = OrderRepository()
    return OrderService(repository)


def create_order(order_id: str) -> str:
    service = build_service()
    return service.create(order_id)

