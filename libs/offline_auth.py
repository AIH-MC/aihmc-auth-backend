from libs.config_loader import settings
from libs.database import Database
from libs.auth import save_other_data
from libs.utils import generate_offline_uuid, hash_password, check_password

db = Database()



async def offline_reg(playername, passwd, repasswd, ip):
    code = 200
    if not settings.allow_offline:
        code = 400
        msg = "注册失败，已关闭离线登录注册"
    elif passwd == repasswd:
        uuid = generate_offline_uuid(playername)
        hashed_pass = hash_password(passwd)
        success = await db.execute("INSERT INTO offline (username, uuid, password, ip) VALUES (%s, %s, %s, %s)", playername, uuid, hashed_pass, ip)
        if not success:
            code = 400
            msg = f"注册失败，玩家 {playername} 已存在"
        else:
            await save_other_data(uuid, playername)
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

async def offline_login(playername, password):
    code=200
    if not settings.allow_offline:
        code = 400
        msg = "登录失败，已关闭离线登录注册"
    else:
        data = await db.query("SELECT * FROM offline WHERE username = %s", playername)
        if not data:
            code = 404
            msg = f"登录失败，玩家 {playername} 不存在，请先注册！"
        else:
            hashed_pass = data[0].get("password")
            if check_password(password, hashed_pass):
                code = 200
                msg = "登录成功！"
            else:
                code = 403
                msg = "密码错误！"
    
    rtn = {
        "code": code,
        "msg": msg
    }
    return rtn

async def offline_check(playername):
    code=200
    if not settings.allow_offline:
        code = 400
        msg = "查询失败，已关闭离线登录注册"
    else:
        data = await db.query("SELECT * FROM offline WHERE username = %s", playername)
        if not data:
            code = 404
            msg = f"玩家 {playername} 尚未注册，请先注册！"
        else:
            code = 200
            msg = f"玩家 {playername} 已注册，请登录！"
    rtn = {
        "code": code,
        "msg": msg
    }
    return rtn

async def offline_chpsswd(playername, password, newpasswd):
    code=200
    if not settings.allow_offline:
        code = 400
        msg = "登录失败，已关闭离线登录注册"
    else:
        data = await db.query("SELECT * FROM offline WHERE username = %s", playername)
        if not data:
            code = 404
            msg = f"登录失败，玩家 {playername} 不存在"
        else:
            hashed_pass = data[0].get("password")
            if check_password(password, hashed_pass):
                new_hashed_pass = hash_password(newpasswd)
                await db.execute("UPDATE offline SET password = %s WHERE username = %s", new_hashed_pass, playername)
                code = 200
                msg = "密码修改成功！"
            else:
                code = 403
                msg = "密码错误！"
    
    rtn = {
        "code": code,
        "msg": msg
    }
    return rtn