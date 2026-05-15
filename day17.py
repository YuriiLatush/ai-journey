from openai import OpenAI
import os
from dotenv import load_dotenv
import json
import time
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Логгер — записывает всё что происходит
logs = []

def log(event, data):
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "event": event,
        "data": data
    }
    logs.append(entry)
    print(f"📋 LOG [{entry['time']}] {event}: {str(data)[:60]}")

# Валидатор — проверяет ответ AI
def validate_response(response, required_fields=None):
    if not response:
        return False, "Empty response"
    
    if len(response) < 10:
        return False, "Response too short"
    
    if required_fields:
        try:
            data = json.loads(response)
            for field in required_fields:
                if field not in data:
                    return False, f"Missing field: {field}"
        except:
            return False, "Invalid JSON"
    
    return True, "OK"

# AI с reliability системой
def reliable_ai_call(messages, required_fields=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            log("API_CALL", f"Attempt {attempt + 1}")
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )
            
            reply = response.choices[0].message.content
            log("API_RESPONSE", reply[:60])
            
            # Валидация
            is_valid, reason = validate_response(reply, required_fields)
            
            if is_valid:
                log("VALIDATION", "PASSED")
                return reply
            else:
                log("VALIDATION_FAILED", reason)
                if attempt < max_retries - 1:
                    messages.append({
                        "role": "user",
                        "content": f"Your response was invalid: {reason}. Please try again."
                    })
                    time.sleep(1)
                    
        except Exception as e:
            log("ERROR", str(e))
            if attempt < max_retries - 1:
                time.sleep(2)
    
    return "I apologize, our system encountered an issue. Please try again."

system = """You are a VIP transportation assistant.
When asked for quotes, respond ONLY with JSON:
{
  "service": "airport_sedan or airport_suv or hourly_sedan or hourly_suv",
  "price": number,
  "availability": "available or limited or unavailable"
}
For general questions, respond normally."""

print("Reliability System Demo")
print("=" * 40)
print("Type 'quit' to exit\n")

messages = [{"role": "system", "content": system}]

while True:
    user_input = input("Client: ")
    if user_input.lower() == "quit":
        break
    
    messages.append({"role": "user", "content": user_input})
    
    # Если запрос про цену — требуем JSON
    if any(word in user_input.lower() for word in ["price", "cost", "quote", "how much"]):
        reply = reliable_ai_call(
            messages.copy(),
            required_fields=["service", "price", "availability"]
        )
    else:
        reply = reliable_ai_call(messages.copy())
    
    messages.append({"role": "assistant", "content": reply})
    print(f"\nAssistant: {reply}\n")

print(f"\n📊 Total logs: {len(logs)}")