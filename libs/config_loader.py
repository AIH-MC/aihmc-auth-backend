from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.yml"

class AppConfig:
    def __init__(self):
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(f"未找到配置文件: {CONFIG_PATH}")
        self._data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
        self.db = self._data.get('database')
        self.servers = self._data.get('servers', [])
        self.extra_skin_domains = self._data.get('extra_skin_domains', [])
        self.skin_apis = self._data.get('skin_apis', [])
        self.server = self._data.get('server', {})
        self.keys = self._data.get('rsakey', {})
        self.allow_offline = self._data.get('allow_offline')
        self.access_token = self._data.get('access_token')

settings = AppConfig()