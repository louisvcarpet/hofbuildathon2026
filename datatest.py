import os
from pyspark.sql import SparkSession
from dotenv import load_dotenv

load_dotenv()

# Databricks connection details from .env
SERVER_HOSTNAME = os.getenv("DATABRICKS_SERVER_HOSTNAME")
ACCESS_TOKEN = os.getenv("DATABRICKS_TOKEN")

def create_spark_session():
    """
    Create a Spark session connected to Databricks using Databricks Connect
    """
    spark = (
        SparkSession.builder
        .remote(f"sc://{SERVER_HOSTNAME}:443")
        .config("spark.databricks.service.token", ACCESS_TOKEN)
        .getOrCreate()
    )
    return spark


def query_databricks_table(spark, table_name):
    """
    Query a Unity Catalog table from Databricks
    """
    try:
        df = spark.sql(f"SELECT * FROM {table_name} LIMIT 10")

        print(f"\nTable: {table_name}")
        print(f"Rows Retrieved: {df.count()}")
        print("\nData:")
        df.show(10, truncate=False)

        return df

    except Exception as e:
        print(f"\n Error querying table {table_name}: {e}")
        return None


if __name__ == "__main__":
    print("Creating Spark session...")
    spark = create_spark_session()

    print("Connected to Databricks!")

    # ✅ Use full 3-level namespace (catalog.schema.table)
    table_name = "workspace.buildathon.market_data_intelligent"

    df = query_databricks_table(spark, table_name)

    if df is not None:
        print("\nSchema:")
        df.printSchema()

    spark.stop()
    print("END!")