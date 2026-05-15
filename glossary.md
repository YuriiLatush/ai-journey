An API (Application Programming Interface) is a way for two applications to communicate with each other. An API key is a unique identifier used to authenticate requests and associate them with your account."

print() — это команда которая выводит текст на экран в терминале.

Git is a version control system that tracks changes in your code. A commit is a saved snapshot of your project at a specific point in time. Push sends your commits to a remote repository like GitHub."

"System prompt is a hidden instruction that tells the AI how to behave. User prompt is the message from the user that the AI responds to."

"conversation loop — программа которая продолжает разговор пока пользователь не напишет quit"

".env — файл который хранит секретные ключи локально и не выкладывается на GitHub"

На сегодня хват
"AI Agent is an AI system that can take actions autonomously — searching, creating, saving, sending — not just answering questions."
"RAG (Retrieval Augmented Generation) is a technique where AI searches a knowledge base before answering, giving more accurate and specific responses."
git commit — saves a snapshot locally. git push — uploads commits to GitHub."
"Twilio — SMS API service that allows sending text messages programmatically."
## LLM (Large Language Model)
A large AI model trained on massive text data that can understand and generate human language. Examples: GPT-4, Claude, Gemini. This is what you use every day through OpenAI API.

## NLP (Natural Language Processing)
The broader field of how computers understand human language. LLMs are a modern tool within NLP.

## IBM (International Business Machines)
One of the oldest tech companies, founded 1911. Now focused on cloud and AI. Known for Watson AI platform and professional certifications.

RAG (Retrieval Augmented Generation) — giving AI your own data before a conversation so it answers based on your information, not general knowledge."
"Token — a unit of text (roughly 1 word). OpenAI charges per token used in requests and responses."
"Context window — the maximum amount of text an AI can process in one conversation. If exceeded, AI starts forgetting earlier messages."

"Eval system — automated tests that check if AI responses meet expected criteria. Used to measure reliability and catch failures."

Harness Engineering. - Harness — это оболочка вокруг AI которая контролирует:

Что AI может и не может делать
Как AI получает контекст
Как AI маршрутизирует запросы
Как обрабатываются ошибки

"Harness — a control layer around AI that manages routing, topic filtering, retries, and error handling. Keeps AI within defined boundaries."

Context engineering — это искусство правильно собирать и передавать информацию AI. Не просто system prompt, а полный пакет контекста:

Кто клиент
История разговора
Текущая задача
Ограничения
Примеры правильных ответов

angChain basics.
Простое объяснение:
До сих пор ты писал всё сам — агентов, harness, memory. LangChain это готовая библиотека которая делает это за тебя. Используется в большинстве AI стартапов.
Tool calling — это когда AI может вызывать реальные функции в твоём коде.
Например:

Клиент спрашивает погоду → AI вызывает функцию get_weather()
Клиент хочет забронировать → AI вызывает create_booking()
Клиент спрашивает цену → AI вызывает calculate_price()

AI сам решает какую функцию вызвать и с какими параметрам

Reliability — это система которая:

Проверяет ответы AI перед тем как отправить клиенту
Автоматически исправляет ошибки
Логирует всё что происходит

Прежде чем выпустить AI в продакшн — нужно попытаться его сломать. Это называется adversarial testing — ты специально пишешь плохие запросы чтобы найти проблемы.

"RAG (Retrieval Augmented Generation) — giving AI your own database or documents before a conversation so it answers based on your specific information, not general knowledge."

while True — представь охранник который стоит на посту и постоянно проверяет — пришёл кто-то? Пришёл — обработал. Ушёл — снова ждёт. Бесконечно пока не скажешь "конец смены" (quit).
if/elif/else — это логика выбора. Как светофор:

if красный → стой
elif жёлтый → приготовься
else зелёный → езжай