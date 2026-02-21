import os
from pyspark.sql import SparkSession
from dotenv import load_dotenv

load_dotenv()

# Databricks connection details from .env
SERVER_HOSTNAME = os.getenv("DATABRICKS_SERVER_HOSTNAME")
HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")
ACCESS_TOKEN = os.getenv("DATABRICKS_TOKEN")

def create_spark_session():
    """
    Create a Spark session connected to Databricks
    """
    return SparkSession.builder \
        .appName("DatabricksQuery") \
        .config("spark.databricks.host", SERVER_HOSTNAME) \
        .config("spark.databricks.token", ACCESS_TOKEN) \
        .config("spark.databricks.cluster.profile", "singleNode") \
        .config("spark.master", "local[*]") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .getOrCreate()

def query_databricks_table(spark, table_name, limit=10):
    """
    Query a table from Databricks and display results
    """
    try:
        df = spark.sql(f"SELECT * FROM {table_name} LIMIT {limit}")
        print(f"\nTable: {table_name}")
        print(f"Rows: {df.count()}")
        print("\nData:")
        df.show(limit, truncate=False)
        return df
    except Exception as e:
        print(f"Error querying table {table_name}: {e}")
        return None

if __name__ == "__main__":
    print("Creating Spark session...")
    spark = create_spark_session()
    
    print("Connecting to Databricks...")
    
    # Query the buildathonoffers table
    table_name = "default.buildathonoffers"
    df = query_databricks_table(spark, table_name, limit=10)
    
    if df:
        print(f"\nSchema:")
        df.printSchema()
    
    spark.stop()
    print("\nDone!")
        
    


