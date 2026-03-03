from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict

class AuditLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_logger()
        return cls._instance

    def _init_logger(self):
        try:
            cfg = load_config("hosts.yaml").data.audit
            self.enabled = cfg.enabled
            self.log_file = Path(cfg.log_file)
        except:
            self.enabled = True
            self.log_file = Path("./logs/audit.jsonl")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, operation_type: str, host_name: str, details: Dict[str, Any]):
        if not self.enabled:
            return
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "operation_type": operation_type,
            "host_name": host_name,
            **details,
            "user": "AI_Agent"
        }
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")