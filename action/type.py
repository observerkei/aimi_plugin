from pydantic import BaseModel, constr
from typing import Any, List, Generator, Dict

class ActionToolItem(BaseModel):
    type: str = "object"
    call: str
    description: str
    request: Any
    execute: constr(regex="system|AI")
