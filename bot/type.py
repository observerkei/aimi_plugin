from typing import Generator, List, Dict, Any, Tuple, Optional, Union
from pydantic import BaseModel, constr
import time

log_dbg, log_err, log_info = print, print, print


class BotType:
    Bing: str = "bing"
    Google: str = "google"
    OpenAI: str = "openai"
    Wolfram: str = "wolfram"
    Task: str = "task"
    LLaMA: str = 'llama'
    XAI: str = "xai"

class BotAskData(BaseModel):
    question: Optional[str]
    model: Optional[Union[str, None]] = ""
    messages: Optional[Union[List[Dict[str, str]], None]] = []
    conversation_id: Optional[Union[str, None]] = ""
    timeout: Optional[Union[int, None]] = 0
    aimi_name: Optional[Union[str, None]] = ""
    nickname: Optional[Union[str, None]] = ""
    preset: Optional[Union[str, None]] = ""
    history: Optional[Union[str, None]] = ""

# call bot_ plugin example
class Bot:
    # This has to be globally unique
    type: str = "public_name"
    trigger: str = "#public_name"
    bot: Any = None
    # no need define plugin_prefix
    plugin_prefix = "bot_"

    def __init__(self):
        pass

    @property
    def init(self) -> bool:
        pass

    def is_call(self, caller: 'Bot', req: str) -> bool:
        pass

    def get_models(self, caller: 'Bot') -> List[str]:
        pass

    def ask(self, caller: 'Bot', ask_data: BotAskData) -> Generator[dict, None, None]:
        pass

    def bot_ask(self, caller: 'Bot', bot_type: str, ask_data: BotAskData) -> Generator[dict, None, None]:
        pass

    def when_exit(self, caller: 'Bot'):
        pass

    def when_init(self, caller: 'Bot', setting: dict = None):
        pass

    def bot_set_response(self, code: int, message: str) -> Any:
        pass

    def bot_log_dbg(self, msg: str):
        pass

    def bot_log_err(self, msg: str):
        pass

    def bot_log_info(self, msg: str):
        pass

def make_history(talk_history: List[Dict]) -> str:
    history = ""

    talk_count = 0
    for talk in talk_history:
        content = ""
        it = ""
        for k, v in talk.items():
            if k == "role" and v == "user":
                talk_count += 1
                it = "我说:"
                continue
            elif k == "role" and v == "assistant":
                it = "你说:"
            if k != "content":
                continue
            content = v
        history += f"{talk_count} {it} {content}\n"
    return history

# OpenAI Messages 结构长度限制。
def process_messages(messages, max_messages = 1024):
    try:
        # Step 1: 新建一个 new_messages 数组
        new_messages = []
        
        # Step 2: 将 messages 的第一个数据直接加到 new_messages 中
        new_messages.append(messages[0])
        # 剔除 第一个数据，方便处理
        messages = messages[1:]
        
        # Step 3: 将 messages 的最后一个 role: user 的数据也加到 new_messages 中
        last_user_message = None
        user_cnt = 0
        assistant_cnt = 0
        message_pair = []

        for message in reversed(messages):
            if message['role'] == 'user':
                user_cnt = user_cnt + 1
                if user_cnt == 1:
                    # 默认倒数第一个是 user
                    new_messages.insert(1, message)
                else: 
                    message_pair.insert(0, message)

            elif message['role'] == 'assistant':
                assistant_cnt = assistant_cnt + 1
                message_pair = [message]


            if user_cnt > 1 and user_cnt == assistant_cnt + 1:
                # 倒序，先 assistant 再 user 
                # user - 1 == assistant 说明是一组 
                if len(str(message_pair)) + len(str(new_messages)) < max_messages:
                    # 先插 assistant 再插 user，这样顺序是对的。
                    new_messages.insert(1, message_pair[1])
                    new_messages.insert(1, message_pair[0])
        return new_messages
    except Exception as e:
        log_dbg(f'process messages fail: {str(e)}')
        return message

class OpenAIBot:
    type: str = "openai"
    max_messages: int = 1024
    max_repeat_times: int = 3
    max_request_minute_times: int = 10
    cur_request_minute_times: int = 0
    cur_time_seconds: int = 0
    api_key: str = ""
    api_base: str = ""
    models: Dict[str, Dict] = {}
    init: bool = False
    chatbot: Any

    def is_call(self, question: str) -> bool:
        for default in self.models["default"]["trigger"]:
            if default.lower() in question.lower():
                return True

        return False

    def __cul_bot_model(self, question: str):
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
        try:
            yield from self.api_ask(model, messages, timeout)
        except Exception as e:
            log_err(f"fail to api ask: {str(e)}")
            yield f'fail to ask: {str(e)}'

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
        
        if len(str(messages)) > self.max_messages:
            log_dbg(f"messages > {max_messages}, try fix")
            messages = process_messages(messages, self.max_messages)

        req_cnt = 0
        question = messages[-1]["content"]
        if not bot_model or not len(bot_model):
            bot_model = self.__cul_bot_model(question)

        log_dbg(f"use model: {bot_model}")

        log_dbg(f"msg({str(type(messages))}): {str(messages)}")

        while req_cnt < self.max_repeat_times:
            req_cnt += 1
            answer["code"] = 1

            try:
                log_dbg("try ask: " + str(question))
                res = None

                for event in self.chatbot.chat.completions.create(
                    model=bot_model,
                    messages=messages,
                    stream=True,
                ):
                    if (event.choices[0].finish_reason 
                        and event.choices[0].finish_reason == "stop"):
                        break
                    if (not event.choices[0].delta.content):
                        continue

                    answer["message"] += event.choices[0].delta.content
                    yield answer

                    res = event

                log_dbg(f"res: {str(    )}")

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

    def __create_bot(self) -> bool:
        if (self.api_key and len(self.api_key)) and (
            self.api_base and len(self.api_base)
        ):
            try:
                import os
                from openai import OpenAI

                self.chatbot = OpenAI(
                    api_key=self.api_key,
                    base_url=self.api_base,
                )

                models = self.chatbot.models.list()  
                log_dbg(f"all model: {self.models}")

                self.init = True
            except Exception as e:
                log_err(f"fail to init {self.type} bot: " + str(e))
                self.init = False

        return self.init

    def __init__(self, caller: Bot, setting: Any) -> None:
        global log_dbg, log_err, log_info
        log_info = caller.bot_log_info
        log_dbg = caller.bot_log_dbg
        log_err = caller.bot_log_err

        self.__load_setting(setting)
        self.__create_bot()


    def __load_models(self, setting):
        try:
            models = setting["models"]
            self.models = {}

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
            self.max_messages = setting["max_messages"]
        except Exception as e:
            log_err(f"fail to load {self.type} config: " + str(e))
            self.max_messages = 512
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

