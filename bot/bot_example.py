from typing import Any, Generator, List

from aimi_plugin.bot.type import Bot as BotType
from aimi_plugin.bot.type import BotAskData

log_dbg, log_err, log_info = print, print, print


# call bot_ plugin
class Bot(BotType):
    # This has to be globally unique
    type: str = "globally_unique_name"
    trigger: str = "#globally_unique_name"
    bot: Any
    setting: Any

    def __init__(self):
        self.bot = None

    @property
    def init(self) -> bool:
        return self.bot.init

    # when time call bot
    def is_call(self, caller: BotType, ask_data: BotAskData) -> bool:
        question = ask_data.question
        if f"#{self.type} " in question:
            return True
        return False

    # get support model
    def get_models(self, caller: BotType) -> List[str]:
        return [self.type]

    # ask bot
    def ask(self, caller: BotType, ask_data: BotAskData) -> Generator[dict, None, None]:
        question = ask_data.question
        yield caller.bot_set_response(code=1, message="ask")
        yield caller.bot_set_response(code=0, message="ask ok.")
        # if error, then: yield caller.bot_set_response(code=-1, message="err")

    # exit bot
    def when_exit(self, caller: BotType):
        log_info("exit")

    # init bot
    def when_init(self, caller: BotType):
        global log_info, log_dbg, log_err
        log_info = caller.bot_log_info
        log_dbg = caller.bot_log_dbg
        log_err = caller.bot_log_err

        log_info("init")
        self.setting = caller.bot_load_setting(self.type)
