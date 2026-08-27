import logging
import re
import uuid
from typing import Optional

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


logger = logging.getLogger(__name__)

# TABLAS SOPORTADAS

SUPPORTED_TABLES = {
    "users",
    "addresses",
    "categories",
    "products",
    "product_variants",
    "product_categories",
    "product_inventory",
    "orders",
    "order_items",
    "payments",
    "carts",
    "cart_items",
    "product_reviews",
}

# COLUMNAS DE USERS

USERS_BRONZE_COLUMNS = [
    "user_id",
    "email",
    "first_name",
    "last_name",
    "phone",
    "birth_date",
    "gender",
    "status",
    "created_at",
    "updated_at",
]

# VALIDACIONES

def validate_identifier(
    value: str,
    identifier_name: str,
) -> None:
    """
    Valida identificadores simples como schemas,
    bases de datos o catálogos.

    Solo permite:
    - letras
    - números
    - guion bajo

    El identificador debe comenzar por letra o guion bajo.
    """

    pattern = r"^[A-Za-z_][A-Za-z0-9_]*$"

    if not value or not re.match(pattern, value):
        raise ValueError(
            f"Invalid {identifier_name}: '{value}'. "
            "Only letters, numbers and underscores are allowed."
        )


def validate_source_table(
    source_table: str,
) -> None:
    """
    Verifica que la tabla solicitada pertenezca
    al modelo transaccional del e-commerce.
    """

    if source_table not in SUPPORTED_TABLES:
        raise ValueError(
            f"Unsupported source table: '{source_table}'. "
            f"Allowed tables: {sorted(SUPPORTED_TABLES)}"
        )

# EXTRACCIÓN JDBC

def read_postgresql_table(
    glue_context,
    connection_name: str,
    source_schema: str,
    source_table: str,
) -> DataFrame:
    """
    Realiza una extracción FULL LOAD desde PostgreSQL.

    La conexión JDBC se obtiene desde una AWS Glue Connection.

    Para la tabla users se utiliza una consulta explícita
    para evitar extraer password_hash.
    """

    validate_identifier(
        source_schema,
        "source_schema",
    )

    validate_source_table(
        source_table,
    )

    qualified_table = (
        f"{source_schema}.{source_table}"
    )

    connection_options = {
        "useConnectionProperties": "true",
        "connectionName": connection_name,
    }

    if source_table == "users":

        columns = ", ".join(
            USERS_BRONZE_COLUMNS
        )

        connection_options["sampleQuery"] = (
            f"SELECT {columns} "
            f"FROM {qualified_table}"
        )

    else:

        connection_options["dbtable"] = (
            qualified_table
        )

    logger.info(
        (
            "BATCH_JDBC_READ_START "
            "source_table=%s "
            "connection_name=%s"
        ),
        qualified_table,
        connection_name,
    )

    dynamic_frame = (
        glue_context
        .create_dynamic_frame
        .from_options(
            connection_type="postgresql",
            connection_options=connection_options,
            transformation_ctx=(
                f"read_{source_table}"
            ),
        )
    )

    dataframe = dynamic_frame.toDF()

    logger.info(
        "BATCH_JDBC_READ_READY source_table=%s",
        qualified_table,
    )

    return dataframe

# PREPARACIÓN DE BRONZE

def prepare_bronze_dataframe(
    dataframe: DataFrame,
    source_table: str,
    batch_id: Optional[str] = None,
) -> DataFrame:
    """
    Prepara el DataFrame para la capa Bronze.

    No realiza:
    - limpieza
    - deduplicación
    - anonimización
    - transformación de negocio
    - agregaciones

    Únicamente agrega metadata técnica de ingesta.
    """

    validate_source_table(
        source_table,
    )

    if batch_id is None:
        batch_id = str(uuid.uuid4())

    bronze_dataframe = (
        dataframe
        .withColumn(
            "_ingestion_timestamp",
            F.current_timestamp(),
        )
        .withColumn(
            "_source_table",
            F.lit(source_table),
        )
        .withColumn(
            "_batch_id",
            F.lit(batch_id),
        )
    )

    return bronze_dataframe

# VALIDACIÓN TABLA ICEBERG

def iceberg_table_exists(
    spark,
    catalog_name: str,
    database_name: str,
    table_name: str,
) -> bool:
    """
    Comprueba si una tabla Iceberg ya existe
    dentro del catálogo configurado.
    """

    validate_identifier(
        catalog_name,
        "catalog_name",
    )

    validate_identifier(
        database_name,
        "database_name",
    )

    validate_source_table(
        table_name,
    )

    table_identifier = (
        f"{catalog_name}."
        f"{database_name}."
        f"{table_name}"
    )

    return spark.catalog.tableExists(
        table_identifier
    )

# ESCRITURA BRONZE

def write_bronze_iceberg(
    spark,
    dataframe: DataFrame,
    database_name: str,
    table_name: str,
    catalog_name: str = "glue_catalog",
) -> None:
    """
    Escribe los datos Bronze utilizando Apache Iceberg.

    Si la tabla no existe:
        CREATE

    Si ya existe:
        APPEND

    Como la ingesta es full load, cada ejecución queda
    identificada mediante _batch_id.
    """

    validate_identifier(
        catalog_name,
        "catalog_name",
    )

    validate_identifier(
        database_name,
        "database_name",
    )

    validate_source_table(
        table_name,
    )

    target_table = (
        f"{catalog_name}."
        f"{database_name}."
        f"{table_name}"
    )

    logger.info(
        (
            "BRONZE_ICEBERG_WRITE_START "
            "target_table=%s"
        ),
        target_table,
    )

    table_exists = iceberg_table_exists(
        spark=spark,
        catalog_name=catalog_name,
        database_name=database_name,
        table_name=table_name,
    )

    writer = (
        dataframe
        .writeTo(target_table)
        .using("iceberg")
        .tableProperty(
            "format-version",
            "2",
        )
        .tableProperty(
            "write.format.default",
            "parquet",
        )
    )

    if table_exists:

        writer.append()

        logger.info(
            (
                "BRONZE_ICEBERG_APPEND_COMPLETE "
                "target_table=%s"
            ),
            target_table,
        )

    else:

        writer.create()

        logger.info(
            (
                "BRONZE_ICEBERG_CREATE_COMPLETE "
                "target_table=%s"
            ),
            target_table,
        )