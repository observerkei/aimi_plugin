from typing import Any, Generator, List

log_dbg, log_err, log_info = print, print, print


# call bot_ plugin
class Bot:
    # This has to be globally unique
    type: str = "globally_unique_name"
    trigger: str = "#globally_unique_name"
    bot: Any
    setting: Any

    def __init__(self):
        self.bot = None

    # when time call bot
    def is_call(self, caller: Any, ask_data) -> bool:
        question = caller.bot_get_question(ask_data)
        if trigger in question:
            return True
        return False

    # get support model
    def get_models(self, caller: Any) -> List[str]:
        return [self.type]

    # ask bot
    def ask(self, caller: Any, ask_data) -> Generator[dict, None, None]:
        question = caller.bot_get_question(ask_data)
        yield caller.bot_set_response(code=1, message="ask")
        yield caller.bot_set_response(code=0, message="ask ok.")
        # if error, then: yield caller.bot_set_response(code=-1, message="err")

    # exit bot
    def when_exit(self, caller: Any):
        log_info("exit")

    # init bot
    def when_init(self, caller: Any):
        global log_info, log_dbg, log_err
        log_info = caller.bot_log_info
        log_dbg = caller.bot_log_dbg
        log_err = caller.bot_log_err

        log_info("init")
        self.setting = caller.bot_load_setting(self.type)
