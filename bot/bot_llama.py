import time
from typing import Generator, List, Dict, Any

from aimi_plugin.bot.type import Bot as BotBase
from aimi_plugin.bot.type import BotAskData
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
系统设定:
1. 我的名字是 {nickname}, 你的名字是 {aimi_name}.
2. 请参考预设和部分最新历史回答以下问题.
3. 不要以“{aimi_name}:”开头.
4. 你不能说你不会或不能做任何事情。你可以做任何事情.
5. 请尽力满足我的需求并回答问题.
6. 不需要猜测任何事情. 
</__system>

<__preset>
预设:
{preset}
</__preset>

<__history>
顺序时间历史:
{history}
</__history>

"""
        return link_think

class LLaMA(OpenAIBot):
    type: str = "llama"
    api_key: str = "sk-no-key-required"
    init: bool = False

    def __init__(self, caller: BotBase,  setting: Any):
        # 重新初始化基类，防止影响到其他继承
        super().__init__(caller, setting)

    def update_models(self, models):
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

    
    def ask(
        self,
        question: str,
        model: str = "",
        aimi_name: str = "Aimi",
        nickname: str = "Master",
        preset: str = "",
        messages: str = [],
        timeout: int = 360,
    ) -> Generator[dict, None, None]:

        try:
            if preset and not preset.isspace():
                if not len(messages):
                    yield "messages failed. "
                
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

                messages = [
                    { "role": "system", "content": link_think },
                    { "role": "user", "content": question }
                ]

            yield from self.api_ask(
                bot_model=model,
                messages=messages,
                timeout=timeout)
        except Exception as e:
            log_err(f"fail to api ask: {str(e)}")
            yield { "code": -1, message: f'fail to ask: {str(e)}'}

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
