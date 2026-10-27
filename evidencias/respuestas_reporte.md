# Preguntas para el reporte (borrador para reescribir con tus palabras)

1. **¿Por qué Decimal y no float?** Un float guarda aproximaciones binarias (0.1 + 0.2 no es exactamente 0.3); en dinero esos errores se acumulan. Decimal representa los importes exactamente, y por eso se construye desde texto: `Decimal("600.00")`.
2. **¿Contar renglones o sumar unidades?** El límite es de 20 unidades. Un pedido con 5 renglones de 4 unidades tiene 5 renglones pero 20 unidades; `units` suma las cantidades, no cuenta filas.
3. **¿Ventaja de la Specification?** Cada regla es una clase pequeña, con nombre del negocio, que se prueba sola y se combina con `&`, `|` y `~` sin tocar el pedido. Cambiar un umbral es cambiar un parámetro, no reescribir condicionales.
4. **¿Por qué eventos solo tras una transición válida?** Un evento es un hecho ya ocurrido. Si se registrara antes de validar, un intento rechazado dejaría un "OrderConfirmed" falso y otros sistemas actuarían sobre algo que no pasó.
5. **¿Qué se reutiliza si cambia FastAPI?** Todo `domain.py` y `specifications.py`: no importan FastAPI. Solo se reemplaza `api.py`, que únicamente busca el pedido, llama al método de `Order` y traduce las excepciones a respuestas.
