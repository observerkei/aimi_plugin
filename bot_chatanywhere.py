from typing import Generator, List, Any, Dict
import time
import openai
import requests

log_dbg, log_err, log_info = print, print, print


class ChatAnywhereAPI:
    type: str = "chatanywhere"
    max_requestion: int = 1024
    max_repeat_times: int = 3
    max_request_minute_times: int = 10
    cur_request_minute_times: int = 0
    cur_time_seconds: int = 0
    api_key: str = ""
    api_base: str = ""
    models: Dict[str, Dict] = {}
    init: bool = False

    def is_call(self, question: str) -> bool:
        for default in self.models["default"]["trigger"]:
            if default.lower() in question.lower():
                return True

        return False

    def __get_bot_model(self, question: str):
        bot_model = self.models["default"]["model"]
        bot_model_len = 0

        for model_name, model_info in self.models.items():
            if "default" == model_name:
                continue

            model_trigger = model_info["trigger"]
            if not model_trigger:
                continue

            for call in model_trigger:
                if not (call.lower() in question.lower()):
                    continue
                if len(call) < bot_model_len:
                    continue
                bot_model = model_info["model"]
                bot_model_len = len(bot_model)

        return bot_model

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
        model: str,
        messages: List[Dict] = [],
        timeout: int = 360,
    ) -> Generator[dict, None, None]:
        yield from self.api_ask(model, messages, timeout)

    def api_ask(
        self,
        bot_model: str,
        messages: List[Dict] = [],
        timeout: int = 360,
    ) -> Generator[dict, None, None]:
        answer = {"message": "", "code": 1}

        if (not self.init) and (not self.__create_bot()):
            log_err(f"fail to create {self.type} bot")
            answer["code"] = -1
            return answer

        now_time_seconds = int(time.time())
        if not self.cur_time_seconds or (self.cur_time_seconds + 60 < now_time_seconds):
            self.cur_time_seconds = now_time_seconds
            self.cur_request_minute_times = 0
        else:
            self.cur_request_minute_times += 1

        if self.cur_request_minute_times >= self.max_request_minute_times:
            answer["message"] = f"to many request, now: {self.cur_request_minute_times}"
            answer["code"] = 0
            yield answer
            return

        req_cnt = 0
        question = messages[-1]["content"]
        if not bot_model or not len(bot_model):
            bot_model = self.__get_bot_model(question)

        log_dbg(f"use model: {bot_model}")

        log_dbg(f"msg: {str(messages)}")

        while req_cnt < self.max_repeat_times:
            req_cnt += 1
            answer["code"] = 1

            try:
                log_dbg("try ask: " + str(question))
                res = None

                completion = {"role": "", "content": ""}
                for event in openai.ChatCompletion.create(
                    model=bot_model,
                    messages=messages,
                    stream=True,
                ):
                    if event["choices"][0]["finish_reason"] == "stop":
                        # log_dbg(f'recv complate: {completion}')
                        break
                    for delta_k, delta_v in event["choices"][0]["delta"].items():
                        if delta_k != "content":
                            # skip none content
                            continue
                        # log_dbg(f'recv stream: {delta_k} = {delta_v}')
                        completion[delta_k] += delta_v

                        answer["message"] = completion[delta_k]
                        yield answer

                    res = event

                log_dbg(f"res: {str(res)}")

                answer["code"] = 0
                yield answer

            except Exception as e:
                log_err("fail to ask: " + str(e))
                log_info("server fail, sleep 15")
                time.sleep(15)
                log_info(f"try recreate {self.type} bot")
                self.__create_bot()

                answer["message"] = str(e)
                answer["code"] = -1
                yield answer

            # request complate.
            if answer["code"] == 0:
                break

    def __create_bot(self) -> bool:
        if (self.api_key and len(self.api_key)) and (
            self.api_base and len(self.api_base)
        ):
            try:
                """
                api_status = 'https://chimeragpt.adventblocks.cc/'
                response = requests.get(api_status)
                if 'Api works!' in response.text:
                    log_info(f'load {self.type} bot done.')
                else:
                    raise Exception(f"fail to init {self.type}, res: {str(response.text)}")
                """
                openai.api_key = self.api_key
                openai.api_base = self.api_base

                models = openai.Model.list()
                for model in models["data"]:
                    log_dbg(f"avalible model: {str(model['id'])}")

                self.init = True
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
            self.api_key = setting["api_key"]
        except Exception as e:
            log_err(f"fail to load {self.type} config: " + str(e))
            self.api_key = ""
        try:
            self.api_base = setting["api_base"]
        except Exception as e:
            log_err(f"fail to load {self.type} config: " + str(e))
            self.api_base = ""
        try:
            self.max_request_minute_times = setting["max_request_minute_times"]
        except Exception as e:
            log_err(f"fail to load {self.type} config: " + str(e))
            self.max_request_minute_times = 10

        self.__load_models(setting)


# call bot_ plugin
class Bot:
    # This has to be globally unique
    type: str
    bot: ChatAnywhereAPI

    def __init__(self):
        self.type = ChatAnywhereAPI.type

    # when time call bot
    def is_call(self, caller: Any, ask_data: Any) -> bool:
        question = caller.bot_get_question(ask_data)
        return self.bot.is_call(question)

    # get support model
    def get_models(self, caller: Any) -> List[str]:
        return self.bot.get_models()

    # ask bot
    def ask(
        self, caller: Any, ask_data: Any, timeout: int = 60
    ) -> Generator[dict, None, None]:
        model = caller.bot_get_model(ask_data)
        messages = caller.bot_get_messages(ask_data)
        yield from self.bot.ask(model, messages, timeout)

    # exit bot
    def when_exit(self, caller: Any):
        pass

    # init bot
    def when_init(self, caller: Any):
        global log_info, log_dbg, log_err
        log_info = caller.bot_log_info
        log_dbg = caller.bot_log_dbg
        log_err = caller.bot_log_err

        self.setting = caller.bot_load_setting(self.type)
        self.bot = ChatAnywhereAPI(self.setting)
