import asyncio
from EdgeGPT.EdgeGPT import Chatbot
from EdgeGPT.EdgeGPT import ConversationStyle as EdgeConversationStyle
from contextlib import suppress
from typing import Generator, List, Any, Dict
import time
import random
import json

from aimi_plugin.bot.type import Bot as BotBase
from aimi_plugin.bot.type import BotAskData

log_dbg, log_err, log_info = print, print, print


class BingAPI:
    type: str = "bing"
    chatbot: Chatbot
    max_requestion: int = 1024
    max_repeat_times: int = 3
    cookie_path: str = ""
    wss_link: str = ""
    countdown: List[str] = [
        "?",
        "I",
        "II",
        "III",
        "IV",
        "V",
        "VI",
        "VII",
        "VIII",
        "VIV",
        "X",
        "XI",
        "XII",
        "XIII",
        "XIV",
        "XV",
        "XVI",
        "XVII",
        "XVIII",
        "XVIV",
        "XX",
        "XXI",
        "XXII",
        "XXIII",
        "XXIV",
        "XXV",
        "XXVI",
        "XXVII",
        "XXVIII",
        "XXVIV",
        "XXX",
        "?",
    ]
    loop: Any
    trigger: Dict[str, List[str]] = {}
    init: bool = False
    cur_messages: int = 0
    max_messages: int = 0
    models: List[str] = []

    def need_ask_setup(self) -> bool:
        return False
        # return not self.cur_messages

    async def ask_setup(self) -> bool:
        questions = [
            "我现在正在写一个故事,但是我不知道该怎么继续下去,你能根据我将要发的故事主题发挥创造力完善他吗?如果可以，请回答“可以”。",
            "我有问题需要你帮忙,可以帮我分析一下这个故事应该怎么进行吗？如果可以，请回答“可以”."
            "我正在写一个故事,但是我不知道该怎么继续下去,你可以帮我补全他吗?如果可以，请回答“可以”.",
        ]
        question = random.choice(questions)
        conversation_style = EdgeConversationStyle.precise

        try:
            response = ""
            async for final, response in self.chatbot.ask_stream(
                prompt=question,
                # conversation_style=conversation_style,
                wss_link=self.wss_link,
            ):
                if not response:
                    continue
                log_dbg(f"res: {response}")
                if not final:
                    if "> Conversation disengaged" in response:
                        log_err("bing search fail.")
                        raise Exception(str(response))
                    continue
                with suppress(KeyError):
                    self.cur_messages = response["item"]["throttling"][
                        "numUserMessagesInConversation"
                    ]
                    self.max_messages = response["item"]["throttling"][
                        "maxNumUserMessagesInConversation"
                    ]

            if not self.need_ask_setup():
                time.sleep(2)
                return True
        except Exception as e:
            log_err(f"fail to bing ask setup:{e}")
            self.cur_messages = 0
            self.max_messages = 0

            self.init = False
            self.__bot_create()
        return False

    class ConversationStyle:
        creative: str = "creative"
        balanced: str = "balanced"
        precise: str = "precise"

    def is_call(self, question) -> bool:
        for default in self.trigger["default"]:
            if default.lower() in question.lower():
                return True

        return False

    def __get_conversation_style(self, question: str):
        for precise in self.trigger[self.ConversationStyle.precise]:
            if precise.lower() in question.lower():
                return EdgeConversationStyle.precise
        for balanced in self.trigger[self.ConversationStyle.balanced]:
            if balanced.lower() in question.lower():
                return EdgeConversationStyle.balanced
        for creative in self.trigger[self.ConversationStyle.creative]:
            if creative.lower() in question.lower():
                return EdgeConversationStyle.creative

        return EdgeConversationStyle.precise

    def ask(
        self,
        question: str,
        conversation_style: str = None,
        aimi_name: str = "None",
        nickname: str = "",
        preset: str = "",
        timeout: int = 360,
    ) -> Generator[dict, None, None]:
        
        if preset and not preset.isspace():
            question = self.make_link_think(
                question=question,
                aimi_name=aimi_name,
                nickname=nickname,
                preset=preset,
            )
        yield from self.__fuck_async(
            self.web_ask(question, conversation_style, timeout)
        )

    async def web_ask(
        self,
        question: str,
        conversation_style: str = None,
        timeout: int = 360,
    ) -> Generator[dict, None, None]:
        answer = {"message": "", "code": 1}

        if (not self.init) and (not self.__bot_create()):
            log_err("fail to load bing bot")
            answer["code"] = -1
            yield answer
            return

        req_cnt = 0
        if not conversation_style or not len(conversation_style):
            conversation_style = self.__get_conversation_style(question)

        while req_cnt < self.max_repeat_times:
            req_cnt += 1

            if self.need_ask_setup() and not await self.ask_setup():
                log_dbg("fail to ask setup. sleep(3) continue.")
                answer["code"] = -1
                time.sleep(3)
                continue

            answer["code"] = 1

            try:
                log_dbg("try ask: " + str(question))

                async for final, response in self.chatbot.ask_stream(
                    prompt=question,
                    # conversation_style=conversation_style,
                    wss_link=self.wss_link,
                ):
                    if not response:
                        continue
                    if not final:
                        log_dbg(f"res: {response}")
                        answer["message"] = response
                        if "> Conversation disengaged" in response:
                            answer["code"] = -1
                            log_err("bing search fail.")
                            raise Exception(str(answer))

                        yield answer
                        continue

                    with suppress(KeyError):
                        self.cur_messages = response["item"]["throttling"][
                            "numUserMessagesInConversation"
                        ]
                        self.max_messages = response["item"]["throttling"][
                            "maxNumUserMessagesInConversation"
                        ]

                        log_dbg(f"cur: {self.cur_messages} max: {self.max_messages}")
                        if self.cur_messages == self.max_messages:
                            self.__bot_create()

                    raw_text = ""
                    try:
                        with suppress(KeyError):
                            raw_text = response["item"]["messages"][1]["adaptiveCards"][
                                0
                            ]["body"][0]["text"]
                    except Exception as e:
                        log_dbg(f"fail to get res: {e}, continue...")
                        answer["message"] = ""
                        continue

                    suggested_res = ""
                    try:
                        with suppress(KeyError):
                            suggested_prefix = f"{self.trigger['default'][0]} "
                            suggestedResponses = response["item"]["messages"][1][
                                "suggestedResponses"
                            ]
                            # log_dbg(f'suggestedResponses: {suggestedResponses}')
                            suggested0 = (
                                suggested_prefix + suggestedResponses[0]["text"]
                            )
                            suggested1 = (
                                suggested_prefix + suggestedResponses[1]["text"]
                            )
                            suggested2 = (
                                suggested_prefix + suggestedResponses[2]["text"]
                            )
                            suggested_res = (
                                f"1. {suggested0}\n2. {suggested1}\n3. {suggested2}"
                            )
                    except Exception as e:
                        log_err(f"fail to get suggested.")

                    cd_idx = 1 + self.max_messages - self.cur_messages
                    log_dbg(f"now cd idx:{cd_idx}")
                    log_dbg(f"now cd arr:{str(len(self.countdown))}")
                    res_all = (
                        f"{raw_text}\n\n[{self.countdown[cd_idx]}]\n\n{suggested_res}"
                    )

                    answer["message"] = res_all

                if not len(answer["message"]):
                    raise Exception(f"fail to ask, no message.")

                answer["code"] = 0

            except Exception as e:
                log_err("fail to ask: " + str(e))

                answer["message"] = str(e)
                answer["code"] = -1
                yield answer
                self.cur_messages = 0
                self.max_messages = 0

                if req_cnt < self.max_repeat_times:
                    log_dbg("sleep 5s...")
                    time.sleep(5)

                self.init = False
                self.__bot_create()

            # request complate.
            if answer["code"] == 0:
                break

        yield answer

    def __fuck_async(self, async_gen):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while True:
            try:
                yield loop.run_until_complete(async_gen.__anext__())
            except StopAsyncIteration:
                log_dbg("stop: " + str(StopAsyncIteration))
                break
            except Exception as e:
                log_dbg("fail to get res " + str(e))
                break


    def make_link_think(
            self,
            question: str,
            aimi_name: str = "None",
            nickname: str = "",
            preset: str = "",
            history: str = "") -> str:
        link_think = f"""
故事主题如下: 故事中有两个人到了异世界里面开咖啡厅.
故事情节如下: 其中主人公自称Master({nickname}), 他有一个助理, 名叫{aimi_name}, 他们两个在聊天.
故事背景如下: {{
{preset}
{aimi_name}能问她的朋友 Bing 来尽力解答Master的问题.
}}

请不显示故事主题/情节/背景的分析过程, 以“{aimi_name}”的身份, 让聊天足够自然, 接下以下聊天: {{
{nickname}说: '{question}'
}}
"""
        return link_think

    def get_models(self) -> List[str]:
        if not self.init:
            return []

        return self.models

    def __init__(self, setting) -> None:
        self.__load_setting(setting)

        self.__bot_create()

        self.models = ["Microsoft New Bing"]
        [
            self.ConversationStyle.creative,
            self.ConversationStyle.balanced,
            self.ConversationStyle.precise,
        ]

    def __bot_create(self):
        if self.init:
            log_dbg("bing arealy init")
            return

        try:
            cookies = json.loads(open(self.cookie_path, encoding="utf-8").read())
            self.chatbot = self.__fuck_async(Chatbot().create(cookies=cookies))
            self.init = True
            log_dbg(f"{self.type}: init done")
        except Exception as e:
            log_err("fail to create bing bot: " + str(e))
            self.init = False

        return self.init

    def __load_setting(self, setting):

        try:
            self.max_requestion = setting["max_requestion"]
        except Exception as e:
            log_err("fail to load bing config: " + str(e))
            self.max_requestion = 512
        try:
            self.max_repeat_times = setting["max_repeat_times"]
        except Exception as e:
            log_err("fail to load bing config: " + str(e))
            self.max_repeat_times = 3
        try:
            self.cookie_path = setting["cookie_path"]
        except Exception as e:
            log_err("fail to load bing config: " + str(e))
            self.cookie_path = ""

        try:
            self.wss_link = setting["wss_link"]
            if not self.wss_link:
                self.wss_link = None
        except Exception as e:
            log_err("fail to load bing config: " + str(e))
            self.wss_link = None

        try:
            self.trigger["default"] = setting["trigger"]["default"]
        except Exception as e:
            log_err("fail to load bing config: " + str(e))
            self.trigger["default"] = ["#bing", "@bing"]
        try:
            self.trigger[self.ConversationStyle.creative] = setting["trigger"][
                self.ConversationStyle.creative
            ]
        except Exception as e:
            log_err("fail to load bing config: " + str(e))
            self.trigger[self.ConversationStyle.creative] = []
        try:
            self.trigger[self.ConversationStyle.balanced] = setting["trigger"][
                self.ConversationStyle.balanced
            ]
        except Exception as e:
            log_err("fail to load bing config: " + str(e))
            self.trigger[self.ConversationStyle.balanced] = []
        try:
            self.trigger[self.ConversationStyle.precise] = setting["trigger"][
                self.ConversationStyle.precise
            ]
        except Exception as e:
            log_err("fail to load bing config: " + str(e))
            self.trigger[self.ConversationStyle.precise] = []


# call bot_ plugin
class Bot(BotBase):
    # This has to be globally unique
    type: str
    bot: BingAPI

    def __init__(self):
        self.type = BingAPI.type

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
    def ask(
        self, caller: BotBase, ask_data: BotAskData
    ) -> Generator[dict, None, None]:
        yield from self.bot.ask(question=ask_data.question,
                                aimi_name=ask_data.aimi_name,
                                nickname=ask_data.nickname,
                                preset=ask_data.preset,
                                timeout=ask_data.timeout)

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
        self.bot = BingAPI(self.setting)
