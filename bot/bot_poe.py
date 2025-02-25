from typing import Generator, List, Any, Dict
import time
import poe

log_dbg, log_err, log_info = print, print, print
from aimi_plugin.bot.type import Bot as BotBase
from aimi_plugin.bot.type import BotAskData, BotType


class PoeAPI:
    type: str = BotType.Poe
    chatbot: Any
    max_requestion: int = 1024
    max_repeat_times: int = 3
    cookie_key: str = ""
    models: Dict[str, Dict] = {}
    init: bool = False

    def is_call(self, question) -> bool:
        for default in self.models["default"]["trigger"]:
            if default.lower() in question.lower():
                return True

        return False

    def __get_bot_model(self, question: str):
        for model_name, model_info in self.models.items():
            if "default" == model_name:
                continue

            model_trigger = model_info["trigger"]
            if not model_trigger:
                continue

            for call in model_trigger:
                if call.lower() in question.lower():
                    return model_info["model"]

        return self.models["default"]["model"]

    # get support model
    def get_models(self) -> List[str]:
        if not self.init:
            return []

        models = []

        for model_name, model_info in self.models.items():
            if "default" == model_name:
                continue
            models.append(model_info["model"])

        return models

    def ask(
        self,
        question: str,
        timeout: int = 60,
    ) -> Generator[dict, None, None]:
        yield from self.api_ask(question, timeout)

    def api_ask(
        self,
        question: str,
        timeout: int = 60,
    ) -> Generator[dict, None, None]:
        answer = {"message": "", "code": 1}

        if (not self.init) and (not self.__create_bot()):
            log_err(f"fail to create {self.type} bot")
            answer["code"] = -1
            return answer

        req_cnt = 0
        bot_model = self.__get_bot_model(question)

        while req_cnt < self.max_repeat_times:
            req_cnt += 1
            answer["code"] = 1

            try:
                log_dbg("try ask: " + str(question))

                for chunk in self.chatbot.send_message(bot_model, question):
                    answer["message"] = chunk["text"]
                    yield answer

                answer["code"] = 0
                yield answer

            except Exception as e:
                log_err("fail to ask: " + str(e))
                log_dbg("server fail, sleep 15")
                time.sleep(15)
                log_dbg(f"try recreate {self.type} bot")
                self.__create_bot()

                answer["message"] = str(e)
                answer["code"] = -1
                yield answer

            # request complate.
            if answer["code"] == 0:
                break

    def __create_bot(self):
        if self.cookie_key and len(self.cookie_key):
            try:
                new_bot = poe.Client(self.cookie_key)
                self.chatbot = new_bot
                self.init = True
                log_dbg(f"load {self.type} bot: " + str(self.chatbot.bot_names))
            except Exception as e:
                log_err(f"fail to init {self.type} bot: " + str(e))
                self.init = False

        return self.init

    def __init__(self, setting: Any) -> None:
        self.__load_setting(setting)
        self.__create_bot()

    def __load_models(self, setting):
        try:
            models = setting["models"]

            for model_name, model_info in models.items():
                self.models[model_name] = {}
                try:
                    self.models[model_name]["model"] = model_info["model"]
                except Exception as e:
                    log_err(
                        "model_name:{} no model, err:{}".format(str(model_name), str(e))
                    )
                    self.models[model_name]["model"] = None

                try:
                    self.models[model_name]["trigger"] = model_info["trigger"]
                except Exception as e:
                    log_dbg(
                        "model_name:{} no trigger, err:{}".format(
                            str(model_name), str(e)
                        )
                    )
                    self.models[model_name]["trigger"] = None

        except Exception as e:
            self.models = {}
            log_err(f"fail to load {self.type} model cfg: " + str(e))

    def __load_setting(self, setting: Any):
        try:
            self.max_requestion = setting["max_requestion"]
        except Exception as e:
            log_err(f"fail to load {self.type} config: " + str(e))
            self.max_requestion = 512
        try:
            self.max_repeat_times = setting["max_repeat_times"]
        except Exception as e:
            log_err(f"fail to load {self.type} config: " + str(e))
            self.max_repeat_times = 3
        try:
            self.cookie_key = setting["cookie_p-b"]
        except Exception as e:
            log_err(f"fail to load {self.type} config: " + str(e))
            self.cookie_key = ""

        self.__load_models(setting)


# call bot_ plugin
class Bot(BotBase):
    # This has to be globally unique
    type: str
    bot: PoeAPI

    def __init__(self):
        self.type = PoeAPI.type

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
        yield from self.bot.ask(ask_data.question, ask_data.timeout)

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
        self.bot = PoeAPI(self.setting)
