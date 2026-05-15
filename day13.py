from openai import OpenAI
import os
from dotenv import load_dotenv
import json

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# HARNESS — оболочка которая контролирует всё
class AIHarness:
    def __init__(self):
        self.allowed_topics = ["transportation", "booking", "pricing", "vehicles"]
        self.max_retries = 3
        self.conversation_history = []
        
    def is_on_topic(self, message):
        """Проверяет что клиент спрашивает по теме"""
        check_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Is this message related to transportation services? Answer only YES or NO. Topics: {self.allowed_topics}"},
                {"role": "user", "content": message}
            ]
        )
        return "YES" in check_response.choices[0].message.content.upper()
    
    def get_response(self, message):
        """Получает ответ с retry логикой"""
        self.conversation_history.append({"role": "user", "content": message})
        
        for attempt in range(self.max_retries):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": """You are a VIP transportation assistant.
Pricing: airport sedan $150, airport SUV $200, hourly sedan $100, hourly SUV $150.
Always be elegant and professional."""},
                        *self.conversation_history
                    ]
                )
                reply = response.choices[0].message.content
                self.conversation_history.append({"role": "assistant", "content": reply})
                return reply
                
            except Exception as e:
                if attempt == self.max_retries - 1:
                    return "I apologize, our system is temporarily unavailable. Please try again."
                print(f"Retry {attempt + 1}...")
    
    def process(self, message):
        """Главный метод — контролирует весь поток"""
        # 1. Проверка темы
        if not self.is_on_topic(message):
            return "I can only assist with transportation services. How can I help you with your travel needs?"
        
        # 2. Получить ответ
        return self.get_response(message)

# Запуск
harness = AIHarness()

print("VIP Transportation - AI Harness System")
print("=" * 40)
print("Type 'quit' to exit\n")

while True:
    user_input = input("Client: ")
    if user_input.lower() == "quit":
        break
    
    response = harness.process(user_input)
    print(f"\nAssistant: {response}\n")