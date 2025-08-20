import ollama
import json
import re
import os
from dotenv import load_dotenv
import docker

class BasicActionLLM:
    def __init__(self):
        self.model = ""
        self.conversation_history = []
        self.system_prompt = """
            размышляй и пиши только на Русском языке
            Нужно запросить НАЗВАНИЕ файла согласно шаблону начиная с @, пример @test.py
            Анализ файла будет выполнятся стороними средствами, нужно просто ответить в json
            Когда пользователь написал файл по шаблону, нужно ответить в формате json по следжующей схеме:
            {
                file_name: Имя файла(без символа @)
            }
        """
        self.finish_prompt = ""
        self.think_delete = False

    def add_to_context(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})

    def clear_context(self):
        self.conversation_history = []

    def get_llm_response(self, prompt: str, role='user'):
        final_response = False
        self.add_to_context(role, prompt)
        try:
            client = ollama.Client(host=os.getenv('HOST_PORT_OLLAMA'))
            response = client.chat(
                model=os.getenv('OLLAMA_MODEL'),
                messages=self.conversation_history,
                stream=False,                
            )
            llm_response = response["message"]["content"].strip()
            self.add_to_context("assistant", llm_response)
            if self.think_delete:
                llm_response = self.clean_response(llm_response)
                try:
                    llm_response = json.loads(llm_response)
                    final_response = True
                except Exception as e:
                    pass
                return final_response, llm_response
            else:
                try:
                    llm_response_clear = self.clean_response(llm_response)
                    llm_response_clear = json.loads(llm_response_clear)
                    llm_response = llm_response_clear
                    final_response = True
                except Exception as e:
                    pass
                return final_response, llm_response
        except Exception as e:
            print(f"Ошибка при обращении к LLM: {str(e)}")
            return final_response, ""

    def clean_response(self, llm_response: str):
        return re.sub(r"<think>.*?</think>", "", llm_response, flags=re.DOTALL).strip()

    def get_gamedev_tz_info(self):
        self.add_to_context("system", self.system_prompt)
        print(f"Бот: Могу проверить файл на Python, введите название файла в проекте для проверки")
        while True:
            try:
                user_input = input("\nВы: ").strip()
                final, response = self.get_llm_response(user_input)
                if final:
                    result = DockerRun.run_file_python(response.get('file_name'))
                    print(f'Результат выполнения файла: {result}')
                    break
                print(f"Бот_ТЗ: {response}")
            except Exception as e:
                print(f"Произошла ошибка: {e}")

class DockerRun(BasicActionLLM):
    def __init__(self):
        self.model = os.getenv('OLLAMA_MODEL')
        self.conversation_history = []

        self.sending_prompt = ""
        self.think_delete = True
            
    @staticmethod
    def run_file_python(file_path:str):
        project_folder = '/home/lifeteo/LLM/AI_Advent_2025/llm10/'
        folder = '/project/'
        client = docker.from_env()
        result = client.containers.run(
            image ='python:3',
            command =f'python "{folder + file_path}"',
            volumes={
                project_folder: {
                    'bind': folder,
                    'mode': 'ro'  # или 'ro' для read-only
                }
            },
            remove=True
        )
        return result.decode('utf-8')


def main():
    bot_info = BasicActionLLM()
    if os.path.exists('.env'):
        load_dotenv('.env')
    s = bot_info.get_gamedev_tz_info()

if __name__ == "__main__":
    main()