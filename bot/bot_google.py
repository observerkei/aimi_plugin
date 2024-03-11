import os
import time
from typing import Generator, List, Any
from contextlib import suppress
import pprint
from gemini import Gemini
import asyncio
from os import environ

from aimi_plugin.bot.type import Bot as BotType

log_dbg, log_err, log_info = print, print, print


class GoogleAPI:
    type: str = "google"
    chatbot: Any
    cookie_1PSIDTS: str = ""
    cookie_1PSID: str = ""
    cookie_NID: str = ""
    cookie_file: str = "./run/google_gemini_cookie.json"
    api_key: str = ""
    max_requestion: int = 1024
    max_repeat_times: int = 3
    trigger: List[str] = []
    init_api: bool = False
    init_web: bool = False
    init_gemini: bool = False
    use_web_ask: bool = False
    models: List[str] = []
    models_api: List[str] = []
    models_gemini: List[str] = []
    loop: Any

    def is_call(self, question) -> bool:
        for call in self.trigger:
            if call.lower() in question.lower():
                return True
        return False

    @property
    def init(self) -> bool:
        if self.init_gemini:
            return True
        if self.init_api:
            return True
        if self.init_web:
            return True
        return False

    def get_models(self) -> List[str]:
        return self.models

    def ask(
        self,
        question: str,
        model: str = "",
        timeout: int = 5,
    ) -> Generator[dict, None, None]:

        if not len(model) and len(self.models):
            if len(self.models_gemini):
                model = self.models_gemini[0]
            else:
                model = self.models[0]

        if model in self.models_gemini:
            yield from self.ask_gemini(question, model, timeout)
        elif model in self.models_api:
            yield from self.api_ask(question, model, timeout)
        else:
            yield from self.__fuck_async(self.web_ask(question, timeout))

    def ask_gemini(
        self, question: str, model: str, timeout: int = 5
    ) -> Generator[dict, None, None]:
        answer = {"message": "", "code": 1}

        if (not self.init_gemini) and self.__fuck_async(self.__bot_create()):
            log_err("fail to create gemini bot")
            answer["code"] = -1
            return answer

        req_cnt = 0

        while req_cnt < self.max_repeat_times:
            req_cnt += 1
            answer["code"] = 1

            try:
                model = self.gemini.GenerativeModel(model)

                message = ""
                for chunk in model.generate_content(question, stream=True):
                    message += chunk.text
                    answer["message"] = message
                    yield answer

                answer["code"] = 0
                yield answer

            except Exception as e:
                log_err("fail to ask: " + str(e))
                log_info("server fail, maybe need check api_kei")

                answer["message"] = str(e)
                answer["code"] = -1
                yield answer
                if req_cnt < self.max_repeat_times:
                    log_dbg("sleep 5...")
                    time.sleep(5)

                log_info("reload bot")
                self.init_gemini = False
                self.__fuck_async(self.__bot_create())

            # request complate.
            if answer["code"] == 0:
                break

    def api_ask(
        self,
        question: str,
        model: str,
        timeout: int = 5,
    ) -> Generator[dict, None, None]:
        answer = {"message": "", "code": 1}

        if (not self.init_api) and self.__fuck_async(self.__bot_create()):
            log_err("fail to create google api bot")
            answer["code"] = -1
            return answer

        req_cnt = 0

        while req_cnt < self.max_repeat_times:
            req_cnt += 1
            answer["code"] = 1

            try:
                log_dbg("try ask: " + str(question))

                calc_prompt = f"""
Please solve the following problem.

{question}

----------------

Important: Use the calculator for each step.
Don't do the arithmetic in your head. 

To use the calculator wrap an equation in <calc> tags like this: 

<calc> 3 cats * 2 hats/cat </calc> = 6

----------------

"""
                equation = None
                while equation is None:
                    completion = self.chatbot.generate_text(
                        model=model,
                        prompt=calc_prompt,
                        stop_sequences=["</calc>"],
                        # The maximum length of the response
                        max_output_tokens=4096,
                    )

                    try:
                        answer["message"], equation = completion.result.split(
                            "<calc>", maxsplit=1
                        )
                        res = answer["message"]
                        log_dbg(f"{str(res)}")

                        yield answer

                    except Exception:
                        continue

                answer["code"] = 0
                yield answer

            except Exception as e:
                log_err("fail to ask: " + str(e))
                log_info("server fail, maybe need check api_kei")

                answer["message"] = str(e)
                answer["code"] = -1
                yield answer
                if req_cnt < self.max_repeat_times:
                    log_dbg("sleep 5...")
                    time.sleep(5)

                log_info("reload bot")
                self.init_api = False
                self.__fuck_async(self.__bot_create())

            # request complate.
            if answer["code"] == 0:
                break

    async def web_ask(
        self,
        question: str,
        timeout: int = 360,
    ) -> Generator[dict, None, None]:
        answer = {"message": "", "code": 1}

        if (not self.init_web) and (self.__bot_create()):
            log_err("fail to create google bot")
            answer["code"] = -1
            yield answer
            return

        req_cnt = 0

        while req_cnt < self.max_repeat_times:
            req_cnt += 1
            answer["code"] = 1

            try:
                log_dbg("try ask: " + str(question))

                response = self.webchat.generate_content(question)
                answer["message"] = response

                log_dbg(f"recv Gemini: {str(answer['message'])}")

                answer["code"] = 0
                yield answer

            except Exception as e:
                log_err("fail to ask: " + str(e))
                log_info("server fail, maybe need check cookie")

                answer["message"] = str(e)
                answer["code"] = -1
                yield answer

                if req_cnt < self.max_repeat_times:
                    log_dbg(f"sleep 5s...")
                    time.sleep(5)

                log_info("reload bing")
                self.init_web = False
                await self.__bot_create()

            # request complate.
            if answer["code"] == 0:
                break

    async def __bot_create(self):

        if len(self.api_key) and not self.init_gemini:
            try:
                import google.generativeai as genai

                self.gemini = genai

                self.gemini.configure(api_key=self.api_key)
                models = [
                    m
                    for m in self.gemini.list_models()
                    if "generateContent" in m.supported_generation_methods
                ]
                self.models_gemini = [m.name for m in models]
                self.models.extend(self.models_gemini)

                log_dbg(f"avalible model: {self.models_gemini}")
                self.init_gemini = True
                log_dbg("google gemini init done")

            except Exception as e:
                self.init_gemini = False
                log_err(f"fail to create gemini google: {e}")

        if len(self.api_key) and not self.init_api:
            try:
                import google.generativeai as palm

                self.chatbot = palm

                self.chatbot.configure(api_key=self.api_key)
                models = [
                    m
                    for m in self.chatbot.list_models()
                    if "generateText" in m.supported_generation_methods
                ]
                self.models_api = [m.name for m in models]
                self.models.extend(self.models_api)

                log_dbg(f"avalible model: {self.models_api}")
                self.init_api = True
                log_dbg("google api init done")
            except Exception as e:
                self.init_api = False
                log_err(f"fail to create api google: {e}")

        if (
            False
            and not self.init_web
            and len(self.cookie_1PSID)
            and len(self.cookie_1PSIDTS)
            and len(self.cookie_NID)
        ):
            try:
                cookies = {
                    "__Secure-1PSID": self.cookie_1PSID,
                    "__Secure-1PSIDTS": self.cookie_1PSIDTS,
                    "NID": self.cookie_NID,
                }

                self.webchat = Gemini(cookie_fp=self.cookie_file)
                self.init_web = True
                self.models.append(f"Gemini")
                log_dbg("google web init done")
            except Exception as e:
                self.init_web = False
                log_err(f"fail to create web google: {e}")

        return not self.init

    def __fuck_async(self, async_gen):
        while True:
            try:
                yield self.loop.run_until_complete(async_gen.__anext__())
            except StopAsyncIteration:
                log_dbg("stop: " + str(StopAsyncIteration))
                break
            except Exception as e:
                log_dbg("fail to get res " + str(e))
                break

    def __init__(self, setting) -> None:
        self.__load_setting(setting)

        try:
            asyncio.run(self.__bot_create())

            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop = asyncio.get_event_loop()

        except Exception as e:
            log_err("fail to init google: " + str(e))
            self.init = False

    def __load_setting(self, setting):

        try:
            self.max_requestion = setting["max_requestion"]
        except Exception as e:
            log_err("fail to load google config: " + str(e))
            self.max_requestion = 1024
        try:
            self.cookie_1PSID = setting["cookie_1PSID"]
        except Exception as e:
            log_err("fail to load google config: " + str(e))
            self.cookie_1PSID = ""
        try:
            self.cookie_1PSIDTS = setting["cookie_1PSIDTS"]
        except Exception as e:
            log_err("fail to load google config: " + str(e))
            self.cookie_1PSIDTS = ""
        try:
            self.cookie_NID = setting["cookie_NID"]
        except Exception as e:
            log_err("fail to load google config: " + str(e))
            self.cookie_NID = ""
        try:
            self.api_key = setting["api_key"]
        except Exception as e:
            log_err("fail to load google config: " + str(e))
            self.api_key = ""
        try:
            self.max_repeat_times = setting["max_repeat_times"]
        except Exception as e:
            log_err("fail to load google config: " + str(e))
            self.max_repeat_times = 3
        try:
            self.trigger = setting["trigger"]
        except Exception as e:
            log_err("fail to load google config: " + str(e))
            self.trigger = ["@google", "#google"]


# call bot_ plugin
class Bot(BotType):
    # This has to be globally unique
    type: str
    bot: GoogleAPI

    def __init__(self):
        self.type = GoogleAPI.type

    @property
    def init(self) -> bool:
        return self.bot.init

    # when time call bot
    def is_call(self, caller: BotType, ask_data: Any) -> bool:
        question = caller.bot_get_question(ask_data)
        return self.bot.is_call(question)

    # get support model
    def get_models(self, caller: BotType) -> List[str]:
        return self.bot.get_models()

    # ask bot
    def ask(
        self, caller: BotType, ask_data: Any, timeout: int = 60
    ) -> Generator[dict, None, None]:
        question = caller.bot_get_question(ask_data)
        model = caller.bot_get_model(ask_data)
        yield from self.bot.ask(question, model, timeout)

    # exit bot
    def when_exit(self, caller: BotType):
        pass

    # init bot
    def when_init(self, caller: BotType):
        global log_info, log_dbg, log_err
        log_info = caller.bot_log_info
        log_dbg = caller.bot_log_dbg
        log_err = caller.bot_log_err

        self.setting = caller.bot_load_setting(self.type)
        self.bot = GoogleAPI(self.setting)
