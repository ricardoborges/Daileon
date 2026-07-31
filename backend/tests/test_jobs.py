"""Estado observável de um job de sincronização.

O polling da UI depende do contrato do cursor: cada resposta traz só o que o
cliente ainda não viu. Se `cursor` ou o filtro por `seq` escorregar, o console
duplica linhas ou perde linhas — sem erro nenhum aparecer.
"""
from app.sync.jobs import MAX_LOG_LINES, SyncJob


def _job() -> SyncJob:
    return SyncJob(id="abc123", mode="update")


def test_snapshot_inicial():
    job = _job()
    snap = job.snapshot()

    assert snap["state"] == "running"
    assert snap["total"] is None, "sem total, a UI mostra a barra indeterminada"
    assert snap["processed"] == 0
    assert snap["logs"] == []
    assert snap["cursor"] == 0


def test_cursor_entrega_cada_linha_uma_vez():
    job = _job()
    job.log("info", "primeira")
    job.log("ok", "segunda")

    primeira_leitura = job.snapshot(since=0)
    assert [l["message"] for l in primeira_leitura["logs"]] == ["primeira", "segunda"]

    # Nada novo desde então.
    assert job.snapshot(since=primeira_leitura["cursor"])["logs"] == []

    job.log("warn", "terceira")
    segunda_leitura = job.snapshot(since=primeira_leitura["cursor"])
    assert [l["message"] for l in segunda_leitura["logs"]] == ["terceira"]


def test_progresso_acompanha_os_passos():
    job = _job()
    job.set_total(3)
    job.advance()
    job.advance()

    snap = job.snapshot()
    assert (snap["processed"], snap["total"]) == (2, 3)


def test_log_e_truncado_mas_o_cursor_nao_regride():
    """O teto de memória não pode fazer o cliente reler linhas antigas."""
    job = _job()
    for i in range(MAX_LOG_LINES + 50):
        job.log("info", f"linha {i}")

    snap = job.snapshot(since=0)
    assert len(job.logs) == MAX_LOG_LINES
    assert snap["cursor"] == MAX_LOG_LINES + 50
    # As mais antigas caíram; as retidas mantêm o seq original.
    assert snap["logs"][0]["message"] == "linha 50"
    assert snap["logs"][0]["seq"] == 50
