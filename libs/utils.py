from libs.config_loader import settings
from libs.database import Database
from urllib.parse import urlparse
import tldextract
import httpx

db = Database()

# 请求数据
async def send_data(url):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            return False
        else:
            return resp.json()

# Figura 后端验证
async def reg_figura_uuid(uuid, username):
    await db.execute("INSERT IGNORE INTO figura (uuid, username) VALUES (%s, %s)", uuid, username)
    print(f"💾 玩家 {username} Figura 数据注册成功")
        
async def validate_figura_data(username):
    res_list = await db.query("SELECT * FROM figura WHERE username = %s", username)
    if not res_list:
        print(f"❌ Figura 验证失败，玩家可能没进过服")
        return False
    res = res_list[0]
    figura_data = {
        "id": res.get("uuid"),
        "name": res.get("username"),
        "properties": []
    }
    
    return figura_data

# 数据迁移
async def link_server_profile(uuid, new_uuid):
    res_list = await db.query("SELECT * FROM userlink WHERE uuid = %s", uuid)
    if not res_list:
        print(f"❌ 数据迁移失败，玩家可能没进过服")
        return False
    else:
        await db.execute("UPDATE userlink SET new_uuid = %s WHERE uuid = %s", new_uuid, uuid)
        print(f"💾 玩家 {uuid} 数据迁移成功，已迁移至 {new_uuid}")
        
# 用户名存在性检测
async def check_player_name(username):
    for user_api in settings.servers:
        current_name = user_api.get("name")
        current_type = user_api.get("api_type")
        current_url = user_api.get("root_url")
        extracted = tldextract.extract(current_url)
        root_domain = f"{extracted.domain}.{extracted.suffix}"
        protocol = urlparse(current_url).scheme
        
        full_url= ""
        
        enabled = user_api.get("enabled", True)
        if not enabled:
            print(f"❌ 已关闭 {current_name} 来源的用户存在性验证。正在尝试下一个...")
            continue
        
        if current_type == "mojang":
            full_url = f"{protocol}://api.{root_domain}/users/profiles/minecraft"
        elif current_type == "aihmc":
            full_url = f"{protocol}://api.{root_domain}/mcauth/api/users/profiles/minecraft"
        elif current_type == "blessingskin":
            full_url = f"{protocol}://{root_domain}/api/yggdrasil/api/users/profiles/minecraft"
        elif current_type == "elyby":
            full_url = f"{protocol}://authserver.{root_domain}/api/users/profiles/minecraft"

        respdata = await send_data(f"{full_url}/{username}")
        
        if respdata:
            respdata["source"] = current_name
            print(f"❌ 玩家名 {username} 已存在于途径 {current_name}")
            return respdata
        
    print(f"⚠️ 玩家名 {username} 可用")
    return False

# 玩家改名
async def server_player_rename(uuid, username):
    is_used = await check_player_name(username)
    if not is_used:
        await db.execute("UPDATE namelink SET username = %s WHERE uuid = %s", username, uuid)
        print(f"✅ 玩家 {uuid} 更名成功，新玩家名 {username}")
        return True
    else:
        print(f"❌ 玩家 {uuid} 更名失败，玩家名 {username} 已存在")
        return False

# 玩家重置名称
async def server_player_rstname(uuid):
    users_list = await db.query("SELECT * FROM users WHERE uuid = %s", uuid)
    user_data = users_list[0]
    await db.execute("UPDATE namelink SET username = %s WHERE uuid = %s", user_data.get("username"), uuid)
    print(f"✅ 玩家 {uuid} 名称已重置")