import logging
import sys
import uuid

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext

from bronze_ingestion_core import (
    prepare_bronze_dataframe,
    read_postgresql_table,
    write_bronze_iceberg,
)

# LOGGING

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s "
        "%(levelname)s "
        "%(name)s - "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    "batch.bronze.glue"
)

# ARGUMENTOS OPCIONALES

def get_optional_argument(
    argument_name: str,
    default=None,
):
    """
    Obtiene argumentos opcionales enviados al Glue Job.

    Ejemplo:

    --write_enabled false
    """

    flag = f"--{argument_name}"

    if flag not in sys.argv:
        return default

    position = sys.argv.index(flag)

    if position + 1 >= len(sys.argv):
        raise ValueError(
            f"Missing value for argument {flag}"
        )

    return sys.argv[position + 1]


def str_to_bool(
    value: str,
) -> bool:
    """
    Convierte un valor recibido como argumento
    a booleano.
    """

    return str(value).strip().lower() in {
        "true",
        "1",
        "yes",
        "y",
    }


def main():
    args = getResolvedOptions(
        sys.argv,
        [
            "JOB_NAME",
            "connection_name",
            "source_schema",
            "source_table",
        ],
    )

    connection_name = (
        args["connection_name"]
    )

    source_schema = (
        args["source_schema"]
    )

    source_table = (
        args["source_table"]
    )

    # Parámetros opcionales

    write_enabled = str_to_bool(
        get_optional_argument(
            "write_enabled",
            "false",
        )
    )

    target_database = (
        get_optional_argument(
            "target_database"
        )
    )

    catalog_name = (
        get_optional_argument(
            "catalog_name",
            "glue_catalog",
        )
    )

    batch_id = str(
        uuid.uuid4()
    )

    spark_context = (
        SparkContext.getOrCreate()
    )

    glue_context = GlueContext(
        spark_context
    )

    spark = (
        glue_context.spark_session
    )

    job = Job(
        glue_context
    )

    job.init(
        args["JOB_NAME"],
        args,
    )

    logger.info(
        (
            "BRONZE_BATCH_INGESTION_START "
            "table=%s "
            "schema=%s "
            "batch_id=%s"
        ),
        source_table,
        source_schema,
        batch_id,
    )

    # 1. EXTRACCIÓN

    source_dataframe = (
        read_postgresql_table(
            glue_context=glue_context,
            connection_name=connection_name,
            source_schema=source_schema,
            source_table=source_table,
        )
    )

    logger.info(
        (
            "SOURCE_DATA_EXTRACTED "
            "table=%s "
            "batch_id=%s"
        ),
        source_table,
        batch_id,
    )

    # 2. PREPARACIÓN BRONZE

    bronze_dataframe = (
        prepare_bronze_dataframe(
            dataframe=source_dataframe,
            source_table=source_table,
            batch_id=batch_id,
        )
    )

    logger.info(
        (
            "BRONZE_DATA_PREPARED "
            "table=%s "
            "batch_id=%s"
        ),
        source_table,
        batch_id,
    )

    # 3. ESCRITURA

    if write_enabled:

        if not target_database:
            raise ValueError(
                "--target_database is required "
                "when --write_enabled=true."
            )

        write_bronze_iceberg(
            spark=spark,
            dataframe=bronze_dataframe,
            database_name=target_database,
            table_name=source_table,
            catalog_name=catalog_name,
        )

        logger.info(
            (
                "BRONZE_WRITE_COMPLETE "
                "table=%s "
                "batch_id=%s"
            ),
            source_table,
            batch_id,
        )

    else:

        logger.warning(
            (
                "BRONZE_WRITE_SKIPPED "
                "table=%s "
                "batch_id=%s "
                "reason=write_enabled_false"
            ),
            source_table,
            batch_id,
        )


    job.commit()

    logger.info(
        (
            "BRONZE_BATCH_INGESTION_COMPLETE "
            "table=%s "
            "batch_id=%s"
        ),
        source_table,
        batch_id,
    )


if __name__ == "__main__":
    main()