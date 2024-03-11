from typing import Generator, List, Dict, Any, Tuple


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

    def is_call(self, caller: Any, req) -> bool:
        pass

    def get_models(self, caller: Any) -> List[str]:
        pass

    def ask(self, caller: Any, ask_data) -> Generator[dict, None, None]:
        pass

    def when_exit(self, caller: Any):
        pass

    def when_init(self, caller: Any):
        pass

    def bot_pack_ask_data(
        self,
        question: str,
        model: str = "",
        messages: List = [],
        conversation_id: str = "",
    ):
        pass

    def bot_get_question(self, ask_data):
        pass

    def bot_get_model(self, ask_data):
        pass

    def bot_get_messages(self, ask_data):
        pass

    def bot_get_conversation_id(self, ask_data):
        pass

    def bot_get_timeout(self, ask_data):
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