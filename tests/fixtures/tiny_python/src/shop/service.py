from .repository import OrderRepository


class OrderService:
    def __init__(self, repository: OrderRepository) -> None:
        self.repository = repository

    def create(self, order_id: str) -> str:
        return self.repository.save(order_id)

