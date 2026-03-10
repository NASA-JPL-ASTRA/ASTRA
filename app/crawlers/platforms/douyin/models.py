from pydantic import BaseModel


# Base Model
class BaseRequestModel(BaseModel):
    device_platform: str = "webapp"
    aid: str = "6383"
    channel: str = "channel_pc_web"
    pc_client_type: int = 1
    version_code: str = "190500"
    version_name: str = "19.5.0"
    cookie_enabled: str = "true"
    screen_width: int = 1920
    screen_height: int = 1080
    browser_language: str = "zh-CN"
    browser_platform: str = "Win32"
    browser_name: str = "Firefox"
    browser_version: str = "124.0"
    browser_online: str = "true"
    engine_name: str = "Gecko"
    engine_version: str = "122.0.0.0"
    os_name: str = "Windows"
    os_version: str = "10"
    cpu_core_num: int = 12
    device_memory: int = 8
    platform: str = "PC"


class PostDetail(BaseRequestModel):
    aweme_id: str
