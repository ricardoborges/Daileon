"""Isolamento da suíte de testes.

As settings são resolvidas no momento em que `app.core.config` é importado,
então o `DATABASE_URL` precisa ser definido aqui — antes de qualquer import de
`app.*` ou `main`. Sem isso, os testes gravam no banco de desenvolvimento
(`backend/daileon.db`).
"""
import os
import shutil
import tempfile
from pathlib import Path

import pytest

_TMP_DIR = tempfile.mkdtemp(prefix="daileon-tests-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(Path(_TMP_DIR) / 'test.db').as_posix()}"


@pytest.fixture(scope="session", autouse=True)
def _cleanup_temp_db():
    yield
    # ignore_errors: no Windows o arquivo pode continuar travado pelo driver.
    shutil.rmtree(_TMP_DIR, ignore_errors=True)
