import pytest
from fastapi.testclient import TestClient

from app import api
from cargar_csv import load_fixture


@pytest.fixture(autouse=True)
def reiniciar_pedidos():
    api.orders.clear()
    api.orders.update(load_fixture())


client = TestClient(api.app)


def test_get_pedido():
    r = client.get("/orders/O001")
    assert r.status_code == 200
    body = r.json()
    assert body["units"] == 4 and body["total"] == "2100.00"
    assert body["discount_rate"] == "0.10" and body["status"] == "DRAFT"


def test_pedido_inexistente_404():
    assert client.get("/orders/NOEXISTE").status_code == 404
    assert client.post("/orders/NOEXISTE/confirm").status_code == 404


def test_confirmar_ok():
    r = client.post("/orders/O013/confirm")
    assert r.status_code == 200 and r.json()["status"] == "CONFIRMED"


def test_confirmar_dos_veces_409():
    client.post("/orders/O013/confirm")
    r = client.post("/orders/O013/confirm")
    assert r.status_code == 409
    assert client.get("/orders/O013").json()["events"] == ["OrderConfirmed"]


def test_confirmar_pedido_vacio_422():
    assert client.post("/orders/O007/confirm").status_code == 422


def test_confirmar_cliente_inactivo_422():
    assert client.post("/orders/O003/confirm").status_code == 422


def test_enviar_sin_guia_422():
    client.post("/orders/O012/confirm")
    r = client.post("/orders/O012/ship", json={"tracking_number": ""})
    assert r.status_code == 422


def test_flujo_completo_entrega():
    client.post("/orders/O016/confirm")
    r = client.post("/orders/O016/ship", json={"tracking_number": "G-123"})
    assert r.status_code == 200 and r.json()["tracking_number"] == "G-123"
    r = client.post("/orders/O016/deliver")
    assert r.json()["status"] == "DELIVERED"


def test_devolucion():
    client.post("/orders/O015/confirm")
    client.post("/orders/O015/ship", json={"tracking_number": "G-1"})
    assert client.post("/orders/O015/return").json()["status"] == "RETURNED"


def test_cancelar_confirmado_y_rechazar_desde_shipped():
    client.post("/orders/O013/confirm")
    r = client.post("/orders/O013/cancel", json={"reason": "Ya no lo quiero"})
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    client.post("/orders/O014/confirm")
    client.post("/orders/O014/ship", json={"tracking_number": "G-2"})
    r = client.post("/orders/O014/cancel", json={"reason": "tarde"})
    assert r.status_code == 409


def test_listar_16_pedidos():
    assert len(client.get("/orders").json()) == 16
