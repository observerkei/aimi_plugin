import asyncio
from typing import Generator, List, Any, Dict
import time
import poe

log_dbg, log_err, log_info = print, print, print

class PoeAPI:
    type: str = 'poe'
    chatbot: Any
    max_requestion: int = 1024
    max_repeat_times: int = 3
    cookie_key: str = ''
    models: Dict[str, Dict] = {}
    init: bool = False

    def is_call(self, question) -> bool:
        for default in self.models['default']['trigger']:
            if default.lower() in question.lower():
                return True
        
        return False

    def __get_bot_model(self, question: str):
        for model_name, model_info in self.models.items():
            if 'default' == model_name:
                continue
            
            model_trigger = model_info['trigger']
            if not model_trigger:
                continue

            for call in model_trigger:
                if call.lower() in question.lower():
                    return model_info['model']
        
        return self.models['default']['model']

    def ask(
        self,
        question: str,
        timeout: int = 360,
    ) -> Generator[dict, None, None]:
        yield from self.api_ask(question, timeout)

    def api_ask(
        self,
        question: str,
        timeout: int = 360,
    ) -> Generator[dict, None, None]:
        answer = { 
           "message": '',
           "code": 1
        }

        if (not self.init) and (not self.__create_bot()):
            log_err('fail to create qoe bot')
            answer['code'] = -1
            return answer

        req_cnt = 0
        bot_model = self.__get_bot_model(question)
        
        while req_cnt < self.max_repeat_times:
            req_cnt += 1
            answer['code'] = 1
            
            try:
                log_dbg('try ask: ' + str(question))

                for chunk in self.chatbot.send_message(
                    bot_model,
                    question
                ):
                    answer['message'] = chunk['text']
                    yield answer

                answer['code'] = 0
                yield answer
             
            except Exception as e:
                log_err('fail to ask: ' + str(e))
                log_info('server fail, sleep 15')
                time.sleep(15)
                log_info("try recreate poe bot")
                self.__create_bot()
                
                answer['message'] = str(e)
                answer['code'] = -1
                yield answer

            # request complate.
            if answer['code'] == 0:
                break

    def __create_bot(self):
        if self.cookie_key and len(self.cookie_key):
            try:
                new_bot = poe.Client(self.cookie_key)
                self.chatbot = new_bot
                self.init = True
                log_info('load poe bot: ' + str(self.chatbot.bot_names))
            except Exception as e:
                log_err('fail to init poe bot: ' + str(e))
                self.init = False

        return self.init
    
    def __init__(self, setting: Any) -> None:
        self.__load_setting(setting)
        self.__create_bot()

    def __load_models(self, setting):
        try:
            models = setting['models']

            for model_name, model_info in models.items():
                self.models[model_name] = {}
                try:
                    self.models[model_name]['model'] = model_info['model']
                except Exception as e:
                    log_err('model_name:{} no model, err:{}'.format(str(model_name), str(e)))
                    self.models[model_name]['model'] = None

                try:
                    self.models[model_name]['trigger'] = model_info['trigger']
                except Exception as e:
                    log_dbg('model_name:{} no trigger, err:{}'.format(str(model_name), str(e)))
                    self.models[model_name]['trigger'] = None
                    
        except Exception as e:
            self.models = {}
            log_err('fail to load poe model cfg: ' + str(e))
    
    def __load_setting(self, setting: Any):
        try:
            self.max_requestion = setting['max_requestion']
        except Exception as e:
            log_err('fail to load poe config: ' + str(e))
            self.max_requestion = 512
        try:
            self.max_repeat_times = setting['max_repeat_times']
        except Exception as e:
            log_err('fail to load poe config: ' + str(e))
            self.max_repeat_times = 3
        try:
            self.cookie_key = setting['cookie_p-b']
        except Exception as e:
            log_err('fail to load poe config: ' + str(e))
            self.cookie_key = ''

        self.__load_models(setting)


# call bot_ plugin
class Bot:
    # This has to be globally unique
    type: str
    bot: PoeAPI

    def __init__(self):
        self.type = PoeAPI.type

    # when time call bot
    def is_call(self, caller: Any, ask_data: Any) -> bool:
        question = caller.bot_get_question(ask_data)
        return self.bot.is_call(question)

    # ask bot
    def ask(self, caller: Any, ask_data: Any, timeout: int = 60) -> Generator[dict, None, None]:
        question = caller.bot_get_question(ask_data)
        yield from self.bot.ask(question, timeout)

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
        self.bot = PoeAPI(self.setting)

