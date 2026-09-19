import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

def migrate():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set")
        return
    
    with open("database/migrations/001_lane5_vector_schema.sql", "r") as f:
        sql = f.read()
        
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    print("Migration applied successfully.")

if __name__ == "__main__":
    migrate()
