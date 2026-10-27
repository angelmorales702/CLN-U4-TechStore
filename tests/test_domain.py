import pytest
from decimal import Decimal

from app.domain import (
    Customer, InvalidOrderData, InvalidOrderTransition, Money, Order,
    OrderItem, OrderItemLimitExceeded, OrderStatus,
)
from app.specifications import (
    ActivePromotionSpec, MinimumAmountSpec, VIPCustomerSpec,
    discount_amount, discount_rate,
)
from cargar_csv import load_fixture


@pytest.fixture
def orders():
    return load_fixture()


def make_order(units=1, price="100", vip=False, active=True, promo=False):
    o = Order(Customer("CX", vip, active), "OX", promo)
    if units:
        o.add_item(OrderItem("SKU001", units, Money(Decimal(price))))
    return o


# ---------- Value Objects ----------
def test_money_negativo():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("-1"))


def test_money_no_finito():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("NaN"))


def test_money_add_devuelve_objeto_nuevo():
    a, b = Money(Decimal("10")), Money(Decimal("5"))
    c = a.add(b)
    assert c.amount == Decimal("15") and a.amount == Decimal("10")


def test_money_monedas_distintas():
    with pytest.raises(InvalidOrderData):
        Money(Decimal("1")).add(Money(Decimal("1"), "USD"))


def test_money_es_inmutable():
    m = Money(Decimal("1"))
    with pytest.raises(Exception):
        m.amount = Decimal("2")


@pytest.mark.parametrize("sku,qty", [("", 1), ("  ", 1), ("SKU001", 0), ("SKU001", -1)])
def test_orderitem_invalido(sku, qty):
    with pytest.raises(InvalidOrderData):
        OrderItem(sku, qty, Money(Decimal("1")))


# ---------- Carga de datos ----------
def test_carga_16_pedidos_en_draft(orders):
    assert len(orders) == 16
    assert all(o.status == OrderStatus.DRAFT for o in orders.values())


def test_pedido_o001_inicia_draft(orders):
    assert orders["O001"].status.value == "DRAFT"
    assert orders["O001"].units == 4
    assert orders["O001"].total.amount == Decimal("2100.00")


# ---------- Límite de unidades ----------
def test_20_unidades_permitidas(orders):
    assert orders["O008"].units == 20


def test_21_unidades_rechazadas():
    o = make_order(units=19)
    with pytest.raises(OrderItemLimitExceeded):
        o.add_item(OrderItem("SKU003", 2, Money(Decimal("1"))))
    assert o.units == 19  # no se modificó items


def test_limite_cuenta_unidades_no_renglones():
    o = make_order(units=0)
    for _ in range(5):  # 5 renglones de 4 = 20 unidades
        o.add_item(OrderItem("SKU001", 4, Money(Decimal("1"))))
    assert len(o.items) == 5 and o.units == 20


def test_solo_draft_admite_articulos():
    o = make_order()
    o.confirm()
    with pytest.raises(InvalidOrderTransition):
        o.add_item(OrderItem("SKU001", 1, Money(Decimal("1"))))


# ---------- Descuentos ----------
@pytest.mark.parametrize("pid,tasa", [
    ("O001", "0.10"),   # E01 VIP, >500, >=4 unidades, sin promoción
    ("O002", "0"),      # E02 no VIP
    ("O005", "0"),      # E04 promoción activa
    ("O006", "0.05"),   # E05 total > 5000
    ("O010", "0"),      # E09 total exacto 500: umbral estricto
    ("O011", "0"),      # E10 solo 3 unidades
])
def test_descuentos_de_escenarios(orders, pid, tasa):
    assert discount_rate(orders[pid]) == Decimal(tasa)


def test_descuento_monto_o001(orders):
    assert discount_amount(orders["O001"]) == Decimal("210.00")


def test_prioridad_10_sobre_5():
    o = make_order(units=4, price="2000", vip=True)  # total 8000, VIP, 4 uds
    assert discount_rate(o) == Decimal("0.10")


def test_frontera_5000_no_aplica():
    o = make_order(units=1, price="5000")
    assert discount_rate(o) == Decimal("0")


def test_promocion_bloquea_5_por_ciento():
    o = make_order(units=1, price="6000", promo=True)
    assert discount_rate(o) == Decimal("0")


def test_composicion_and_or_not():
    o = make_order(units=1, price="600", vip=True)
    assert (VIPCustomerSpec() & MinimumAmountSpec(Decimal("500"))).is_satisfied_by(o)
    assert (VIPCustomerSpec() | ActivePromotionSpec()).is_satisfied_by(o)
    assert (~ActivePromotionSpec()).is_satisfied_by(o)
    assert not (ActivePromotionSpec() & VIPCustomerSpec()).is_satisfied_by(o)


def test_specification_no_modifica_el_pedido(orders):
    o = orders["O001"]
    discount_rate(o)
    assert o.status == OrderStatus.DRAFT and o.events == []


# ---------- Máquina de estados y eventos ----------
def test_confirmar_cliente_inactivo(orders):
    o = orders["O003"]
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.status == OrderStatus.DRAFT and o.events == []


def test_confirmar_pedido_vacio(orders):
    o = orders["O007"]
    with pytest.raises(InvalidOrderData):
        o.confirm()
    assert o.events == []


def test_confirmar_dos_veces_no_agrega_evento(orders):
    o = orders["O013"]
    o.confirm()
    assert o.status == OrderStatus.CONFIRMED
    assert [e.name for e in o.events] == ["OrderConfirmed"]
    with pytest.raises(InvalidOrderTransition):
        o.confirm()
    assert len(o.events) == 1


@pytest.mark.parametrize("guia", ["", "   "])
def test_enviar_sin_guia(orders, guia):
    o = orders["O012"]
    o.confirm()
    with pytest.raises(InvalidOrderData):
        o.ship(guia)
    assert o.status == OrderStatus.CONFIRMED
    assert [e.name for e in o.events] == ["OrderConfirmed"]


def test_cancelar_desde_shipped_rechazado(orders):
    o = orders["O014"]
    o.confirm(); o.ship("G1")
    with pytest.raises(InvalidOrderTransition):
        o.cancel("tarde")
    assert o.status == OrderStatus.SHIPPED
    assert "OrderCancelled" not in [e.name for e in o.events]


def test_cancelar_desde_confirmed(orders):
    o = orders["O013"]
    o.confirm()
    o.cancel("Cliente cambió de opinión")
    assert o.status == OrderStatus.CANCELLED
    assert o.events[-1].name == "OrderCancelled"


def test_cancelar_sin_motivo(orders):
    o = orders["O013"]
    o.confirm()
    with pytest.raises(InvalidOrderData):
        o.cancel(" ")
    assert o.status == OrderStatus.CONFIRMED


def test_flujo_entregado(orders):
    o = orders["O016"]
    o.confirm(); o.ship("G1"); o.deliver()
    assert o.status == OrderStatus.DELIVERED
    assert [e.name for e in o.events] == ["OrderConfirmed", "OrderShipped", "OrderDelivered"]


def test_flujo_devuelto(orders):
    o = orders["O015"]
    o.confirm(); o.ship("G1"); o.return_order()
    assert o.status == OrderStatus.RETURNED
    assert o.events[-1].name == "OrderReturned"


def test_no_entregar_ni_devolver_desde_confirmed(orders):
    o = orders["O013"]
    o.confirm()
    with pytest.raises(InvalidOrderTransition):
        o.deliver()
    with pytest.raises(InvalidOrderTransition):
        o.return_order()
