from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.inspection import inspect
from typing import AsyncGenerator
import hashlib

DB_NAME = 'project_pog'
#-----------------------------
# All Required table Names...

employee_table = 'employee_table'
project_data = 'project_table'
project_assignment_table = 'project_assignment_table'
project_codebase = 'project_codebase'
login_log_table = 'login_log_table'
project_updates_table = 'project_updates_table'
project_master_table = 'project_master_table'
todo_assignment_table = 'todo_assignment_table'
todo_esclation_table = 'todo_esclation_table'
todo_master_table = 'todo_master_table'
#---------------------------


# Example: "postgresql+asyncpg://username:password@localhost:5432/dbname"
DATABASE_URL = f"postgresql+asyncpg://postgres:actowiz@localhost:5432/{DB_NAME}"
# DATABASE_URL = f"mysql+aiomysql://root:actowiz@localhost:3306/{DB_NAME}"



# --------------------------
# 1. Create async engine with pool size
# --------------------------
engine = create_async_engine(
    DATABASE_URL,
    echo=False,              # Set True for SQL logs
    pool_size=10,            # Number of connections to keep in the pool
    max_overflow=10,         # Extra connections beyond pool_size
    pool_timeout=30,         # Seconds to wait for a connection
    pool_recycle=1800,       # Recycle connections every 30 minutes
    future=True
)

# --------------------------
# 2. Create session factory
# --------------------------
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# --------------------------
# 3. Dependency for FastAPI
# --------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


# --------------------------
# 4. To generate hash text.
# --------------------------
def hash_string(input_string):
    encoded_string = str(input_string).encode('utf-8')
    sha256_hash = hashlib.sha256(encoded_string)
    return sha256_hash.hexdigest()


# --------------------------
# 5. To Get User's Ip address
# --------------------------
def get_client_ip(request) -> str:
    try:
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.client.host
        return ip
    except:
        return 'N/A'

def orm_to_dict(obj):
    return {c.key: getattr(obj, c.key) for c in inspect(obj).mapper.column_attrs}

def orm_to_dict_2(obj):
    return {col.name: getattr(obj, col.name) for col in obj.__table__.columns}
