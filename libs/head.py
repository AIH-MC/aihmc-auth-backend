from pathlib import Path
from libs.config_loader import settings
from urllib.parse import urlparse
from libs.utils import send_data, identify_identifier
from PIL import Image
import io
import tldextract
import httpx
import json
import base64

# 定义本地默认皮肤路径
DEFAULT_SKIN_PATH = Path("assets/alex.png")

def parse_mojang_skin_url(resp_dict):
    if not resp_dict or not isinstance(resp_dict, dict):
        return None
    textures_item = next((p for p in resp_dict.get("properties", []) if p.get("name") == "textures"), None)
    if not textures_item:
        return None

    try:
        decoded_data = json.loads(base64.b64decode(textures_item["value"]))
        textures = decoded_data.get("textures", {})
        
        skin_info = textures.get("SKIN", {})
        skin_url = skin_info.get("url")
        return skin_url
    except Exception as e:
        print(f"解析错误: {e}")
        return None
    
async def process_skin_to_head(skin_source, size: int = 64):
    """
    获取皮肤图片并裁剪出头像部分，支持缩放。
    skin_source 可以是远程 URL (str) 或本地图片字节流 (bytes)。
    """
    try:
        if isinstance(skin_source, str) and skin_source.startswith("http"):
            async with httpx.AsyncClient() as client:
                resp = await client.get(skin_source, timeout=5.0)
                if resp.status_code != 200:
                    raise Exception(f"远程皮肤获取失败: {resp.status_code}")
                skin_bytes = resp.content
        else:
            # 假设是传入的本地字节流
            skin_bytes = skin_source

        with Image.open(io.BytesIO(skin_bytes)) as img:
            img = img.convert("RGBA")
            # 基础层 (8, 8, 16, 16)
            head = img.crop((8, 8, 16, 16))
            
            # 叠加层 (40, 8, 48, 16)
            if img.width >= 64: # 确保是标准或双层皮肤
                overlay = img.crop((40, 8, 48, 16))
                head.paste(overlay, (0, 0), overlay)
            
            # 缩放 (使用 Resampling.NEAREST 保持像素感)
            head = head.resize((size, size), Image.Resampling.NEAREST)
            
            # 转为二进制
            output = io.BytesIO()
            head.save(output, format="PNG")
            return output.getvalue()
    except Exception as e:
        print(f"处理头像出错: {e}")
        # 如果当前处理的不是默认皮肤，则尝试回退到本地默认皮肤
        if not isinstance(skin_source, bytes):
             try:
                 if DEFAULT_SKIN_PATH.exists():
                     return await process_skin_to_head(DEFAULT_SKIN_PATH.read_bytes(), size)
             except:
                 pass
        return None
    
async def get_player_info(username):
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
            print(f"❌ 已关闭 {current_name} 来源的档案信息。正在尝试下一个...")
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
            print(f"已获取玩家名 {username} 的档案，来源 {current_name}")
            return respdata
        
    print(f"⚠️ 玩家名 {username} 档案不存在")
    return False

async def get_player_full_profile(uuid):
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
            print(f"❌ 已关闭 {current_name} 来源的详细档案信息。正在尝试下一个...")
            continue
        
        if current_type == "mojang":
            full_url = f"{protocol}://sessionserver.{root_domain}/session/minecraft/profile"
        elif current_type == "aihmc":
            full_url = f"{protocol}://api.{root_domain}/mcauth/sessionserver/session/minecraft/profile"
        elif current_type == "blessingskin":
            full_url = f"{protocol}://{root_domain}/api/yggdrasil/sessionserver/session/minecraft/profile"
        elif current_type == "elyby":
            full_url = f"{protocol}://authserver.{root_domain}/session/profile"
            
        respdata = await send_data(f"{full_url}/{uuid}")
        
        if respdata:
            print(f"已获取玩家 {uuid} 的档案，来源 {current_name}")
            return respdata
        
    print(f"⚠️ 玩家 {uuid} 档案不存在")
    return False

async def get_player_head(account, size=64):
    res = identify_identifier(account)
    player_profile = None
    skin_url = None

    # 1. 尝试获取档案
    if res == "USERNAME":
        player_info = await get_player_info(account)
        if player_info:
            p_uuid = player_info.get("id").replace("-", "")
            player_profile = await get_player_full_profile(p_uuid)
    elif res == "UUID":
        player_profile = await get_player_full_profile(account.replace("-", ""))

    # 2. 解析皮肤 URL
    if player_profile:
        skin_url = parse_mojang_skin_url(player_profile)
    
    # 3. 如果没有远程 URL，直接使用本地默认皮肤
    if not skin_url:
        print(f"无法获取 {account} 的远程档案，使用本地默认皮肤: {DEFAULT_SKIN_PATH}")
        if DEFAULT_SKIN_PATH.exists():
            return await process_skin_to_head(DEFAULT_SKIN_PATH.read_bytes(), size)
        return None
    
    # 4. 处理远程头像
    return await process_skin_to_head(skin_url, size)