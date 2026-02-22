import os
from dotenv import load_dotenv
from databricks import sql

load_dotenv()

# Databricks connection details from .env
SERVER_HOSTNAME = os.getenv("DATABRICKS_SERVER_HOSTNAME")
HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")
ACCESS_TOKEN = os.getenv("DATABRICKS_TOKEN")

def connect_to_databricks():
    """
    Create a connection to Databricks SQL Warehouse
    """
    try:
        connection = sql.connect(
            server_hostname=SERVER_HOSTNAME,
            http_path=HTTP_PATH,
            personal_access_token=ACCESS_TOKEN
        )
        return connection
    except Exception as e:
        print(f"Connection error: {e}")
        return None


def query_databricks_table(connection, table_name):
    """
    Query a Unity Catalog table from Databricks and print the first 10 rows
    """
    try:
        cursor = connection.cursor()
        
        # Query the table with LIMIT 10
        query = f"SELECT * FROM {table_name} LIMIT 10"
        cursor.execute(query)
        
        # Fetch results
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        print(f"\nTable: {table_name}")
        print(f"Rows Retrieved: {len(results)}")
        print(f"Columns: {', '.join(columns)}")
        print("\n--- First 10 Rows ---")
        
        # Print header
        print(" | ".join(columns))
        print("-" * 80)
        
        # Print rows
        for row in results:
            print(" | ".join(str(val) for val in row))
        
        cursor.close()
        return results

    except Exception as e:
        print(f"Error querying table {table_name}: {e}")
        return None


if __name__ == "__main__":
    print("Connecting to Databricks warehouse...")
    
    connection = connect_to_databricks()
    
    if connection is None:
        print("Failed to connect. Please check your .env file with:")
        print("  DATABRICKS_SERVER_HOSTNAME=<your-server-hostname>")
        print("  DATABRICKS_HTTP_PATH=<your-http-path>")
        print("  DATABRICKS_TOKEN=<your-personal-access-token>")
    else:
        print("Connected to Databricks!")
        
        # Query the table
        table_name = "workspace.buildathon.market_data_intelligent"
        results = query_databricks_table(connection, table_name)
        
        connection.close()
        print("\nConnection closed!")
        print("END!")