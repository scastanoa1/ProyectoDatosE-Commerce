# Simulador de eventos de e-commerce

Simulador en Python basado en los contratos definidos en:

- `estructura-evento.md`: envelope común del evento.
- `estructura-payload-evento.md`: payload específico por `event_type` y `processing.targets`.

## Qué implementa

- Sesiones coherentes: `session_started` → navegación/interacciones → carrito/checkout opcional → `session_ended`.
- Usuarios registrados y anónimos.
- Catálogo ficticio, pero consistente entre eventos.
- Los 20 `event_type` documentados pueden aparecer en la simulación.
- Moneda `COP` para todos los payloads monetarios.
- Probabilidades de comportamiento centralizadas en `config/settings.py`.
- Inyección controlada de errores de calidad.
- Salida local en JSONL.
- Interfaz `Publisher` preparada para que otro integrante conecte Google Pub/Sub.

## Estructura

```text
event-simulator/
├── main.py
├── requirements.txt
├── config/
│   └── settings.py
├── simulator/
│   ├── data_catalog.py
│   ├── event_generator.py
│   ├── session_generator.py
│   ├── payload_generators.py
│   ├── error_injector.py
│   └── publisher.py
└── output/
```

## Ejecución

Desde la raíz del proyecto:

```bash
python main.py --events 100 --error-rate 0.05
```

Esto genera exactamente 100 eventos, los publica localmente a `output/events.jsonl` y mantiene el ritmo predeterminado de 1 evento por segundo.

Para probar sin esperar:

```bash
python main.py --events 100 --error-rate 0.05 --no-sleep
```

Para imprimir también los eventos:

```bash
python main.py --events 20 --error-rate 0.05 --console --no-sleep
```

Para una ejecución reproducible:

```bash
python main.py --events 100 --error-rate 0.05 --seed 42 --no-sleep
```

## Parámetros

- `--events`: cantidad exacta de eventos. Mínimo 3 para no cortar sesiones.
- `--rate`: eventos por segundo. Por defecto `1.0`.
- `--error-rate`: probabilidad entre `0` y `1` de inyectar un error controlado en cada evento.
- `--output`: ruta del JSONL local.
- `--console`: imprime los eventos además de escribirlos.
- `--no-sleep`: desactiva la espera entre publicaciones.
- `--seed`: semilla opcional para reproducibilidad.

## Errores de calidad simulados

Cuando un evento es seleccionado por `--error-rate`, se introduce **un solo error controlado** entre opciones como:

- `event_id` duplicado;
- timestamp inválido;
- campo requerido nulo;
- tipo incorrecto;
- `product_id` inexistente;
- categoría inconsistente en `product_view`;
- payload incompleto.

No se añade metadata de error al evento porque eso rompería el contrato que se quiere probar.

## Notas de consistencia

- Un `product_id` conserva categoría y precio en todos los eventos válidos.
- Una sesión conserva `session_id`, customer y device.
- Los eventos monetarios usan `COP`.
- `search_no_results.results_count` siempre es `0` antes de una eventual inyección de error.
- `purchase.items` se construye a partir del carrito de la misma sesión.
- `payment_success.amount` y `purchase.total_amount` son coherentes en una compra exitosa.
- `session_ended` resume páginas vistas, productos vistos, ítems agregados y si hubo compra.
- Todos los eventos pasan por el mismo `Publisher`; `processing.targets` queda como metadata de enrutamiento downstream.
