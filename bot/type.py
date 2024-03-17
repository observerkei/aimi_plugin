from typing import Generator, List, Dict, Any, Tuple, Optional, Union
from pydantic import BaseModel, constr

class BotType:
    Bing: str = "bing"
    Google: str = "google"
    OpenAI: str = "openai"
    Wolfram: str = "wolfram"
    Task: str = "task"
    LLaMA: str = 'llama'

class BotAskData(BaseModel):
    question: Optional[str]
    model: Optional[Union[str, None]] = ""
    messages: Optional[Union[List[Dict[str, str]], None]] = []
    conversation_id: Optional[Union[str, None]] = ""
    timeout: Optional[Union[int, None]] = 0
    aimi_name: Optional[Union[str, None]] = ""
    nickname: Optional[Union[str, None]] = ""
    preset: Optional[Union[str, None]] = ""
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

    def is_call(self, caller: 'Bot', req: str) -> bool:
        pass

    def get_models(self, caller: 'Bot') -> List[str]:
        pass

    def ask(self, caller: 'Bot', ask_data: BotAskData) -> Generator[dict, None, None]:
        pass

    def bot_ask(self, caller: 'Bot', bot_type: str, ask_data: BotAskData) -> Generator[dict, None, None]:
        pass

    def when_exit(self, caller: 'Bot'):
        pass

    def when_init(self, caller: 'Bot', setting: dict = None):
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
