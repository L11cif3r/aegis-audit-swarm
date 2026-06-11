# backend/database.py
import os, ssl
import databases
import sqlalchemy
from dotenv import load_dotenv

load_dotenv()

RAW_URL = os.getenv('DATABASE_URL')  
# Convert to asyncpg-compatible scheme
ASYNC_URL = RAW_URL.replace('postgresql://', 'postgresql+asyncpg://')

# SSL context — bypasses Supabase self-signed cert
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

database = databases.Database(ASYNC_URL, ssl=ssl_ctx)

metadata = sqlalchemy.MetaData()

audit_logs = sqlalchemy.Table(
    'audit_logs', metadata,
    sqlalchemy.Column('id',            sqlalchemy.String,  primary_key=True),
    sqlalchemy.Column('timestamp',     sqlalchemy.String),
    sqlalchemy.Column('agent',         sqlalchemy.String),
    sqlalchemy.Column('prompt',        sqlalchemy.Text),
    sqlalchemy.Column('response',      sqlalchemy.Text),
    sqlalchemy.Column('model',         sqlalchemy.String),
    sqlalchemy.Column('cost',          sqlalchemy.String),
    sqlalchemy.Column('input_tokens',  sqlalchemy.Integer),
    sqlalchemy.Column('output_tokens', sqlalchemy.Integer),
    sqlalchemy.Column('status',        sqlalchemy.String),
    sqlalchemy.Column('threat_type',   sqlalchemy.String, nullable=True),
)

# Sync engine for create_tables only — uses psycopg2
SYNC_URL = RAW_URL  # plain postgresql:// is fine for psycopg2
engine = sqlalchemy.create_engine(
    SYNC_URL,
    connect_args={"sslmode": "require", "sslrootcert": "disable"}
)

def create_tables():
    metadata.create_all(engine)