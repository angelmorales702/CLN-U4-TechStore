"""Dominio de TechStore U4: Value Objects, entidades, máquina de estados y eventos."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

MAX_UNITS = 20


class DomainException(Exception):
    """Base de todos los errores de negocio."""


class InvalidOrderData(DomainException):
    """Datos inválidos (monto, artículo, guía, motivo, pedido vacío...)."""


class InvalidOrderTransition(DomainException):
    """Operación no permitida desde el estado actual."""


class OrderItemLimitExceeded(DomainException):
    """Se superan las 20 unidades permitidas por pedido."""


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "MXN"

    def __post_init__(self):
        if not isinstance(self.amount, Decimal):
            raise InvalidOrderData("El monto debe ser Decimal")
        if not self.amount.is_finite() or self.amount < 0:
            raise InvalidOrderData("Monto inválido")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise InvalidOrderData("Monedas distintas")
        return Money(self.amount + other.amount, self.currency)


@dataclass(frozen=True)
class Customer:
    id: str
    is_vip: bool = False
    active: bool = True


@dataclass(frozen=True)
class OrderItem:
    sku: str
    quantity: int
    unit_price: Money

    def __post_init__(self):
        if not self.sku.strip() or self.quantity <= 0:
            raise InvalidOrderData("Artículo inválido")

    @property
    def subtotal(self) -> Money:
        return Money(self.unit_price.amount * self.quantity, self.unit_price.currency)


class OrderStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"


@dataclass(frozen=True)
class DomainEvent:
    name: str
    order_id: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Order:
    """Aggregate Root: todas las reglas de un pedido viven aquí."""
    customer: Customer
    id: str
    has_promotion: bool = False
    status: OrderStatus = OrderStatus.DRAFT
    items: list = field(default_factory=list)
    events: list = field(default_factory=list)
    tracking_number: str | None = None
    cancel_reason: str | None = None

    @property
    def units(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def total(self) -> Money:
        amount = sum((x.subtotal.amount for x in self.items), Decimal("0"))
        return Money(amount)

    def add_item(self, item: OrderItem) -> None:
        if self.status != OrderStatus.DRAFT:
            raise InvalidOrderTransition("Solo DRAFT admite artículos")
        if self.units + item.quantity > MAX_UNITS:
            raise OrderItemLimitExceeded("Máximo 20 unidades")
        if item.unit_price.currency != "MXN":
            raise InvalidOrderData("Solo MXN")
        self.items.append(item)

    # Regla común: validar primero, cambiar status después, registrar evento al final.
    def _register(self, status: OrderStatus, event_name: str) -> None:
        self.status = status
        self.events.append(DomainEvent(event_name, self.id))

    def confirm(self) -> None:
        if self.status != OrderStatus.DRAFT:
            raise InvalidOrderTransition("Solo DRAFT")
        if not self.items or not self.customer.active:
            raise InvalidOrderData("Requiere artículos y cliente activo")
        self._register(OrderStatus.CONFIRMED, "OrderConfirmed")

    def ship(self, tracking_number: str) -> None:
        if self.status != OrderStatus.CONFIRMED:
            raise InvalidOrderTransition("Solo CONFIRMED puede enviarse")
        if not tracking_number or not tracking_number.strip():
            raise InvalidOrderData("La guía de envío es obligatoria")
        self.tracking_number = tracking_number.strip()
        self._register(OrderStatus.SHIPPED, "OrderShipped")

    def cancel(self, reason: str) -> None:
        if self.status != OrderStatus.CONFIRMED:
            raise InvalidOrderTransition("Solo CONFIRMED puede cancelarse")
        if not reason or not reason.strip():
            raise InvalidOrderData("El motivo de cancelación es obligatorio")
        self.cancel_reason = reason.strip()
        self._register(OrderStatus.CANCELLED, "OrderCancelled")

    def deliver(self) -> None:
        if self.status != OrderStatus.SHIPPED:
            raise InvalidOrderTransition("Solo SHIPPED puede entregarse")
        self._register(OrderStatus.DELIVERED, "OrderDelivered")

    def return_order(self) -> None:
        if self.status != OrderStatus.SHIPPED:
            raise InvalidOrderTransition("Solo SHIPPED puede devolverse")
        self._register(OrderStatus.RETURNED, "OrderReturned")
