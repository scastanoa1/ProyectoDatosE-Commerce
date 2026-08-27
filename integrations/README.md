# Integrations

La carpeta `integrations/` se organiza por **fuente de ingesta**, no por si el
procesamiento final es batch o streaming.

```text
integrations/
├── pubsub_ingestion/
│   ├── common/
│   ├── sources/
│   ├── targets/
│   ├── sample_data/
│   ├── output/
│   └── main.py
│
└── database_ingestion/
    └── glue/
        └── .gitkeep
```

## `pubsub_ingestion`

Responsable de recibir eventos provenientes de GCP Pub/Sub o de un archivo local
de prueba y enrutarlos según `processing.targets`:

- `batch` -> punto de handoff de Glue.
- `streaming` -> punto de handoff de Flink.
- `batch + streaming` -> ambos.

Por eso esta integración no debe vivir dentro de una carpeta llamada `streaming`.

## `database_ingestion`

Reservada para la futura HU de extracción batch desde la base de datos
transaccional hacia AWS Glue. Esa integración tendrá otra fuente y otro ciclo de
vida, por lo que no se mezcla con la ingesta proveniente de Pub/Sub.
