from pydantic import BaseModel
from typing import Literal, Optional

class HostAuth(BaseModel):
    method: Literal["password", "key"]
    password_env: Optional[str] = None
    key_path: Optional[str] = None
    passphrase_env: Optional[str] = None

class HostConfig(BaseModel):
    host: str
    port: int = 22
    username: str
    auth: HostAuth

class CommandResult(BaseModel):
    command: str
    exit_code: int
    stdout: str
    stderr: str
    success: bool