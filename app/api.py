"""API REST de TechStore U4. Los endpoints solo coordinan: las reglas están en Order."""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.domain import (
    InvalidOrderData,
    InvalidOrderTransition,
    OrderItemLimitExceeded,
)
from app.specifications import discount_amount, discount_rate
from cargar_csv import load_fixture

app = FastAPI(title="TechStore U4")
orders = load_fixture()  # repositorio en memoria


class ShipBody(BaseModel):
    tracking_number: str = ""


class CancelBody(BaseModel):
    reason: str = ""


def _get(order_id: str):
    order = orders.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="No existe")
    return order


def _summary(order):
    return {"id": order.id, "status": order.status.value}


@app.exception_handler(InvalidOrderTransition)
async def _transition(request: Request, exc: InvalidOrderTransition):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(InvalidOrderData)
async def _invalid(request: Request, exc: InvalidOrderData):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(OrderItemLimitExceeded)
async def _limit(request: Request, exc: OrderItemLimitExceeded):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/orders")
def list_orders():
    return [_summary(o) for o in orders.values()]


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    o = _get(order_id)
    return {
        "id": o.id,
        "customer_id": o.customer.id,
        "status": o.status.value,
        "units": o.units,
        "total": str(o.total.amount),
        "currency": o.total.currency,
        "has_promotion": o.has_promotion,
        "discount_rate": str(discount_rate(o)),
        "discount_amount": str(discount_amount(o)),
        "tracking_number": o.tracking_number,
        "events": [e.name for e in o.events],
    }


@app.post("/orders/{order_id}/confirm")
def confirm_order(order_id: str):
    o = _get(order_id)
    o.confirm()
    return _summary(o)


@app.post("/orders/{order_id}/ship")
def ship_order(order_id: str, body: ShipBody):
    o = _get(order_id)
    o.ship(body.tracking_number)
    return {**_summary(o), "tracking_number": o.tracking_number}


@app.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str, body: CancelBody):
    o = _get(order_id)
    o.cancel(body.reason)
    return _summary(o)


@app.post("/orders/{order_id}/deliver")
def deliver_order(order_id: str):
    o = _get(order_id)
    o.deliver()
    return _summary(o)


@app.post("/orders/{order_id}/return")
def return_order(order_id: str):
    o = _get(order_id)
    o.return_order()
    return _summary(o)
