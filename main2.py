from fastapi import FastAPI, Form, Request
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import openai
import os
from openai import OpenAI
app = FastAPI()
from dotenv import load_dotenv
load_dotenv()
# Подключение шаблонов
templates = Jinja2Templates(directory="templates")
origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Set-Cookie", "Access-Control-Allow-Headers", "Access-Control-Allow-Origin", "Authorization"],)
# Инициализация API-ключа OpenAI
openai.api_key = os.getenv('OPENAI_API_KEY')

# Глобальные состояния чата
chat_states = {
    "about_me": "",
    "education": "",
    "professional": "",
    "skills": ""
}

# Переменные для системных сообщений и начальных тем
system_messages = {
    "about_me": "Ты рекрутер. Задавай вопросы о личной информации.",
    "education": "Ты рекрутер. Задавай вопросы об образовании.",
    "professional": "Ты рекрутер. Задавай вопросы о профессиональном опыте.",
    "skills": "Ты рекрутер. Задавай вопросы о навыках."
}

topics = {
    "about_me": "Расскажите о себе.",
    "education": "Расскажите о вашем образовании.",
    "professional": "Расскажите о вашем профессиональном опыте.",
    "skills": "Расскажите о ваших навыках."
}

# Модель для данных чата
class ChatRequest(BaseModel):
    section: str
    user_message: str

# Функция для генерации ответа через OpenAI API
def generate_response(system, topic):
    client = OpenAI()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": topic}
    ]
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
       
    )
    answer = completion.choices[0].message.content
    return answer



@app.get("/", response_class=HTMLResponse)
async def get_chat_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})



@app.post("/chat", response_model=ChatRequest)
async def chat(request: ChatRequest):
    section = request.section
    user_message = request.user_message

    if section in chat_states:
        system_message = system_messages[section]
        topic = topics[section]
        response_message = generate_response(system_message, user_message)
        
        # Сохраняем диалог
        chat_states[section] += f"Клиент: {user_message}\nРекрутер: {response_message}\n"
        
        return JSONResponse({"response_message": response_message, "dialog": chat_states[section]})
    else:
        return JSONResponse({"message": "Неверный раздел"}, status_code=400)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
