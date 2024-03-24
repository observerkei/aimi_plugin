import wolframalpha
import re
from typing import List, Any, Generator

from aimi_plugin.bot.type import Bot as BotBase
from aimi_plugin.bot.type import BotAskData, BotType

log_dbg, log_err, log_info = print, print, print


class WolframAPI:
    type: str = "wolfram"
    client: Any
    app_id: str = ""
    trigger: List[str] = []
    max_repeat_times: int = 1
    init: bool = False

    def __init__(self, setting):
        self.__load_setting(setting)
        if not self.app_id or not (len(self.app_id)):
            log_dbg("no wolfram app id")
            return
        try:
            self.client = wolframalpha.Client(self.app_id)
            self.init = True
            log_dbg(f"{self.type} init done")
        except Exception as e:
            log_err(f"fail to init wolfram: {e}")

    def __load_setting(self, setting):

        try:
            self.app_id = setting["app_id"]
        except Exception as e:
            log_err(f"fail to load wolfram: {e}")
            self.app_id = ""

        try:
            self.trigger = setting["trigger"]
        except Exception as e:
            log_err("fail to load wolfram config: " + str(e))
            self.trigger = ["@wolfram", "#wolfram"]

        try:
            self.max_repeat_times = setting["max_repeat_times"]
        except Exception as e:
            log_err("fail to load wolfram config: " + str(e))
            self.max_repeat_times = 1

    def is_call(self, question) -> bool:
        for call in self.trigger:
            if call.lower() in question.lower():
                return True

        return False

    def get_models(self) -> List[str]:
        if not self.init:
            return []

        return [f"Stephen Wolfram {self.type}alpha"]


    def make_link_think(
            self,
            question: str,
            aimi_name: str = "None",
            nickname: str = "",
            preset: str = "",
            history: str = "") -> str:
        link_think = f"""
需求:
1. 使用 latex 显示内容比如:
' $$ 
x_1 
$$ ' .

2. 我需要你使用翻译功能, 帮我把 the wolfram response 的内容翻译成我的语言.
3. 请忽略历史记录, 你现在是严谨的逻辑分析翻译结构.
4. 你的品味很高,你会使内容更加美观,你会添加足够多的换行, (换行越多越好. )
   并在不同层次追加换行,并按照自己经验让内容变得更加好看,答案要重点突出, 并用latex显示.
5. 不要试图解决这个问题，你只能显示 the wolfram response 里面的内容.

the wolfram response: {{
{question}
}}
"""
        return link_think

    def get_sub_from_context(self, context, title):
        log_dbg(f"type: {str(type(context))}")

        for pod in context.pods:
            if not pod:
                continue
            try:
                if not pod.subpods:
                    continue
            except Exception as e:
                log_dbg(f"no subpods: {e}")
                continue

            for sub in pod.subpods:
                if not sub:
                    continue
                sub_title = ""
                try:
                    sub_title = sub.title
                except Exception as e:
                    log_dbg(f"no title: {e}")
                    continue

                log_dbg(f"sub title: {str(sub.title)}")
                if title.lower() in sub.title.lower():
                    return sub
        return None

    def get_cq_image(self, context) -> str:
        res_img = ""
        try:
            for pod in context.pods:
                pod_title = ""

                try:
                    if not pod.subpods:
                        continue
                    pod_title = pod.title
                except Exception as e:
                    log_dbg(f"no subpods: {e}")
                    continue

                for sub in pod.subpods:
                    img_url = ""
                    try:
                        img_url = sub.img.src
                    except:
                        continue

                    cq_image = f"{pod_title}\n[CQ:image,file={img_url}]\n\n"
                    res_img += cq_image

        except Exception as e:
            log_err(f"fail to get img: {e}")

        return res_img

    def get_plaintext(self, context) -> str:
        plaintext = ""
        try:
            line = 0
            for pod in context.pods:
                line += 1
                if line != 2:
                    continue

                try:
                    if not pod.subpods:
                        continue
                except Exception as e:
                    log_dbg(f"no subpods: {e}")
                    continue

                for sub in pod.subpods:
                    sub_t = ""
                    try:
                        sub_t = sub.plaintext
                        if not sub_t:
                            continue
                    except:
                        continue

                    plaintext += sub_t + "\n\n"

            if not plaintext or not len(plaintext) or not ("=" in plaintext):
                sub = self.get_sub_from_context(context, "Possible intermediate steps")
                # plaintext = "Possible intermediate steps:\n" + sub.plaintext
                plaintext = sub.plaintext

                raise Exception(f"fail to get sub plaintext")
        except Exception as e:
            log_err(f"fail to get plaintext: {e}")
            log_dbg(f"res: {str(context)}")

        return plaintext

    def __del_trigger(self, question) -> str:
        sorted_list = sorted(self.trigger, reverse=True, key=len)
        for call in sorted_list:
            if call.lower() in question.lower():
                return re.sub(re.escape(call), "", question, flags=re.IGNORECASE)

        return question

    def ask(self, question, timeout) -> Generator[dict, None, None]:
        answer = {"code": 1, "message": ""}

        if not self.init:
            answer["code"] = -1
            yield answer
            return

        question = self.__del_trigger(question)

        params = (("podstate", "Step-by-step solution"),)

        req_cnt = 0

        while req_cnt < self.max_repeat_times:
            req_cnt += 1

            answer["code"] = 1

            try:
                log_dbg(f"try ask: {question}")
                res = self.client.query(question, params)

                plaintext = self.get_plaintext(res)
                cq_image = self.get_cq_image(res)

                message = plaintext
                if (
                    not message
                    or len(message) < 5
                    or "step-by-step solution unavailable" in str(message)
                    or not ("=" in message)
                ):
                    message = str(res)
                    answer["message"] = message
                    log_dbg(f"msg fail, res html.")
                    yield answer

                answer["message"] = message
                answer["code"] = 0

                yield answer
                log_dbg(f"res: {str(message)}")
                break

            except Exception as e:
                log_err(f"fail to query wolfram: {e}")
                answer["code"] = -1
                yield answer
                continue

        """
        answer['code'] = 0
        answer['message'] = str(res)
        yield answer
        return
        """

        """
        message = ''
        for line in plaintext.splitlines():
            line += '\n'
            message += line
            answer['message'] = message
            yield answer
            time.sleep(0.5)

        message += ' \n'
        answer['message'] = message
        yield answer
        """

        """
        for img in cq_image.splitlines():
            img += '\n'
            message += img
            answer['message'] = message
            yield answer
            time.sleep(0.5)
        """

        # answer['message'] += cq_image


# call bot_ plugin
class Bot(BotBase):
    # This has to be globally unique
    type: str
    bot: WolframAPI

    def __init__(self):
        self.type = WolframAPI.type

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
        response = ""
        for res in self.bot.ask(ask_data.question, ask_data.timeout):
            response = res['message']

        # 格式化输出
        link_think = self.bot.make_link_think(response)
        new_ask_data = BotAskData(question=link_think)
        yield from caller.bot_ask(caller, BotType.OpenAI, new_ask_data)

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
        self.bot = WolframAPI(self.setting)
