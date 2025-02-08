from typing import Generator, List, Any, Dict
import time

from aimi_plugin.bot.type import Bot as BotBase
from aimi_plugin.bot.type import BotAskData
from aimi_plugin.bot.type import OpenAIBot, BotType

log_dbg, log_info, log_err = print, print, print

class XAIAPI(OpenAIBot):
    type: str = BotType.XAI
    init: bool = False

    def __init__(self, caller: BotBase,  setting: Any):
        # 重新初始化基类，防止影响到其他继承
        super().__init__(caller, setting)

# call bot_ plugin
class Bot(BotBase):
    # This has to be globally unique
    type: str
    bot: XAIAPI

    def __init__(self):
        self.type = XAIAPI.type

    @property
    def init(self) -> bool:
        if self.bot:
            return self.bot.init
        return False

    # when time call bot
    def is_call(self, caller: BotBase, ask_data: BotAskData) -> bool:
        return self.bot.is_call(ask_data.question)

    # get support model
    def get_models(self, caller: BotBase) -> List[str]:
        return self.bot.get_models()

    # ask bot
    def ask(
        self, caller: BotBase, ask_data: BotAskData
    ) -> Generator[dict, None, None]:
        yield from self.bot.ask(ask_data.model, ask_data.messages, ask_data.timeout)

    # exit bot
    def when_exit(self, caller: BotBase):
        pass

    # init bot
    def when_init(self, caller: BotBase, setting: dict = None):
        global log_info, log_dbg, log_err
        log_info = caller.bot_log_info
        log_dbg = caller.bot_log_dbg
        log_err = caller.bot_log_err

        self.setting = setting
        self.bot = XAIAPI(caller, self.setting)
