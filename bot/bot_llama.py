import time
from typing import Generator, List, Dict, Any

from aimi_plugin.bot.type import Bot as BotBase
from aimi_plugin.bot.type import BotAskData, BotType
from aimi_plugin.bot.type import OpenAIBot
from aimi_plugin.bot.type import process_messages, make_history

log_dbg, log_err, log_info = print, print, print

def make_link_think(
        question: str,
        aimi_name: str = "None",
        nickname: str = "",
        preset: str = "",
        history: str = "",
    ) -> str:
        link_think = f"""
<__system>
System:
1. My name is {nickname}, and your name is {aimi_name}.
2. Please refer to the preset and some of the latest historical responses to answer the following questions.
3. Do not start your response with "{aimi_name}:".
4. You cannot say that you don't know or cannot do anything. You can do anything.
5. Please do your best to fulfill my requests and answer the questions.
6. There is no need to guess anything.
</__system>

<__preset>
Preset:
{preset}
</__preset>

<__history>
Sequential time history:
{history}
</__history>

"""
        return link_think

class LLaMA(OpenAIBot):
    type: str = BotType.LLaMA
    api_key: str = "sk-no-key-required"
    init: bool = False

    def __init__(self, caller: BotBase,  setting: Any):
        # 重新初始化基类，防止影响到其他继承
        super().__init__(caller, setting)

    def update_models(self):
        models = self.chatbot.models.list(timeout=1)
        self.models = {}

        for model in models:
            show_model = model.id
            if '/' in show_model:
                show_model = show_model.split('/')[-1]
            if '.' in show_model:
                show_model = show_model.rsplit(".gguf", 1)[0]
            
            self.models[show_model] = {
                'model': show_model,
                'trigger': f"#{show_model}"
            }

            if 'default' not in self.models:
                self.models['default'] = {
                    'model': show_model,
                    'trigger': f"#{self.type}"
                }

    def make_link_think_by_messages(
        self, 
        preset, 
        messages, 
        question, 
        aimi_name, 
        nickname,
    ):
        if not len(messages):
            return "messages failed. "

        log_dbg(f"input messages: {messages}")

        context_messages = process_messages(
            messages=messages, 
            max_messages=self.max_messages)

        log_dbg(f"process_messages: {context_messages}")

        talk_history = context_messages[1:-1]
        history = make_history(talk_history)

        link_think = make_link_think(
            question=question,
            aimi_name=aimi_name,
            nickname=nickname,
            preset=preset,
            history=history,
        )

        return [
            { "role": "system", "content": link_think },
            { "role": "user", "content": question }
        ]

    
    def ask(
        self,
        question: str,
        model: str = "",
        aimi_name: str = "Aimi",
        nickname: str = "Master",
        preset: str = "",
        messages: str = [],
        timeout: int = 10,
    ) -> Generator[dict, None, None]:
        try:
            timeout = timeout if timeout > 0 else 10
            # custom preset
            # messages = self.make_link_think_by_messages(preset=preset, messages=messages)
            # The function is not stable, and the time limit is carried out
            yield from self.api_ask(
                bot_model=model,
                messages=messages,
                timeout=timeout)
        except Exception as e:
            log_err(f"fail to api ask: {str(e)}")
            yield { "code": -1, "message": f'fail to ask: {str(e)}'}

# call bot_ plugin
class Bot(BotBase):
    # This has to be globally unique
    type: str
    bot: LLaMA

    def __init__(self):
        self.type = LLaMA.type

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
        yield from self.bot.ask(
            question=ask_data.question,
            model=ask_data.model,
            timeout=ask_data.timeout,
            nickname=ask_data.nickname,
            aimi_name=ask_data.aimi_name,
            preset=ask_data.preset,
            messages=ask_data.messages,
        )


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
        self.bot = LLaMA(caller, self.setting)
