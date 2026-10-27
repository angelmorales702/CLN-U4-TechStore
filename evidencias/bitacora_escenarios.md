# Bitácora de escenarios E01–E15

| Caso | Pedido | Estado inicial | Operación | Resultado real | Eventos emitidos | Explicación |
|---|---|---|---|---|---|---|
| E01 | O001 | DRAFT | evaluar_descuento | descuento 10% (monto 210.00 sobre total 2100.00) | ninguno | VIP, total 2100 (>500), 4 unidades (>=4) y sin promoción: cumple la regla del 10 %. |
| E02 | O002 | DRAFT | evaluar_descuento | descuento 0% (monto 0.00 sobre total 1050.00) | ninguno | No es VIP y el total (1050) no supera 5000: ninguna regla aplica. |
| E03 | O003 | DRAFT | confirmar | RECHAZADO (InvalidOrderData): Requiere artículos y cliente activo. Estado final: DRAFT | ninguno | El cliente está inactivo: confirm() lo rechaza y el pedido sigue en DRAFT. |
| E04 | O005 | DRAFT | evaluar_descuento | descuento 0% (monto 0.00 sobre total 2100.00) | ninguno | Tiene promoción activa: ambas reglas la excluyen con NOT. |
| E05 | O006 | DRAFT | evaluar_descuento | descuento 5% (monto 900.00 sobre total 18000.00) | ninguno | Total 18000 (>5000) sin promoción: aplica el 5 % (no es VIP, no cumple el 10 %). |
| E06 | O007 | DRAFT | confirmar | RECHAZADO (InvalidOrderData): Requiere artículos y cliente activo. Estado final: DRAFT | ninguno | Pedido sin artículos: confirm() lo rechaza. |
| E07 | O008 | DRAFT | confirmar | DRAFT -> CONFIRMED | OrderConfirmed | 20 unidades exactas están permitidas (el límite es > 20). |
| E08 | O009 | DRAFT | agregar SKU003 x2 | RECHAZADO (OrderItemLimitExceeded): Máximo 20 unidades. Estado final: DRAFT | ninguno | Tiene 19 unidades; agregar 2 daría 21, se rechaza antes de modificar items. |
| E09 | O010 | DRAFT | evaluar_descuento | descuento 0% (monto 0.00 sobre total 500.00) | ninguno | Total exactamente 500: el umbral es estricto (>500), no aplica descuento. |
| E10 | O011 | DRAFT | evaluar_descuento | descuento 0% (monto 0.00 sobre total 1500.00) | ninguno | Solo 3 unidades: la regla del 10 % exige al menos 4. |
| E11 | O012 | DRAFT | confirmar y enviar sin guia | RECHAZADO (InvalidOrderData): La guía de envío es obligatoria. Estado final: CONFIRMED | OrderConfirmed | confirm() es válido, pero ship() sin guía lanza InvalidOrderData; queda CONFIRMED y sin OrderShipped. |
| E12 | O013 | DRAFT | confirmar dos veces | RECHAZADO (InvalidOrderTransition): Solo DRAFT. Estado final: CONFIRMED | OrderConfirmed | La segunda confirmación falla (ya está CONFIRMED) y no agrega un segundo evento. |
| E13 | O014 | DRAFT | confirmar, enviar y cancelar | RECHAZADO (InvalidOrderTransition): Solo CONFIRMED puede cancelarse. Estado final: SHIPPED | OrderConfirmed, OrderShipped | cancel() solo se permite desde CONFIRMED; desde SHIPPED se rechaza y no hay OrderCancelled. |
| E14 | O015 | DRAFT | confirmar, enviar y devolver | DRAFT -> RETURNED | OrderConfirmed, OrderShipped, OrderReturned | Desde SHIPPED la devolución es válida y termina en RETURNED. |
| E15 | O016 | DRAFT | confirmar, enviar y entregar | DRAFT -> DELIVERED | OrderConfirmed, OrderShipped, OrderDelivered | Desde SHIPPED la entrega es válida y termina en DELIVERED. |
