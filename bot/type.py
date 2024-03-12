from typing import Generator, List, Dict, Any, Tuple, Optional, Union
from pydantic import BaseModel, constr

class BotType:
    Bing: str = "bing"
    Google: str = "google"
    OpenAI: str = "openai"
    Wolfram: str = "wolfram"

class BotAskData(BaseModel):
    question: Optional[str]
    model: Optional[Union[str, None]] = ""
    api_key:  Optional[Union[str, None]] = ""
    messages: Optional[Union[List[Dict[str, str]], None]] = []
    conversation_id: Optional[Union[str, None]] = ""
    timeout: Optional[Union[int, None]] = 10
    aimi_name: Optional[Union[str, None]] = "Aimi",
    nickname: Optional[Union[str, None]] = "Master",
    preset: Optional[Union[str, None]] = "",
    history: Optional[Union[str, None]] = ""

# call bot_ plugin example
class Bot:
    # This has to be globally unique
    type: str = "public_name"
    trigger: str = "#public_name"
    bot: Any = None
    # no need define plugin_prefix
    plugin_prefix = "bot_"

    def __init__(self):
        pass

    @property
    def init(self) -> bool:
        pass

    def is_call(self, caller: Any, req: str) -> bool:
        pass

    def get_models(self, caller: Any) -> List[str]:
        pass

    def ask(self, caller: Any, ask_data: BotAskData) -> Generator[dict, None, None]:
        pass

    def bot_ask(self, caller: Any, bot_type: str, ask_data: BotAskData) -> Generator[dict, None, None]:
        pass

    def when_exit(self, caller: Any):
        pass

    def when_init(self, caller: Any, setting: dict = None):
        pass

    def bot_set_response(self, code: int, message: str) -> Any:
        pass

    def bot_load_setting(self, type: str):
        pass

    def bot_log_dbg(self, msg: str):
        pass

    def bot_log_err(self, msg: str):
        pass

    def bot_log_info(self, msg: str):
        pass
