"""Execução das operações de catálogo em segundo plano.

O crawl do GitLab leva minutos e a UI precisa mostrar progresso enquanto ele
roda, então a requisição não pode segurá-lo até o fim. O endpoint dispara um
job e devolve na hora; a UI acompanha por polling em `/sync/status`.

O estado vive em memória, num único slot: só uma operação de catálogo pode
rodar por vez (elas escrevem nas mesmas tabelas) e o histórico não precisa
sobreviver a um restart do processo.
"""
import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.db.session import AsyncSessionLocal
from app.gitlab.gitlab_crawler import GitLabCrawlerService, SyncMode

logger = logging.getLogger(__name__)

# Teto de linhas retidas: um rebuild de milhares de projetos não pode crescer
# sem limite na memória do processo.
MAX_LOG_LINES = 2000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LogLine:
    seq: int
    ts: str
    level: str  # info | ok | warn | error
    message: str


class SyncAlreadyRunning(RuntimeError):
    def __init__(self, mode: str):
        super().__init__(f"Já existe uma operação em andamento ({mode}).")
        self.mode = mode


@dataclass
class SyncJob:
    """Estado observável de uma operação. Também é o `SyncProgress` do crawler."""

    id: str
    mode: str
    state: str = "running"  # running | success | partial | error
    # `None` enquanto a contagem de passos é desconhecida — a UI mostra a barra
    # em modo indeterminado até a listagem de projetos voltar.
    total: Optional[int] = None
    processed: int = 0
    started_at: str = field(default_factory=_now)
    finished_at: Optional[str] = None
    synced: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    failures: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    logs: List[LogLine] = field(default_factory=list)
    _next_seq: int = 0

    # -- SyncProgress ----------------------------------------------------
    def log(self, level: str, message: str) -> None:
        self.logs.append(LogLine(seq=self._next_seq, ts=_now(), level=level, message=message))
        self._next_seq += 1
        excess = len(self.logs) - MAX_LOG_LINES
        if excess > 0:
            del self.logs[:excess]

    def set_total(self, total: int) -> None:
        self.total = total

    def advance(self) -> None:
        self.processed += 1

    # -- Leitura ---------------------------------------------------------
    def snapshot(self, since: int = 0) -> Dict[str, Any]:
        """Estado atual + apenas as linhas de log ainda não entregues.

        `cursor` é o `since` da próxima chamada: sem isso cada poll reenviaria
        o log inteiro.
        """
        return {
            "job_id": self.id,
            "mode": self.mode,
            "state": self.state,
            "total": self.total,
            "processed": self.processed,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "synced_count": len(self.synced),
            "removed_count": len(self.removed),
            "failed_count": len(self.failures),
            "failures": self.failures,
            "error": self.error,
            "cursor": self._next_seq,
            "logs": [
                {"seq": l.seq, "ts": l.ts, "level": l.level, "message": l.message}
                for l in self.logs
                if l.seq >= since
            ],
        }


class SyncJobRegistry:
    def __init__(self) -> None:
        self._job: Optional[SyncJob] = None
        # Referência forte à task: sem ela o GC pode coletar uma task em voo.
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    @property
    def current(self) -> Optional[SyncJob]:
        return self._job

    async def start(self, mode: SyncMode) -> SyncJob:
        async with self._lock:
            if self._job and self._job.state == "running":
                raise SyncAlreadyRunning(self._job.mode)

            job = SyncJob(id=uuid.uuid4().hex[:12], mode=mode.value)
            job.log("info", f"Operação iniciada: {mode.value}")
            self._job = job
            self._task = asyncio.create_task(self._run(job, mode))
            return job

    async def _run(self, job: SyncJob, mode: SyncMode) -> None:
        crawler = GitLabCrawlerService()
        try:
            # Sessão própria: a do request morre assim que o endpoint responde.
            async with AsyncSessionLocal() as db:
                result = await crawler.run(db, mode=mode, progress=job)

            job.synced = result.synced
            job.removed = result.removed
            job.failures = [
                {"project_id": f.project_id, "name": f.name, "error": f.error}
                for f in result.failed
            ]
            job.state = "partial" if result.failed else "success"
            job.log(
                "warn" if result.failed else "ok",
                f"Concluído: {len(result.synced)} sincronizado(s), "
                f"{len(result.removed)} removido(s), {len(result.failed)} com falha.",
            )
        except Exception as e:
            job.state = "error"
            job.error = str(e)
            job.log("error", f"Operação abortada: {e}")
            logger.exception("Sync job %s (%s) failed", job.id, mode.value)
        finally:
            job.finished_at = _now()


sync_jobs = SyncJobRegistry()
