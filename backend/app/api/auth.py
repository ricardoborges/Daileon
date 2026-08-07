import json
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.session import get_db
from app.db.models import SystemSetting
from app.plugins.ldap import LDAPAuthService

auth_router = APIRouter(prefix="/auth", tags=["auth"])

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

class LoginRequest(BaseModel):
    username: str
    password: str

class LDAPConfigRequest(BaseModel):
    enabled: bool = False
    server_host: str = ""
    server_port: int = 389
    use_ssl: bool = False
    bind_dn: str = ""
    bind_password: str = ""
    base_dn: str = ""
    user_attribute: str = "uid"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_system_setting(db: AsyncSession, key: str) -> Optional[dict]:
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting and setting.value:
        try:
            return json.loads(setting.value)
        except Exception:
            return None
    return None

async def set_system_setting(db: AsyncSession, key: str, value: dict):
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == key))
    setting = result.scalar_one_or_none()
    json_str = json.dumps(value)
    if setting:
        setting.value = json_str
    else:
        setting = SystemSetting(key=key, value=json_str)
        db.add(setting)
    await db.commit()

async def get_effective_ldap_config(db: AsyncSession) -> dict:
    config = await get_system_setting(db, "ldap_config")
    if config is not None:
        return config

    default_config = {
        "enabled": settings.LDAP_ENABLED,
        "server_host": settings.LDAP_SERVER_HOST,
        "server_port": settings.LDAP_SERVER_PORT,
        "use_ssl": settings.LDAP_USE_SSL,
        "bind_dn": settings.LDAP_BIND_DN,
        "bind_password": settings.LDAP_BIND_PASSWORD,
        "base_dn": settings.LDAP_BASE_DN,
        "user_attribute": settings.LDAP_USER_ATTRIBUTE or "uid"
    }

    if settings.LDAP_SERVER_HOST or settings.LDAP_ENABLED:
        await set_system_setting(db, "ldap_config", default_config)

    return default_config

@auth_router.post("/login")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    username = payload.username.strip()
    password = payload.password

    if not username or not password:
        raise HTTPException(status_code=400, detail="Usuário e senha são obrigatórios.")

    # 1. Checa se é o usuário Break-Glass (Admin das Variáveis de Ambiente)
    if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
        token_data = {
            "sub": username,
            "name": "Admin (Break Glass)",
            "is_admin": True,
            "auth_type": "break_glass"
        }
        access_token = create_access_token(token_data)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "username": username,
                "name": "Admin (Break Glass)",
                "is_admin": True,
                "auth_type": "break_glass"
            }
        }

    # 2. Tenta autenticação via LDAP
    ldap_config = await get_effective_ldap_config(db)
    if not ldap_config.get("enabled", False):
        raise HTTPException(
            status_code=401,
            detail="Credenciais inválidas"
        )

    auth_result = LDAPAuthService.authenticate(ldap_config, username, password)
    if not auth_result.get("success"):
        raise HTTPException(
            status_code=401,
            detail=auth_result.get("message", "Credenciais de LDAP inválidas.")
        )

    user_info = auth_result.get("user", {})
    token_data = {
        "sub": username,
        "name": user_info.get("name", username),
        "email": user_info.get("email", ""),
        "is_admin": False,
        "auth_type": "ldap"
    }
    access_token = create_access_token(token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "username": username,
            "name": user_info.get("name", username),
            "email": user_info.get("email", ""),
            "is_admin": False,
            "auth_type": "ldap"
        }
    }

def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária para acessar esta informação.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ")[1]
    return decode_access_token(token)

@auth_router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {
        "username": user.get("sub"),
        "name": user.get("name"),
        "email": user.get("email", ""),
        "is_admin": user.get("is_admin", False),
        "auth_type": user.get("auth_type", "ldap")
    }

@auth_router.get("/ldap-config")
async def get_ldap_config(db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    config = await get_effective_ldap_config(db)
    res = dict(config)
    # Oculta senha do Bind DN ao retornar para a UI
    if res.get("bind_password"):
        res["bind_password"] = "******"
    return res

@auth_router.post("/ldap-config")
async def update_ldap_config(payload: LDAPConfigRequest, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    current_config = await get_effective_ldap_config(db)
    new_data = payload.model_dump()
    
    # Se a senha for enviada como máscara '******', mantém a senha original gravada
    if new_data.get("bind_password") == "******":
        new_data["bind_password"] = current_config.get("bind_password", "")

    await set_system_setting(db, "ldap_config", new_data)
    return {"message": "Configurações do LDAP salvas com sucesso!"}

@auth_router.post("/ldap-config/test")
async def test_ldap_config(payload: LDAPConfigRequest, db: AsyncSession = Depends(get_db), user: dict = Depends(get_current_user)):
    current_config = await get_effective_ldap_config(db)
    data = payload.model_dump()

    if data.get("bind_password") == "******":
        data["bind_password"] = current_config.get("bind_password", "")

    result = LDAPAuthService.test_connection(data)
    return result
