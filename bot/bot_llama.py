import time
from typing import Generator, List, Dict, Any

from aimi_plugin.bot.type import Bot as BotBase
from aimi_plugin.bot.type import BotAskData

log_dbg, log_err, log_info = print, print, print


class LLaMA:
    type: str = "llama"
    chatbot: Any
    max_requestion: int = 1024
    access_token: str = ""
    max_repeat_times: int = 3
    api_key: str = "sk-no-key-required"
    api_base: str
    trigger: List[str] = []
    init: bool = False
    models: List[str] = []
    model_files: Dict[str, str] = {}

    def __init__(self, setting: dict) -> None:
        self.__load_setting(setting)
        if self.__init_bot():
            log_dbg(f"{self.type} init done.")


    def is_call(self, question) -> bool:
        for call in self.trigger:
            if call.lower() in question.lower():
                return True

        return False

    def get_models(self) -> List[str]:
        if not self.init:
            return []

        return self.models

    def make_link_think(
        self,
        question: str,
        aimi_name: str = "Aimi",
        nickname: str = "Master",
        preset: str = "",
        history: str = "",
    ) -> str:

        link_think = f"""
设定: {{
“{preset}”
}}.

请只关注最新消息,历史如下: {{
{history}
}}.

请根据设定和最新对话历史和你的历史回答, 不用“{aimi_name}:”开头, 回答如下问题: {{
{nickname}说: “{question}”
}}.
"""
        return link_think

    def ask(
        self,
        ask_data: BotAskData,
    ) -> Generator[dict, None, None]:
        yield from self.api_ask(
            question=ask_data.question,
            model=ask_data.model,
            messages=ask_data.messages,
        )
    
    def __get_bot_model(self, question, model):
        if model and model in self.models:
            return self.model_files[model]
        return self.model_files[0]

    def api_ask(
        self,
        question: str,
        model: str = "",
        messages: List[Dict] = [],
    ) -> Generator[dict, None, None]:
        answer = {"message": "", "code": 1}

        req_cnt = 0
        model = self.__get_bot_model(question, model)
       
        log_dbg(f"use model: {model}")
        if not len(messages) and question:
            messages = [{"role": "user", "content": question}]
        # log_dbg(f"msg: {str(messages)}")

        while req_cnt < self.max_repeat_times:
            req_cnt += 1
            answer["code"] = 1

            try:
                log_dbg("try ask: " + str(question))
                res = None

                for event in self.chatbot.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                ):
                    if event.choices[0].finish_reason == "stop":
                        break

                    answer["message"] += event.choices[0].delta.content
                    yield answer

                    res = answer["message"]

                if not len(res):
                    raise Exception(f"server no reply.")
                log_dbg(f"res: {str(res)}")

                answer["code"] = 0
                yield answer

            except Exception as e:
                log_err("fail to ask: " + str(e))
                log_dbg(f"server failed.")

                answer["message"] = str(e)
                answer["code"] = -1
                yield answer

                if req_cnt < self.max_repeat_times:
                    log_dbg("wait 15s...")
                    time.sleep(15)

            # request complate.
            if answer["code"] == 0:
                break

    def __init_bot(self) -> bool:
        api_key = self.api_key
        if api_key and len(api_key):
            try:
                import os
                from openai import OpenAI

                # 因为OpenAI 内部加载逻辑导致, 需要配置环境变量, 否则退出的时候, 容易导致抛出 缺失KEY的异常.
                os.environ["OPENAI_API_KEY"] = "sk-no-key-required"

                self.chatbot = OpenAI(
                    api_key=api_key,
                    base_url=self.api_base,
                )

                models = self.chatbot.models.list()  # (model_type="chat")
                for model in models:
                    show_model = model.id
                    if '/' in show_model:
                        show_model = show_model.split('/')[-1]
                    if '.' in show_model:
                        show_model = show_model.split('.')[0]
                    self.model_files[show_model] = model.id
                    self.models.append(show_model)
                log_dbg(f"avalible model: {self.models}")

                if self.models and len(self.models):
                    self.init = True
                else:
                    log_dbg(f"no avalible model.")

            except Exception as e:
                log_err(f"fail to get model {self.type} : {e}")

        return self.init

    def __load_setting(self, setting: dict):

        try:
            self.max_requestion = setting["max_requestion"]
        except Exception as e:
            log_err(f"fail to load {self.type} config: " + str(e))
            self.max_requestion = 1024
        try:
            self.max_repeat_times = setting["max_repeat_times"]
        except Exception as e:
            log_err(f"fail to load {self.type} config: " + str(e))
            self.max_repeat_times = 3
        try:
            self.model = setting["model"]
        except Exception as e:
            log_err(f"fail to load {self.type} config: " + str(e))
            self.model = ""
        try:
            self.trigger = setting["trigger"]
        except Exception as e:
            log_err(f"fail to load {self.type} config: " + str(e))
            self.trigger = ["@openai", "#openai"]
        try:
            self.api_base = setting["api_base"]
        except Exception as e:
            log_err(f"fail to load {self.type} config: " + str(e))
            self.api_base = ""
        try:
            self.api_key = setting["api_key"]
        except Exception as e:
            log_err(f"fail to load {self.type} config: " + str(e))
            self.api_key = ""


# call bot_ plugin
class Bot(BotBase):
    # This has to be globally unique
    type: str
    bot: LLaMA

    def __init__(self):
        self.type = LLaMA.type

    @property
    def init(self) -> bool:
        return self.bot.init

    # when time call bot
    def is_call(self, caller: BotBase, ask_data: BotAskData) -> bool:
        return self.bot.is_call(ask_data.question)

    # get support model
    def get_models(self, caller: BotBase) -> List[str]:
        return self.bot.get_models()

    # ask bot
    def ask(self, caller: BotBase, ask_data: BotAskData) -> Generator[dict, None, None]:
        yield from self.bot.ask(ask_data)

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
        self.bot = LLaMA(self.setting)
