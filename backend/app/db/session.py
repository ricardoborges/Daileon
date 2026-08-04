from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True
)


if engine.dialect.name == "sqlite":
    @event.listens_for(engine.sync_engine, "connect")
    def _apply_sqlite_pragmas(dbapi_connection, _connection_record):
        """Configura cada conexão nova; os PRAGMAs não são persistentes.

        Os padrões do SQLite são conservadores para um banco de arquivo único
        acessado por um processo só, que é o nosso caso: o modo `delete` do
        journal reescreve e sincroniza o arquivo a cada commit, e o cache de
        2 MB não cobre nem uma fração do banco.
        """
        cursor = dbapi_connection.cursor()
        # WAL deixa leitura e escrita concorrerem — sem ele, o sync (que
        # escreve por minutos) bloqueia toda a API.
        cursor.execute("PRAGMA journal_mode=WAL")
        # Com WAL, `NORMAL` só arrisca as transações do último checkpoint em
        # caso de queda do SO, e não corrupção. O catálogo é reconstruível a
        # partir do GitLab; o fsync por commit não se paga.
        cursor.execute("PRAGMA synchronous=NORMAL")
        # 64 MB de cache e 256 MB de mmap: o banco é dominado por documentos
        # binários, e sem isso toda leitura volta ao disco.
        cursor.execute("PRAGMA cache_size=-64000")
        cursor.execute("PRAGMA mmap_size=268435456")
        cursor.execute("PRAGMA temp_store=MEMORY")
        # Espera o sync liberar o banco em vez de devolver "database is locked".
        cursor.execute("PRAGMA busy_timeout=10000")
        cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
