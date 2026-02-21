from databricks import sql

SERVER_HOSTNAME = "..."
HTTP_PATH = "..."
ACCESS_TOKEN = "..."

def run_query(query):
    with sql.connect(
        server_hostname=SERVER_HOSTNAME,
        http_path=HTTP_PATH,
        access_token=ACCESS_TOKEN,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchall()