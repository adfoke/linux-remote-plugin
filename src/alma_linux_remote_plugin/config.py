import os
from pathlib import Path
from typing import Dict
import yaml
from dotenv import load_dotenv
from .models import HostConfig, HostAuth

load_dotenv()

def load_hosts(config_path: str = "hosts.yaml") -> Dict[str, HostConfig]:
    path = Path(config_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"hosts 文件不存在: {path}。请复制 hosts.yaml.example 并重命名为 hosts.yaml")
    
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    
    hosts_raw = data.get("hosts", {})
    hosts: Dict[str, HostConfig] = {}
    for name, cfg in hosts_raw.items():
        auth_data = cfg.pop("auth", {})
        hosts[name] = HostConfig(**cfg, auth=HostAuth(**auth_data))
    return hosts