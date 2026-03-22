from fastapi import FastAPI, Response, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from libs.config_loader import settings
from libs.auth import ygg_meta, ygg_auth, ygg_seesion
from libs.skin import create_csl_data
from libs.utils import reg_figura_uuid, validate_figura_data, link_server_profile, check_player_name, server_player_rename, server_player_rstname
from libs.model import PostFiguraUUID, LinkProfile, Rename, OfflineReg, OfflineLog, OfflineChpass
from libs.offline_auth import offline_reg, offline_login, offline_check, offline_chpsswd
from typing import Optional
from fastapi.responses import FileResponse
from pathlib import Path
import uvicorn

app=FastAPI()
security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    校验 Token 的依赖项函数
    """
    if credentials.credentials != settings.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Bearer Token",
            headers={"WWW+Authenticate": "Bearer"},
        )
    return credentials.credentials

@app.get("/")
def root():
    return {"message": "Hello World"}

@app.get("/auth")
async def get_ygg_meta():
    data = await ygg_meta()
    return data

@app.get("/auth/sessionserver/session/minecraft/hasJoined")
async def get_ygg_auth(
    username: str,
    serverId: str,
    ip: Optional[str] = None
):
    resp = await ygg_auth(username, serverId, ip)
    if not resp:
        return Response(status_code=204)
    return resp

@app.get("/auth/sessionserver/session/minecraft/profile/{uuid}")
async def get_ygg_profile(
    uuid: str,
):
    resp = await ygg_seesion(uuid)
    if not resp:
        return Response(status_code=204)
    return resp

@app.get("/auth/api/users/profiles/minecraft/{username}")
async def check_ygg_name(username: str):
    resp = await check_player_name(username)
    if not resp:
        return Response(status_code=204)
    return resp
    
@app.get("/csl/{username}")
async def get_csl_data(username: str):
    final_name = username.replace(".json","")
    csl_data = await create_csl_data(final_name)
    if not csl_data:
        raise HTTPException(
            status_code=404, 
            detail={"message": "未找到该玩家或该玩家没有皮肤"}
        )
    return csl_data

@app.get("/textures/{texture_hash}")
async def get_texture_file(texture_hash: str):
    file_path = Path("textures") / texture_hash
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=404, 
            detail={"message": "未找到材质"}
        )
    
    return FileResponse(
        path=file_path, 
        media_type="image/png"
    )
    
@app.get("/figura/hasJoined")
async def figura_auth(username: str):
    resp = await validate_figura_data(username)
    if not resp:
        raise HTTPException(
            status_code=403, 
            detail={"message": "Figura 验证失败，可能该玩家没有进过服"}
        )
    return resp

@app.post("/figura/register")
async def figura_reg(data: PostFiguraUUID, token: str = Depends(verify_token)):
    await reg_figura_uuid(data.uuid, data.username)
    return {"message": "操作成功"}

@app.post("/profile/linkprofile")
async def link_profile(data: LinkProfile, token: str = Depends(verify_token)):
    resp = await link_server_profile(data.uuid, data.new_uuid)
    if not resp:
        raise HTTPException(
            status_code=400, 
            detail={"message": "数据迁移失败，可能该玩家没有进过服"}
        )
    return {"message": "操作成功"}

@app.post("/profile/rename")
async def profile_rename(data: Rename, token: str = Depends(verify_token)):
    resp = await server_player_rename(data.uuid, data.username)
    if not resp:
        raise HTTPException(
            status_code=400, 
            detail={"message": "改名失败，可能该玩家名已存在"}
        )
    return {"message": "操作成功"}

@app.get("/profile/rstname/{uuid}")
async def profile_rstname(uuid: str, token: str = Depends(verify_token)):
    await server_player_rstname(uuid)
    return {"message": "操作成功"}

@app.get("/offline/check/{username}")
async def check_offline_name(username: str, token: str = Depends(verify_token)):
    resp = await offline_check(username)
    if resp.get("code") != 200:
        raise HTTPException(
            status_code=resp.get("code"), 
            detail={"message": resp.get("msg")}
        )
    return {"message": resp.get("msg")}

@app.post("/offline/reg")
async def offline_mode_reg(data: OfflineReg, token: str = Depends(verify_token)):
    print(data)
    resp = await offline_reg(data.username, data.passwd, data.repasswd, data.ip)
    if resp.get("code") != 200:
        raise HTTPException(
            status_code=resp.get("code"), 
            detail={"message": resp.get("msg")}
        )
    return {"message":  resp.get("msg")}

@app.post("/offline/login")
async def offline_mode_login(data: OfflineLog, token: str = Depends(verify_token)):
    resp = await offline_login(data.username, data.passwd)
    if resp.get("code") != 200:
        raise HTTPException(
            status_code=resp.get("code"), 
            detail={"message": resp.get("msg")}
        )
    return {"message":  resp.get("msg")}

@app.post("/offline/chpasswd")
async def offline_mode_chpasswd(data: OfflineChpass, token: str = Depends(verify_token)):
    resp = await offline_chpsswd(data.username, data.passwd, data.newpasswd)
    if resp.get("code") != 200:
        raise HTTPException(
            status_code=resp.get("code"), 
            detail={"message": resp.get("msg")}
        )
    return {"message":  resp.get("msg")}

@app.get("/check_token")
async def check_token(token: str = Depends(verify_token)):
    return {"message":  "验证通过"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host=settings.server.get('host', '0.0.0.0'),
        port=settings.server.get('port', 8000),
        reload=settings.server.get('debug', True),
    )