# Pub/Sub ingestion PoC

## Objetivo

Esta PoC permite probar la misma validación y el mismo routing de eventos en dos
modos:

1. **Local:** lee JSON, JSON array o JSONL sin necesitar GCP ni AWS.
2. **Pub/Sub:** consume una suscripción real de GCP.

El contrato común usa `processing.targets` para enrutar eventos:

- `batch` -> Glue.
- `streaming` -> Flink.
- ambos -> ambos.

Por ahora `targets/glue.py` y `targets/flink.py` son puntos de handoff de prueba.
No escriben todavía en S3 ni DynamoDB.

## Prueba 100 % local

Desde la raíz del repositorio:

```powershell
python -m integrations.pubsub_ingestion.main `
  --source local `
  --target all `
  --input integrations/pubsub_ingestion/sample_data/events.jsonl `
  --reset-rejected
```

También puedes usar directamente el archivo generado por el simulador:

```powershell
python -m integrations.pubsub_ingestion.main `
  --source local `
  --target all `
  --input data-generators/web-events/output/events.jsonl `
  --reset-rejected
```

Para local no necesitas Pub/Sub, credenciales GCP, AWS, `google-cloud-pubsub` ni
variables de entorno.

La salida esperada contiene mensajes como:

```text
GLUE_HANDOFF_READY ...
FLINK_HANDOFF_READY ...
REJECTED ...
LOCAL TEST FINISHED ...
```

Los errores quedan en:

```text
integrations/pubsub_ingestion/output/rejected_local.json
```

## Prueba con Pub/Sub real

Instala dependencias:

```powershell
pip install -r integrations/pubsub_ingestion/requirements.txt
```

Copia:

```powershell
Copy-Item integrations/pubsub_ingestion/.env.example `
  integrations/pubsub_ingestion/.env
```

Completa al menos:

```env
GCP_PROJECT_ID=<project-id>
PUBSUB_GLUE_SUBSCRIPTION=<subscription-glue>
PUBSUB_FLINK_SUBSCRIPTION=<subscription-flink>
GOOGLE_APPLICATION_CREDENTIALS=C:/ruta/service-account.json
```

Como existen dos subscriptions independientes, ejecuta dos procesos.

### Glue

```powershell
python -m integrations.pubsub_ingestion.main `
  --source pubsub `
  --target glue
```

### Flink

```powershell
python -m integrations.pubsub_ingestion.main `
  --source pubsub `
  --target flink
```

No se permite `--source pubsub --target all` porque el diseño real usa una
subscription distinta para cada rama.

## ACK / NACK

En modo Pub/Sub:

- evento válido y procesado -> ACK;
- evento inválido guardado en rechazados -> ACK;
- evento válido que no pertenece a esa rama -> ACK;
- error operacional inesperado -> NACK para permitir reintento.

## Validaciones

Se valida:

- envelope común;
- tipos básicos;
- timestamp ISO 8601 con zona horaria;
- `event_type` soportado;
- `processing.targets`;
- coherencia entre `event_type` y sus targets documentados;
- payload requerido por cada tipo;
- reglas simples de `search_no_results`, `product_favorite`, `purchase` y `login`;
- `event_id` duplicado dentro de la ejecución actual.

La detección de duplicados en memoria es solo una regla de calidad de esta PoC.
La idempotencia persistente/deduplicación definitiva queda para una HU posterior.

## Formatos locales soportados

### JSON object

```json
{"event_id": "..."}
```

### JSON array

```json
[
  {"event_id": "..."},
  {"event_id": "..."}
]
```

### JSONL

```text
{"event_id":"..."}
{"event_id":"..."}
```

JSONL coincide con la salida actual del simulador.
