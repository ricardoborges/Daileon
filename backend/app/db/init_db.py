import logging
from sqlalchemy import inspect, text

from app.db.session import Base
# `Base.metadata` só conhece as tabelas dos modelos já importados. Sem esta
# linha, chamar `auto_migrate_db` antes de algo que importe os modelos percorre
# um metadata vazio e migra nada, em silêncio.
import app.db.models  # noqa: F401

logger = logging.getLogger(__name__)


def auto_migrate_db(sync_conn):
    """Aproxima o schema de um banco existente do que os modelos declaram.

    `Base.metadata.create_all` só cria tabelas que ainda não existem — ele não
    toca em nada que já esteja lá. Sem esta função, toda mudança de modelo só
    valeria para instalações novas.
    """
    inspector = inspect(sync_conn)
    existing_tables = inspector.get_table_names()

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            continue
        _add_missing_columns(sync_conn, inspector, table_name, table)
        _create_missing_indexes(sync_conn, inspector, table_name, table)
        _reconcile_index_uniqueness(sync_conn, inspector, table_name, table)


def _create_missing_indexes(sync_conn, inspector, table_name, table):
    """Cria índices que o modelo declara e o banco ainda não tem.

    `create_all` não volta em tabelas existentes, então um índice adicionado ao
    modelo depois da instalação nunca chegaria a um banco em uso — que é
    justamente onde ele faz falta.
    """
    existing = {idx.get("name") for idx in inspector.get_indexes(table_name)}
    for index in table.indexes:
        if not index.name or index.name in existing:
            continue
        logger.info(f"Auto-migrating DB: Creating missing index '{index.name}' on '{table_name}'")
        index.create(sync_conn)


def _add_missing_columns(sync_conn, inspector, table_name, table):
    existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
    for column in table.columns:
        if column.name in existing_columns:
            continue
        col_type = column.type.compile(sync_conn.dialect)
        logger.info(
            f"Auto-migrating DB: Adding missing column '{column.name}' ({col_type}) to table '{table_name}'"
        )
        sync_conn.execute(
            text(f'ALTER TABLE "{table_name}" ADD COLUMN "{column.name}" {col_type}')
        )


def _reconcile_index_uniqueness(sync_conn, inspector, table_name, table):
    """Recria índices cuja unicidade divergiu do modelo.

    O caso que motivou isto: `components.gitlab_project_id` era UNIQUE quando
    um repositório correspondia a exatamente um componente. O suporte a
    monorepo (vários `project-info.yml` no mesmo repositório) removeu a
    restrição do modelo, mas bancos criados antes disso continuaram com o
    índice único e passaram a falhar no sync com IntegrityError.
    """
    model_indexes = {idx.name: idx for idx in table.indexes if idx.name}

    for db_index in inspector.get_indexes(table_name):
        name = db_index.get("name")
        model_index = model_indexes.get(name)
        # Índice que o modelo não declara é de alguém mais: não mexemos.
        if not name or model_index is None:
            continue
        if bool(db_index.get("unique")) == bool(model_index.unique):
            continue

        # Índice implícito de uma restrição UNIQUE escrita no CREATE TABLE.
        # O SQLite não permite removê-lo sem reconstruir a tabela, o que não
        # cabe fazer automaticamente com os dados do usuário em jogo.
        if name.startswith("sqlite_autoindex_"):
            logger.error(
                f"Column of table '{table_name}' carries an inline UNIQUE constraint "
                f"('{name}') that no longer matches the model. It cannot be dropped "
                f"automatically in SQLite; the table needs to be rebuilt manually."
            )
            continue

        logger.info(
            f"Auto-migrating DB: Recreating index '{name}' on '{table_name}' "
            f"as {'UNIQUE' if model_index.unique else 'non-unique'}"
        )
        sync_conn.execute(text(f'DROP INDEX "{name}"'))
        model_index.create(sync_conn)
