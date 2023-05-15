from typing import Any, Generator

# call bot_ plugin
class Bot:
    # This has to be globally unique
    type: str = 'globally_unique_name'
    trigger: str = '#globally_unique_name'
    bot: Any

    def __init__(self):
        self.bot = None

    # when time call bot
    def is_call(self, caller: Any, ask_data) -> bool:
        question = caller.bot_get_question(ask_data)
        if trigger in question:
            return True
        return False

    # ask bot
    def ask(self, caller: Any, ask_data) -> Generator[dict, None, None]:
        question = caller.bot_get_question(ask_data)
        yield caller.bot_set_response(code=1, message="ask")
        yield caller.bot_set_response(code=0, message="ask ok.")
        # if error, then: yield caller.bot_set_response(code=-1, messa

    # exit bot
    def when_exit(self):
        print('exit')

    # init bot
    def when_init(self):
        print('init')
