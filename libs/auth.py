from libs.config_loader import settings
from pathlib import Path
from libs.database import Database
from urllib.parse import urlparse
import tldextract
import httpx
import random
import string

db = Database()

def generate_aihmc_forced_name():
    """生成 AIHMC_随机4位后缀 的强制改名"""
    chars = string.ascii_lowercase + string.digits
    suffix = "".join(random.choice(chars) for _ in range(4))
    return f"AIHMC_{suffix}"

async def save_other_data(uuid, username):
    # 1. 首先确保 UUID 关联表已记录
    await db.execute("INSERT IGNORE INTO userlink (uuid, new_uuid) VALUES (%s, %s)", uuid, uuid)
    
    # 2. 尝试直接插入原始用户名
    # 注意：前提是你的 namelink 表中 username 字段设置了 UNIQUE 约束
    success = await db.execute("INSERT IGNORE namelink (uuid, username) VALUES (%s, %s)", uuid, username)
    
    # 3. 如果插入失败（说明重名了），则强制改名为 AIHMC_随机4位后缀
    if not success:
        final_name = await force_rename_to_aihmc(uuid, username)
        print(f"💾 玩家 {username} 与 namelink 重名，最终分配名字为: {final_name}")
    else:
        print(f"💾 玩家 {username} 数据保存成功")

async def force_rename_to_aihmc(uuid, original_username):
    """强制改名为 AIHMC_随机4位后缀，并写入 namelink"""
    while True:
        forced_name = generate_aihmc_forced_name()
        success = await db.execute("INSERT INTO namelink (uuid, username) VALUES (%s, %s)", uuid, forced_name)
        if success:
            print(f"⚠️ 玩家 {original_username} 与离线账户重名，强制改名为: {forced_name}")
            return forced_name

async def save_player_data(resp_dict, source_id, ip):
    uuid = resp_dict.get("id")
    name = resp_dict.get("name")
    
    # 1. 先检查该名字在离线登录是否已存在
    offline_exists = await db.query("SELECT username FROM offline WHERE username = %s", name)
    
    if offline_exists:
        # 如果离线已存在，直接强制改名为 AIHMC_随机4位后缀
        final_name = await force_rename_to_aihmc(uuid, name)
    else:
        # 如果离线不存在，走原来的 namelink 逻辑
        await save_other_data(uuid, name)
        # 从 namelink 查出最终分配的名字（可能已被 save_other_data 加后缀改名）
        link_data = await db.query("SELECT username FROM namelink WHERE uuid = %s", uuid)
        final_name = link_data[0]["username"] if link_data else name
    
    # 用 final_name 更新后续逻辑中的 name 变量
    name = final_name
    
    textures_data = next((p for p in resp_dict.get("properties", []) if p['name'] == 'textures'), None)
    
    if textures_data:
        t_value = textures_data.get("value")
        t_signature = textures_data.get("signature")
        
        sql = """
            INSERT INTO users (uuid, username, last_source, last_ip, textures_value, textures_signature)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            username=%s, last_source=%s, last_ip=%s, textures_value=%s, textures_signature=%s
        """
        await db.execute(sql, 
            uuid, name, source_id, ip, t_value, t_signature,  # 插入部分
            name, source_id, ip, t_value, t_signature        # 更新部分
        )
        print(f"💾 已持久化玩家 {name} 的 UUID 和皮肤签名数据")
        
async def final_profile(resp_dict, session_uuid=None):
    uuid = session_uuid or resp_dict.get("id")
    
    # 1. 使用 JOIN 一次性查出：原始数据、关联UUID、关联用户名
    sql = """
        SELECT u.*, l.new_uuid, n.username as linked_name 
        FROM users u
        LEFT JOIN userlink l ON u.uuid = l.uuid
        LEFT JOIN namelink n ON n.uuid = COALESCE(l.new_uuid, u.uuid)
        WHERE u.uuid = %s
    """
    users = await db.query(sql, uuid)
    if not users:
        return resp_dict

    user = users[0]
    # 确定最终展示的 UUID 和 Name
    final_uuid = user.get("new_uuid") or user.get("uuid")
    final_name = user.get("linked_name") or user.get("username")

    # 2. 构造基础属性
    props = [{
        "name": "textures",
        "value": user.get("textures_value")
    }]

    # 3. 只有非 session 请求（即带签名的请求）才加上 signature
    if session_uuid is None:
        props[0]["signature"] = user.get("textures_signature")

    return {
        "id": final_uuid,
        "name": final_name,
        "properties": props
    }

async def get_ygg_data(url, username, serverid, ip):
    async with httpx.AsyncClient() as client:
        if ip is None:
            resp = await client.get(f"{url}?username={username}&serverId={serverid}")
        else:
            resp = await client.get(f"{url}?username={username}&serverId={serverid}?ip={ip}")
        if resp.status_code != 200:
            return False
        else:
            return resp.json()
        
async def get_ygg_profile(url, uuid):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{url}/{uuid}")
        if resp.status_code != 200:
            return False
        else:
            return resp.json()

async def ygg_meta():
    key_content = Path(settings.keys["public_keyfile"]).read_text(encoding="utf-8")
    extra_urls = settings.extra_skin_domains
    skin_urls = [] + extra_urls
    for skin_apis in settings.servers:
        if not skin_apis.get('enabled'):
            continue
        skin_url = skin_apis.get('root_url')
        extracted = tldextract.extract(skin_url)
        root_domain = f"{extracted.domain}.{extracted.suffix}"
        root_domain_with_dot = f".{root_domain}"
        skin_urls.append(root_domain_with_dot)
        skin_urls.append(root_domain)
        
    final_meta_data = {
        "meta": {
            "implementationName": "aihmc-auth-server",
            "implementationVersion": "1.0.0",
            "serverName": "AIHMC Auth",
        },
        "skinDomains": skin_urls,
        "signaturePublickey": key_content
    }
    return final_meta_data

async def ygg_auth(username, serverid, ip):
    for auth_api in settings.servers:
        current_name = auth_api.get("name")
        current_type = auth_api.get("api_type")
        current_url = auth_api.get("root_url")
        extracted = tldextract.extract(current_url)
        root_domain = f"{extracted.domain}.{extracted.suffix}"
        protocol = urlparse(current_url).scheme
        
        full_url= ""
        
        enabled = auth_api.get("enabled", True)
        if not enabled:
            print(f"❌ 玩家 {username} 通过途径 {current_name} 验证失败，原因：已关闭。正在尝试下一个...")
            continue
        if current_type == "mojang":
            full_url = f"{protocol}://sessionserver.{root_domain}/session/minecraft/hasJoined"
        elif current_type == "aihmc":
            full_url = f"{protocol}://api.{root_domain}/mcauth/sessionserver/session/minecraft/hasJoined"
        elif current_type == "blessingskin":
            full_url = f"{protocol}://{root_domain}/api/yggdrasil/sessionserver/session/minecraft/hasJoined"
        elif current_type == "elyby":
            full_url = f"{protocol}://account.{root_domain}/api/minecraft/session/hasJoined"
        respdata = await get_ygg_data(full_url, username, serverid, ip)
        
        if respdata:
            print(f"✅ 玩家 {username} 通过途径 {current_name} 验证成功")
            await save_player_data(respdata, current_name, ip)
            data = await final_profile(respdata)
            return data
            
        print(f"❌ 玩家 {username} 通过途径 {current_name} 验证失败，尝试下一个...")
        
    print(f"⚠️ 玩家 {username} 无法通过任何已知源验证")
    return False

async def ygg_seesion(uuid):
    for user_check in settings.servers:
        current_name = user_check.get("name")
        current_type = user_check.get("api_type")
        current_url = user_check.get("root_url")
        extracted = tldextract.extract(current_url)
        root_domain = f"{extracted.domain}.{extracted.suffix}"
        protocol = urlparse(current_url).scheme
        
        full_url= ""
        
        enabled = user_check.get("enabled", True)
        if not enabled :
            print(f"❌ 途径 {current_name} 已关闭。正在尝试下一个...")
            continue
        if current_type == "mojang":
            full_url = f"{protocol}://sessionserver.{root_domain}/session/minecraft/profile"
        elif current_type == "aihmc":
            full_url = f"{protocol}://api.{root_domain}/mcauth/sessionserver/session/minecraft/profile"
        elif current_type == "blessingskin":
            full_url = f"{protocol}://{root_domain}/api/yggdrasil/sessionserver/session/minecraft/profile"
        elif current_type == "elyby":
            full_url = f"{protocol}://account.{root_domain}/api/minecraft/session/profile"
        respdata = await get_ygg_profile(full_url, uuid)
        
        
        if respdata:
            username = respdata.get("name")
            print(f"✅ 玩家 {username} 通过途径 {current_name} 获取资料成功")
            data = await final_profile(respdata)
            return data
    return False