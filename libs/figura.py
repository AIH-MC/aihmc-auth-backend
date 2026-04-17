from libs.config_loader import settings
from libs.database import Database
from urllib.parse import urlparse
from libs.utils import generate_offline_uuid, parse_duration, hash_password, check_password
from libs.auth import get_ygg_data
import tldextract
import time

db = Database()

async def check_figura_session(username, ip):
    err_type = "NONE"
    session_timeout= parse_duration(settings.figura_session)
    res = await db.query("SELECT username, ip, last_time FROM figura WHERE username = %s", username)
    if res:
        row = res[0]
        reg_ip = row['ip']
        last_time = row['last_time']
        timestamp = int(time.time())
        if ip != reg_ip:
            err_type = "IP_INVALID"
        elif timestamp - last_time > session_timeout:
            err_type = "SESSION_TIMEDOUT"
        else:
            err_type = "SUCCESS"
    else:
        err_type = "NOT_REG"
    return err_type

async def auto_update_session(username, ip):
    timestamp = int(time.time())
    await db.execute("UPDATE figura SET ip = %s, last_time = %s WHERE username = %s", ip, timestamp, username)

async def figura_auth(username, serverid, ip):
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
            print(f"❌ 玩家 {username} 通过途径 {current_name} 验证 Figura 失败，原因：已关闭。正在尝试下一个...")
            continue
        if current_type == "mojang":
            full_url = f"{protocol}://sessionserver.{root_domain}/session/minecraft/hasJoined"
        elif current_type == "aihmc":
            full_url = f"{protocol}://api.{root_domain}/mcauth/sessionserver/session/minecraft/hasJoined"
        elif current_type == "blessingskin":
            full_url = f"{protocol}://{root_domain}/api/yggdrasil/sessionserver/session/minecraft/hasJoined"
        elif current_type == "elyby":
            full_url = f"{protocol}://account.{root_domain}/api/minecraft/session/hasJoined"
        respdata = await get_ygg_data(full_url, username, serverid, None)
        
        if respdata:
            print(f"✅ 玩家 {username} 通过途径 {current_name} 验证 Figura 成功")
            return respdata
            
        print(f"❌ 玩家 {username} 通过途径 {current_name} 验证 Figura 失败，尝试下一个...")
        
    print(f"⚠️ 玩家 {username} 无法通过任何已知源验证，已回退为 Figura 离线模式")
    session_res = await check_figura_session(username, ip)
    if session_res == "IP_INVALID" or session_res == "SESSION_TIMEDOUT":
        return False
    elif session_res == "SUCCESS":
        await auto_update_session(username, ip)
    
    offline_mode = {
        "id": generate_offline_uuid(username),
        "name": username,
        "properties": []
    }
    return offline_mode

async def figura_reg(username, passwd, repasswd, ip):
    code = 200
    if passwd == repasswd:
        uuid = generate_offline_uuid(username)
        hashed_pass = hash_password(passwd)
        timestamp = int(time.time())
        success = await db.execute("INSERT INTO figura (username, uuid, password, ip, last_time) VALUES (%s, %s, %s, %s, %s)", username, uuid, hashed_pass, ip, timestamp)
        if not success:
            code = 400
            msg = f"注册失败，玩家 {username} 已存在"
        else:
            code = 200
            msg = "注册成功"
    else:
        code = 400
        msg = "密码和确认密码不一致"
        
    rtndata = {
        "code": code,
        "msg": msg
    }
    
    return rtndata

async def figura_refresh(username, passwd, ip):
    code=200
    data = await db.query("SELECT * FROM figura WHERE username = %s", username)
    if not data:
        code = 404
        msg = f"刷新失败，玩家 {username} 不存在，请先注册！"
    else:
        hashed_pass = data[0].get("password")
        if check_password(passwd, hashed_pass):
            timestamp = int(time.time())
            await db.execute("UPDATE figura SET ip = %s, last_time = %s WHERE username = %s", ip, timestamp, username)
            code = 200
            msg = "刷新成功！"
        else:
            code = 403
            msg = "密码错误！"
    
    rtn = {
        "code": code,
        "msg": msg
    }
    return rtn
