from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests

from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import requests
import os
import logging
from dotenv import load_dotenv
import openai
import re
import requests
from openai import OpenAI
# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Установка API ключа
openai.api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI()




app = FastAPI()
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:5500"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Set-Cookie", "Access-Control-Allow-Headers", "Access-Control-Allow-Origin", "Authorization"],)


# Создаем объект для работы с шаблонами
templates = Jinja2Templates(directory="templates")

# Модели для работы с данными
class ChatRequest(BaseModel):
    system: str
    topic: str
    user_message: str

class ChatResponse(BaseModel):
    response_message: str

# Хранение состояния диалога для разных разделов
dialogs = {
    "about_me": {"dialog": "", "answer": ""},
    "education": {"dialog": "", "answer": ""},
    "professional": {"dialog": "", "answer": ""},
    "skills": {"dialog": "", "answer": ""}
}

# Примеры промптов для каждого раздела
system_me = '''
Ты профессиональный рекрутер, который составляет резюме для трудоустройства клиента в IT компанию.
В настоящий момент тебе необходимы данные для составления блока резюме "О себе"
Тебе будут писать клиенты. Твоя задача провести разговор с клиентом так, чтобы он сообщил все данные, необходимые для составления блока резюме "О себе".
Поддерживай с клиентом разговор, удерживай внимание клиента, чтобы клиент дал максимально полную информацию.
У тебя есть следующий список вопросов, которые надо задать, чтобы получить данные для составления резюме.

При диалоге с клиентом задавай вопросы по порядку из этого списка, начиная с первого вопроса.
Каждый раз называй только один вопрос. Клиент не должен знать про список вопросов.
Если клиент не знает, что ответить, переформулируй вопрос. Приведи примеры, какую информацию можно дать на твой вопрос.
Одобряй и благодари клиента за ответы на вопросы и предоставленную информацию....
'''
topic0_me = '''
Вот список вопросов, которые надо задать клиенту. Задавай вопросы по порядку, по одному. Ни в коем случае не перечисляй сразу все вопросы. Называй только один вопрос.
1. Ваше ФИО
2. Номер телефона
3. Город проживания
4. адрес электронной почты.
5. к какому уровню программиста Вы себя относите: Junior, Middle, Senior?
6. в какой области программирования Вы являетесь специалистом, например: искусственный интеллект, frontend-разработчик, Java-разработчик, QA-тестировщик?
7. в какой области программирования вы совершенствуетесь в настоящее время?
8. какое Ваше хобби?

Задавай вопросы из списка вопросов строго по порядку, по одному, начиная с самого первого без ответа. Не пропускай вопросы.

Этот пример не показывай клиенту.

Ни в коем случае в своем ответе не перечисляй все вопросы. Задавай только один вопрос.
После того, как уже был задан последний вопрос из списка вопросов - про хобби - напиши, что информация по блоку "о себе" собрана полностью, вопросов по нему больше нет.
'''
system_educ = '''
Ты профессиональный рекрутер, который составляет резюме для трудоустройства клиента в IT компанию.
В настоящий момент тебе необходимы данные для составления блока резюме "Образование"
Тебе будут писать клиенты. Твоя задача провести разговор с клиентом так, чтобы он сообщил все данные, необходимые для составления блока резюме "Образование".
Поддерживай с клиентом разговор, удерживай внимание клиента, чтобы клиент дал максимально полную информацию.
У тебя есть следующий список вопросов, которые надо задать, чтобы получить данные для составления резюме.

При диалоге с клиентом задавай вопросы по порядку из этого списка, начиная с первого вопроса.
Каждый раз называй только один вопрос. Клиент не должен знать про список вопросов.
Если клиент не знает, что ответить, переформулируй вопрос. Приведи примеры, какую информацию можно дать на твой вопрос.
Одобряй и благодари клиента за ответы на вопросы и предоставленную информацию....
'''
topic0_educ = '''
Вот список вопросов, которые надо задать клиенту. Задавай вопросы по порядку, по одному. Ни в коем случае не перечисляй сразу все вопросы. Называй только один вопрос.
1. год окончания учебного заведения?
2. наименование учебного заведения?
3. специальность - укажите по пунктам специальности, полученные в учебном заведении?
4. дополнительные курсы или сертификаты, которые относятся к IT

Задавай вопросы из списка вопросов строго по порядку, по одному, начиная с самого первого без ответа. Не пропускай вопросы.

Этот пример не показывай клиенту.

Ни в коем случае в своем ответе не перечисляй все вопросы. Задавай только один вопрос.
После того, как уже был задан последний вопрос из списка вопросов - про хобби - напиши, что информация по блоку "о себе" собрана полностью, вопросов по нему больше нет.
'''
system_prof = '''
Ты профессиональный рекрутер, который составляет резюме для трудоустройства клиента в IT компанию.
В настоящий момент тебе необходимы данные для составления блока резюме "Профессиональная деятельность"
Тебе будут писать клиенты. Твоя задача провести разговор с клиентом так, чтобы он сообщил все данные, необходимые для составления блока резюме "Профессиональная деятельность".
Поддерживай с клиентом разговор, удерживай внимание клиента, чтобы клиент дал максимально полную информацию.
У тебя есть следующий список вопросов, которые надо задать, чтобы получить данные для составления резюме.

При диалоге с клиентом задавай вопросы по порядку из этого списка, начиная с первого вопроса.
Каждый раз называй только один вопрос. Клиент не должен знать про список вопросов.
Если клиент не знает, что ответить, переформулируй вопрос. Приведи примеры, какую информацию можно дать на твой вопрос.
Одобряй и благодари клиента за ответы на вопросы и предоставленную информацию.
'''
topic0_prof = '''
Вот список вопросов, которые надо задать клиенту. Задавай вопросы по порядку, по одному. Ни в коем случае не перечисляй сразу все вопросы. Называй только один вопрос.
1. период деятельности
2. наименование компании
3. наименование проекта, в котором участвовал клиент
4. специальность клиента в компании
5. задачи - перечислите по пунктам Ваши задачи
6. достижения - перечислите по пунктам Ваши достижения

После ответа на вопрос про достижения необходимо уточнить у клиента (соискателя), имеются ли другие компании, в которых от работал, если "да", то вопросы нужно повторить сначала.

Задавай вопросы из списка вопросов строго по порядку, по одному, начиная с самого первого без ответа. Не пропускай вопросы.

Этот пример не показывай клиенту.

Ни в коем случае в своем ответе не перечисляй все вопросы. Задавай только один вопрос.
После того, как уже был задан последний вопрос из списка вопросов - про хобби - напиши, что информация по блоку "о себе" собрана полностью, вопросов по нему больше нет.
'''
system_skills = '''
Ты профессиональный рекрутер, который составляет резюме для трудоустройства клиента в IT компанию.
В настоящий момент тебе необходимы данные для составления блока резюме "Навыки".
Тебе будут писать клиенты. Твоя задача провести разговор с клиентом так, чтобы он сообщил все данные, необходимые для составления
блока резюме "Навыки" обязательно укажи в ответе примеры IT навыков: Python, C++, Java, NumPy, Pandas, Matplotlib, Seaborn,
Librosa, Gensim, Pymorphy2, Scikit-learn, SciPy, Keras, Pytorch, Langchain, OpenAI.
'''
topic0_skills = '''
Вот список вопросов, которые надо задать клиенту. Задавай вопросы по порядку, по одному.
1. Какие у вас ключевые профессиональные навыки?
2. Какие у вас есть технические навыки, связанные с IT?
'''



def load_document_text(url: str) -> str:
    match_ = re.search('/document/d/([a-zA-Z0-9-_]+)', url)
    if match_ is None:
        raise ValueError('Invalid Google Docs URL')
    doc_id = match_.group(1)
    response = requests.get(f'https://docs.google.com/document/d/{doc_id}/export?format=txt')
    response.raise_for_status()
    return response.text



def answer_index(system, topic):

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": topic}
    ]
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=messages,
        # temperature=temp
    )
    answer = completion.choices[0].message.content
    return answer  # возвращает ответ




def recruiter_conversation(system, topic, section):
    current_dialog = dialogs[section]
    input_question = topic  # Предполагается, что клиент уже ввел вопрос
    current_dialog["dialog"] += f'Клиент: {input_question} '
    updated_topic = f'{topic} \n\n Предыдущие вопросы из списка: {current_dialog["answer"]} \n\n Ответ клиента: {input_question}'
    answer0 = answer_index(system, updated_topic)
    current_dialog["answer"] += answer0
    current_dialog["dialog"] += f'Рекрутер: {answer0} '
    return answer0



def collect_all_dialogs():
    print("Начнем с раздела 'О себе'.")
    dialog_me = recruiter_conversation(system_me, topic0_me, "about_me")
    
    print("\nТеперь перейдем к разделу 'Образование'.")
    dialog_edu = recruiter_conversation(system_educ, topic0_educ, "education")
    
    print("\nДалее раздел 'Профессиональная деятельность'.")
    dialog_prof = recruiter_conversation(system_prof, topic0_prof, "professional")
    
    print("\nИ наконец, раздел 'Навыки'.")
    dialog_skills = recruiter_conversation(system_skills, topic0_skills, "skills")
    
    return dialog_me, dialog_edu, dialog_prof, dialog_skills





@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    user_message = request.user_message.lower()
    
    if "резюме" in user_message:
        dialog_me, dialog_edu, dialog_prof, dialog_skills = collect_all_dialogs()

        res_me = answer_index(system_me, f'Составь часть резюме "О СЕБЕ" из диалога: \n\n{dialogs["about_me"]["dialog"]}.')
        res_edu = answer_index(system_educ, f'Составь часть резюме "Образование" из диалога: \n\n{dialogs["education"]["dialog"]}.')
        res_prof = answer_index(system_prof, f'Составь часть резюме "Профессиональная деятельность" из диалога: \n\n{dialogs["professional"]["dialog"]}.')
        res_skills = answer_index(system_skills, f'Составь часть резюме "Навыки" из диалога: \n\n{dialogs["skills"]["dialog"]}.')
        
        with open('/parts/res_me.txt', 'w') as file:
            file.write(res_me)
        with open('/parts/res_edu.txt', 'w') as file:
            file.write(res_edu)
        with open('/parts/res_prof.txt', 'w') as file:
            file.write(res_prof)
        with open('/parts/res_skills.txt', 'w') as file:
            file.write(res_skills)

        combined_CV = '\n'.join([res_me, res_edu, res_prof, res_skills])
        
        system = load_document_text('https://docs.google.com/document/d/12fSAEOmhbkLTHrDq84OCI8Myo0HnHQ575yh02lzCNI8/export?format=txt')
        resume_complet_example = load_document_text('https://docs.google.com/document/d/16JAVCymtb0Z7f18qNYksn8sV0bBMc0BQ/export?format=txt')
        
        syst = f"{system} \n\nОбразец правильно составленного резюме: {resume_complet_example}"
        feedback = answer_index(syst, f"Кратко укажи замечания по заполнению этого резюме: {combined_CV}")
        
        return ChatResponse(response_message=feedback)

    elif "создать сопроводительное письмо" in user_message:
        good_instructions = ['/parts/primer2.txt', '/parts/primer4.txt', '/parts/primer6.txt', '/parts/primer8.txt']
        
        def read_text_file(file_path):
            with open(file_path, 'r') as file:
                return file.read()
        
        all_instructions = ''.join(read_text_file(file) + '\n' for file in good_instructions)

        system_generalize = '''
        Ты - копирайтер - эксперт и HR-специалист. Ты отлично структурируешь текст и выделяешь ключевые моменты.
        Возьми на себя роль редактора, которому предоставили тексты нескольких рекомендаций по написанию сопроводительных писем...
        '''
        
        generalized_instructions = answer_index(system_generalize, all_instructions)
        
        file_url = 'https://docs.google.com/document/d/1kszDO4qR_7vM-dBjVXjs5dSnqLJn-m-3rPXTL0YUrFE/export?format=txt'
        response = requests.get(file_url)
        resume = response.text
        
        system_cover_letter = f'''
        Ты - эксперт по написанию сопроводительных писем. Ты получил обобщенные рекомендации по созданию сопроводительных писем и резюме кандидата.
        На основе предоставленных рекомендаций и резюме составь сопроводительное письмо для кандидата...
        '''
        
        cover_letter = answer_index(system_cover_letter, "")
        
        return ChatResponse(response_message=cover_letter)
    
    else:
        return ChatResponse(response_message="Команда не распознана. Попробуйте еще раз.")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)