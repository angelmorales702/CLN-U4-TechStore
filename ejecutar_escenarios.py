"""Ejecuta los 15 escenarios E01-E15 y genera evidencias/bitacora_escenarios.md.
Cada escenario usa pedidos recargados desde los CSV (estado independiente)."""
from decimal import Decimal
from pathlib import Path

from app.domain import DomainException, OrderItem, Money
from app.specifications import discount_amount, discount_rate
from cargar_csv import load_fixture, rows

PRICES = {x["sku"]: Decimal(x["precio_mxn"]) for x in rows("productos.csv")}


def evs(order):
    return ", ".join(e.name for e in order.events) or "ninguno"


def run(caso, pedido, accion):
    o = load_fixture()[pedido]
    ini = o.status.value
    resultado = ""
    try:
        if accion == "evaluar_descuento":
            r = discount_rate(o)
            resultado = f"descuento {int(r * 100)}% (monto {discount_amount(o)} sobre total {o.total.amount})"
        elif accion == "confirmar":
            o.confirm()
            resultado = f"{ini} -> {o.status.value}"
        elif accion.startswith("agregar"):
            sku = accion.split()[1]
            qty = int(accion.split("x")[1])
            o.add_item(OrderItem(sku, qty, Money(PRICES[sku])))
            resultado = "artículo agregado"
        elif accion == "confirmar y enviar sin guia":
            o.confirm()
            o.ship("")
        elif accion == "confirmar dos veces":
            o.confirm()
            o.confirm()
        elif accion == "confirmar, enviar y cancelar":
            o.confirm(); o.ship("GUIA-001"); o.cancel("Cliente se arrepintió")
        elif accion == "confirmar, enviar y devolver":
            o.confirm(); o.ship("GUIA-001"); o.return_order()
            resultado = f"{ini} -> {o.status.value}"
        elif accion == "confirmar, enviar y entregar":
            o.confirm(); o.ship("GUIA-001"); o.deliver()
            resultado = f"{ini} -> {o.status.value}"
    except DomainException as exc:
        resultado = f"RECHAZADO ({type(exc).__name__}): {exc}. Estado final: {o.status.value}"
    return ini, resultado, evs(o)


EXPLICACION = {
    "E01": "VIP, total 2100 (>500), 4 unidades (>=4) y sin promoción: cumple la regla del 10 %.",
    "E02": "No es VIP y el total (1050) no supera 5000: ninguna regla aplica.",
    "E03": "El cliente está inactivo: confirm() lo rechaza y el pedido sigue en DRAFT.",
    "E04": "Tiene promoción activa: ambas reglas la excluyen con NOT.",
    "E05": "Total 18000 (>5000) sin promoción: aplica el 5 % (no es VIP, no cumple el 10 %).",
    "E06": "Pedido sin artículos: confirm() lo rechaza.",
    "E07": "20 unidades exactas están permitidas (el límite es > 20).",
    "E08": "Tiene 19 unidades; agregar 2 daría 21, se rechaza antes de modificar items.",
    "E09": "Total exactamente 500: el umbral es estricto (>500), no aplica descuento.",
    "E10": "Solo 3 unidades: la regla del 10 % exige al menos 4.",
    "E11": "confirm() es válido, pero ship() sin guía lanza InvalidOrderData; queda CONFIRMED y sin OrderShipped.",
    "E12": "La segunda confirmación falla (ya está CONFIRMED) y no agrega un segundo evento.",
    "E13": "cancel() solo se permite desde CONFIRMED; desde SHIPPED se rechaza y no hay OrderCancelled.",
    "E14": "Desde SHIPPED la devolución es válida y termina en RETURNED.",
    "E15": "Desde SHIPPED la entrega es válida y termina en DELIVERED.",
}

if __name__ == "__main__":
    lines = [
        "# Bitácora de escenarios E01–E15\n",
        "| Caso | Pedido | Estado inicial | Operación | Resultado real | Eventos emitidos | Explicación |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in rows("escenarios.csv"):
        ini, res, ev = run(s["caso_id"], s["pedido_id"], s["accion"])
        lines.append(
            f"| {s['caso_id']} | {s['pedido_id']} | {ini} | {s['accion']} | {res} | {ev} | {EXPLICACION[s['caso_id']]} |"
        )
        print(s["caso_id"], s["pedido_id"], "|", s["accion"], "|", res, "| eventos:", ev)
    Path("evidencias").mkdir(exist_ok=True)
    Path("evidencias/bitacora_escenarios.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
