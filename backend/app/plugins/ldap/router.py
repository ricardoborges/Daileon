from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.auth import get_current_user, LDAPConfigRequest
from app.plugins.ldap.service import (
    LDAPAuthService,
    get_effective_ldap_config,
    set_system_setting,
)

ldap_router = APIRouter(prefix="/plugins/ldap", tags=["ldap"])


@ldap_router.get("/config")
async def get_ldap_plugin_config(
    db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)
):
    config = await get_effective_ldap_config(db)
    res = dict(config)
    if res.get("bind_password"):
        res["bind_password"] = "******"
    return res


@ldap_router.post("/config")
async def save_ldap_plugin_config(
    payload: LDAPConfigRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    current = await get_effective_ldap_config(db)
    new_data = payload.model_dump()
    if new_data.get("bind_password") == "******":
        new_data["bind_password"] = current.get("bind_password", "")

    await set_system_setting(db, "ldap_config", new_data)
    return {"message": "Configurações do LDAP salvas com sucesso!"}


@ldap_router.post("/config/test")
async def test_ldap_plugin_config(
    payload: LDAPConfigRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    current = await get_effective_ldap_config(db)
    config = payload.model_dump()
    if config.get("bind_password") == "******":
        config["bind_password"] = current.get("bind_password", "")

    res = LDAPAuthService.test_connection(config)
    return res
