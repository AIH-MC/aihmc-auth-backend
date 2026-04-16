from pydantic import BaseModel
from typing import Optional

class PostFiguraUUID(BaseModel):
    uuid: str
    username: str
    
class LinkProfile(BaseModel):
    uuid: str
    new_uuid: str
    
class Rename(BaseModel):
    uuid: str
    username: str
    
class OfflineReg(BaseModel):
    username: str
    passwd: str
    repasswd: str
    ip: Optional[str] = None
    
class FiguraReg(BaseModel):
    username: str
    passwd: str
    repasswd: str
    
class OfflineLog(BaseModel):
    username: str
    passwd: str
    
class OfflineChpass(BaseModel):
    username: str
    passwd: str
    newpasswd: str