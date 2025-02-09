import time
from typing import Generator, List, Dict, Any

from aimi_plugin.bot.type import Bot as BotBase
from aimi_plugin.bot.type import BotAskData, BotType

log_dbg, log_err, log_info = print, print, print


class OpenAIAPI:
    type: str = BotType.OpenAI
    openai: Any
    chatbot: Any
    max_requestion: int = 1024
    access_token: str = ""
    max_repeat_times: int = 3
    fackopen_url: str = ""
    api_key: str
    api_base: str
    trigger: List[str] = []
    model: str = ""
    models: List[str] = []
    default_model: str = "gpt-3.5-turbo"
    chat_completions_models: List[str] = [
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-0125",
        "gpt-3.5-turbo-0301",
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-1106",
        "gpt-3.5-turbo-16k",
        "gpt-3.5-turbo-16k-0613",
        "gpt-3.5-turbo-instruct",
        "gpt-3.5-turbo-instruct-0914",
        "gpt-4",
        "gpt-4-0314",
        "gpt-4-0613",
        "gpt-4-32k",
        "gpt-4-32k-0314",
        "gpt-4-32k-0613",
        "gpt-4-vision-preview",
        "gpt-4-1106-vision-preview"
        "gpt-4o",
        "gpt-4o-2024-08-06",
        "gpt-4o-mini",
        "gpt-4o-mini-2024-07-18",
        "o1-mini",
        "o1-mini-2024-09-12",
        "o1-preview",
        "o1-preview-2024-09-12",
    ]
    init_web: bool = False
    init_api: bool = False

    class InputType:
        SYSTEM = "system"
        USER = "user"
        ASSISTANT = "assistant"

    @property
    def init(self):
        if self.init_web or self.init_api:
            return True
        return False

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
        question: str,
        model: str = "",
        aimi_name: str = "",
        nickname: str = "",
        preset: str = "",
        history: str = "",
        context_messages: List[Dict] = [],
        conversation_id: str = "",
        timeout: int = 10,
        temperature: float = 1,
        top_p: float = 1,
        presence_penalty: float = 0,
        frequency_penalty: float = 0,
    ) -> Generator[dict, None, None]:
        if model == "web":
            link_think = self.make_link_think(
                question=question,
                aimi_name=aimi_name,
                nickname=nickname,
                preset=preset,
                history=history,
            )
            yield from self.web_ask(link_think, conversation_id, timeout)
        else:
            yield from self.api_ask(
                question=question,
                model=model,
                messages=context_messages,
                timeout=timeout,
                temperature=temperature,
                top_p=top_p,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
            )

    def web_ask(
        self,
        question: str,
        conversation_id: str = "",
        timeout: int = 60,
    ) -> Generator[dict, None, None]:
        answer = {"message": "", "conversation_id": conversation_id, "code": 1}

        model = self.model if self.model and len(self.model) else None

        req_cnt = 0

        while req_cnt < self.max_repeat_times:
            req_cnt += 1
            answer["code"] = 1

            try:
                log_dbg("try ask: " + str(question))

                if conversation_id and len(conversation_id):
                    for data in self.chatbot.ask(
                        question,
                        conversation_id,
                        parent_id=None,
                        model=model,
                        auto_continue=False,
                        timeout=timeout,
                    ):
                        answer["message"] = data["message"]
                        yield answer
                else:
                    for data in self.chatbot.ask(
                        question, None, None, None, timeout=480
                    ):
                        answer["message"] = data["message"]
                        yield answer

                    answer["conversation_id"] = self.get_revChatGPT_conversation_id()

                answer["code"] = 0
                yield answer

            except Exception as e:
                log_err("fail to ask: " + str(e))
                log_dbg(f"server failed.")

                answer["message"] = str(e)
                answer["code"] = -1
                yield answer
                if req_cnt < self.max_repeat_times:
                    log_dbg("wait 30s...")
                    time.sleep(30)

            # request complate.
            if answer["code"] == 0:
                break

    def __get_bot_model(self, question: str) -> str:
        if self.init_api:
            return self.default_model
        if self.init_web:
            return "web"

        return ""

    def api_ask(
        self,
        question: str,
        model: str = "",
        api_key: str = "",
        messages: List[Dict] = [],
        timeout: int = 10,
        temperature: float = 1,
        top_p: float = 1,
        presence_penalty: float = 0,
        frequency_penalty: float = 0,
    ) -> Generator[dict, None, None]:
        answer = {"message": "", "code": 1}

        if api_key and len(api_key) and (
            api_key != self.api_key
        ):
            self.api_key = api_key
            self.__init_bot()

        req_cnt = 0
        if not model or not len(model) or (model not in self.chat_completions_models):
            model = self.__get_bot_model(question)
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

                completion = {"role": "", "content": ""}
                for event in self.openai.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                    temperature=temperature,
                    top_p=top_p,
                    presence_penalty=presence_penalty,
                    frequency_penalty=frequency_penalty,
                ):
                    if event.choices[0].finish_reason == "stop":
                        # log_dbg(f'recv complate: {completion}')
                        break

                    answer["message"] += event.choices[0].delta.content
                    yield answer

                    res = event

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

    def get_revChatGPT_conversation_id(self) -> str:
        conv_li = self.chatbot.get_conversations(0, 1)
        try:
            return conv_li[0]["id"]
        except:
            return ""

    def __init__(self, setting: dict) -> None:
        self.__load_setting(setting)
        if self.__init_bot():
            log_dbg(f"{self.type} init done.")

    def __init_bot(self) -> bool:
        access_token = self.access_token
        if access_token and len(access_token):
            from revChatGPT.V1 import Chatbot

            # 这个库有封号风险, 设置才导入这个包.

            self.chatbot = Chatbot({"access_token": access_token})

            # set revChatGPT fackopen_url
            fackopen_url = self.fackopen_url
            if fackopen_url and len(fackopen_url):
                self.chatbot.BASE_URL = fackopen_url
                log_dbg("use fackopen_url: " + str(fackopen_url))

            self.init_web = True
            self.models.append("web")

        api_key = self.api_key if len(self.api_key) else "sk-no-key-required"
        if api_key and len(api_key):
            try:
                import os
                from openai import OpenAI

                # 因为OpenAI 内部加载逻辑导致, 需要配置环境变量, 否则退出的时候, 容易导致抛出 缺失KEY的异常.
                os.environ["OPENAI_API_KEY"] = "sk-no-key-required"

                api_base = self.api_base
                if api_base and len(api_base):
                    OpenAI.api_base = api_base
                    log_dbg(f"use openai base: {api_base}")

                self.openai = OpenAI(
                    api_key=api_key,
                )
                models = self.openai.models.list()  # (model_type="chat")
                for model in models:
                    if not (model.id in self.chat_completions_models):
                        continue
                    self.models.append(model.id)
                log_dbg(f"avalible model: {self.models}")
                if len(self.models) > 0:
                    self.init_api = True
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
            self.access_token = setting["access_token"]
        except Exception as e:
            log_err(f"fail to load {self.type} config: " + str(e))
            self.access_token = ""
        try:
            self.max_repeat_times = setting["max_repeat_times"]
        except Exception as e:
            log_err(f"fail to load {self.type} config: " + str(e))
            self.max_repeat_times = 3
        try:
            self.fackopen_url = setting["fackopen_url"]
        except Exception as e:
            log_err(f"fail to load {self.type} config: " + str(e))
            self.fackopen_url = ""
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
            self.api_key = "sk-no-key-required"


# call bot_ plugin
class Bot(BotBase):
    # This has to be globally unique
    type: str
    bot: OpenAIAPI

    def __init__(self):
        self.type = OpenAIAPI.type

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
    def ask(self, caller: BotBase, ask_data: BotAskData) -> Generator[dict, None, None]:
        yield from self.bot.ask(
            question=ask_data.question,
            model=ask_data.model,
            nickname=ask_data.nickname,
            aimi_name=ask_data.aimi_name,
            preset=ask_data.preset,
            history=ask_data.history,
            context_messages=ask_data.messages,
            conversation_id=ask_data.conversation_id,
            timeout=ask_data.timeout,
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
        self.bot = OpenAIAPI(self.setting)
