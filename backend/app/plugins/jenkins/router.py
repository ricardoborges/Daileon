from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import Component
from app.api.auth import get_current_user
from app.core.config import settings
from app.plugins.jenkins.service import fetch_jenkins_job_status

jenkins_router = APIRouter(tags=["jenkins"])

@jenkins_router.get("/catalog/{component_id}/jenkins", dependencies=[Depends(get_current_user)])
async def get_component_jenkins_status(component_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Component).where(Component.id == component_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Component not found")
    
    pipelines_status = []
    for pipe in c.jenkins_pipelines:
        status_info = await fetch_jenkins_job_status(pipe.job, server_url=pipe.server_url)
        pipelines_status.append({
            "id": pipe.id,
            "name": pipe.name,
            "environment": pipe.environment,
            "job": pipe.job,
            "server_url": pipe.server_url,
            "status_info": status_info
        })

    return {
        "component_id": c.id,
        "component_name": c.name,
        "jenkins_token_configured": bool(settings.JENKINS_API_TOKEN or settings.JENKINS_USER),
        "pipelines": pipelines_status
    }
