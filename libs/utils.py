from libs.config_loader import settings
from libs.database import Database
from urllib.parse import urlparse
import tldextract
import httpx
import hashlib
import uuid
import re
import bcrypt

db = Database()

# 请求数据
async def send_data(url):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            return False
        else:
            return resp.json()

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
    
# 计算基于玩家名的离线Minecraft玩家uuid
def generate_offline_uuid(username: str) -> str:
    """
    还原 Minecraft Java 版离线 UUID 生成算法
    算法公式：UUID.nameUUIDFromBytes(("OfflinePlayer:" + name).getBytes(StandardCharsets.UTF_8))
    """
    # 1. 拼接前缀与用户名并编码为 UTF-8
    content = f"OfflinePlayer:{username}".encode('utf-8')
    
    # 2. 计算 MD5 哈希
    hash_bytes = hashlib.md5(content).digest()
    
    # 3. 构造符合 RFC 4122 变体 2, 版本 3 的 UUID
    # Java 的 nameUUIDFromBytes 会自动处理版本号和变体位
    # 我们需要手动修改 MD5 结果中的特定位：
    hash_list = list(hash_bytes)
    
    # 设置版本号为 3 (bits 12-15 of time_hi_and_version)
    hash_list[6] = (hash_list[6] & 0x0f) | 0x30
    # 设置变体为 IETF (bits 6-7 of clock_seq_hi_and_reserved)
    hash_list[8] = (hash_list[8] & 0x3f) | 0x80
    
    return str(uuid.UUID(bytes=bytes(hash_list)))

# 时间转换
def parse_duration(duration_str: str) -> int:
    """
    将 '7d 10h 50m 20s' 格式的时间字符串转换为总秒数
    支持部分输入，如 '1d 2h' 或 '30m'
    """
    if not duration_str:
        return 0
        
    units = {
        'd': 86400,
        'h': 3600,
        'm': 60,
        's': 1
    }
    # 使用正则匹配数字和单位对
    matches = re.findall(r'(\d+)([dhms])', duration_str.lower())
    
    total_seconds = 0
    for value, unit in matches:
        total_seconds += int(value) * units[unit]
        
    return total_seconds


def hash_password(plain_text_password):
    salt = bcrypt.gensalt()
    
    password_bytes = plain_text_password.encode('utf-8')
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    
    return hashed_password

def check_password(plain_text_password, hashed_password):
    password_bytes = plain_text_password.encode('utf-8')
    
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
        
    return bcrypt.checkpw(password_bytes, hashed_password)