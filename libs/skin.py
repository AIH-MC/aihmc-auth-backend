from libs.config_loader import settings
from pathlib import Path
from libs.database import Database
from urllib.parse import urlparse
import tldextract
import httpx
import json
import base64
import asyncio

db = Database()

def parse_mojang_textures(resp_dict):
    textures_item = next((p for p in resp_dict.get("properties", []) if p.get("name") == "textures"), None)
    if not textures_item:
        return None, None, None

    try:
        decoded_data = json.loads(base64.b64decode(textures_item["value"]))
        textures = decoded_data.get("textures", {})
        
        skin_info = textures.get("SKIN", {})
        skin_url = skin_info.get("url")
        if skin_url is None:
            skin_hash = None
        else:
            skin_hash = skin_url.split('/')[-1].replace(".png","")
        model = skin_info.get("metadata", {}).get("model", "default") # 默认 Alex 为 slim，Steve 为 default
        
        cape_info = textures.get("CAPE", {})
        cape_url = cape_info.get("url")
        if cape_url is None:
            cape_hash = None
        else:
            cape_hash = cape_url.split('/')[-1].replace(".png","")
        
        return skin_hash, cape_hash, model
    except Exception as e:
        print(f"解析错误: {e}")
        return None, None, None
    
def parse_csl_json(resp_dict):
    skins = resp_dict.get("skins", {})
    
    skin_hash = None
    model_type = "default"
    
    if skins:
        model_type, skin_hash = next(iter(skins.items()))
    
    cape_hash = resp_dict.get("cape")
    
    return skin_hash, cape_hash, model_type

async def send_data(url):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            return False
        else:
            return resp.json()
        
async def cache_texture(texture_url, api_id):
    cache_base = Path("textures")
    cache_base.mkdir(parents=True, exist_ok=True)

    texture_hash = texture_url.split("/")[-1]
    file_path = cache_base / texture_hash

    if file_path.exists():
        print(f"📦 {texture_hash} 已存在，跳过下载")
        return True

    print(f"🌐 正在从 {api_id} 下载材质: {texture_url}")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(texture_url, timeout=10.0)
            if resp.status_code == 200:
                file_path.write_bytes(resp.content)
                print(f"✅ 材质已缓存至: {file_path}")
                return file_path
        except Exception as e:
            print(f"❌ 下载失败: {e}")
    
    return False

async def save_skin_data(username, cape, skin, model_type):
    sql = """
    INSERT INTO skins (username, cape_hash, skin_hash, model_type)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE 
    username=%s, cape_hash=%s, skin_hash=%s, model_type=%s
"""
    await db.execute(sql, 
        username, cape, skin, model_type,  # 对应 VALUES
        username, cape, skin, model_type   # 对应 UPDATE
    )
    
async def read_skin_data(username):
    res = await db.query("SELECT * FROM skins WHERE username = %s", username)
    data = res[0]
    if not res:
        return None, None, None, None
    return data.get("username"), data.get("cape_hash"), data.get("skin_hash"), data.get("model_type")
        
async def request_skin_api(protocol, url, username, apitype, api_id):
    skin, cape, model = None, None, "default"

    if apitype == "mojang":
        resp1 = await send_data(f"{protocol}://api.{url}/users/profiles/minecraft/{username}")
        if resp1:
            uuid = resp1.get("id")
            resp2 = await send_data(f"{protocol}://sessionserver.{url}/session/minecraft/profile/{uuid}")
            if resp2:
                skin, cape, model = parse_mojang_textures(resp2)

    elif apitype == "aihmc":
        resp = await send_data(f"{protocol}://skin.{url}/csl/{username}.json")
        if resp:
            skin, cape, model = parse_csl_json(resp)
            
    elif apitype == "blessingskin" :
        resp = await send_data(f"{protocol}://{url}/csl/{username}.json")
        if resp:
            skin, cape, model = parse_csl_json(resp)

    elif apitype == "elyby":
        resp = await send_data(f"{protocol}://authserver.{url}/api/users/profiles/minecraft/{username}")
        if resp:
            skin, cape, model = parse_mojang_textures(resp)

    if not skin and not cape:
        return False

    download_tasks = []
    
    if apitype == "official" or apitype == "elyby":
        if skin: download_tasks.append(cache_texture(f"{protocol}://textures.minecraft.net/texture/{skin}", api_id))
        if cape: download_tasks.append(cache_texture(f"{protocol}://textures.minecraft.net/texture/{cape}", api_id))
        if apitype == "elyby":
            if skin: download_tasks.append(cache_texture(f"{protocol}://{url}/storage/skins/{skin}", api_id))
            if cape: download_tasks.append(cache_texture(f"{protocol}://{url}/storage/skins/{cape}", api_id))
            
    elif apitype == "aihmc":
        if skin: download_tasks.append(cache_texture(f"{protocol}://skin.{url}/textures/{skin}", api_id))
        if cape: download_tasks.append(cache_texture(f"{protocol}://skin.{url}/textures/{cape}", api_id))
        
    
    elif apitype == "blessingskin":
        if skin: download_tasks.append(cache_texture(f"{protocol}://{url}/textures/{skin}", api_id))
        if cape: download_tasks.append(cache_texture(f"{protocol}://{url}/textures/{cape}", api_id))

    if download_tasks:
        await asyncio.gather(*download_tasks)

    await save_skin_data(username, cape, skin, model)
    
    res_data = await read_skin_data(username)
    if res_data[0] is None:
        return False
    skin_username, cape_hash, skin_hash, model_type = res_data
    
    csl_data = {
        "username": skin_username,
        "skins": {
            model_type: skin_hash
        }
    }
    
    if cape_hash:
        csl_data["cape"] = cape_hash
    
    return csl_data

async def create_csl_data(username):
    for skin_api in settings.servers:
        current_name = skin_api.get("name")
        current_type = skin_api.get("api_type")
        current_url = skin_api.get("root_url")
        extracted = tldextract.extract(current_url)
        root_domain = f"{extracted.domain}.{extracted.suffix}"
        protocol = urlparse(current_url).scheme
        
        enabled = skin_api.get("enabled", True)
        if not enabled:
            print(f"❌ 玩家 {username} 通过途径 {current_name} 获取皮肤失败，原因：已关闭。正在尝试下一个...")
            continue
        
        respdata = await request_skin_api(protocol, root_domain, username, current_type, current_name)
        
        if respdata:
            print(f"✅ 玩家 {username} 通过途径 {current_name} 获取皮肤成功")
            return respdata
            
        print(f"❌ 玩家 {username} 通过途径 {current_name} 获取皮肤失败，尝试下一个...")
        
    print(f"⚠️ 玩家 {username} 无法通过任何已知源获取皮肤")
    return False