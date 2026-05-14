from openai import OpenAI
import os
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Это "инструменты" которые agent может использовать
def save_booking(client_name, service, date, price):
    booking = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S"),
        "client": client_name,
        "service": service,
        "date": date,
        "price": price,
        "status": "confirmed"
    }
    print(f"\n✅ BOOKING SAVED: {json.dumps(booking, indent=2)}\n")
    return booking

def calculate_price(service_type):
    prices = {
        "airport_sedan": 150,
        "airport_suv": 200,
        "hourly_sedan": 100,
        "hourly_suv": 150
    }
    return prices.get(service_type, 0)

# Agent logic
system = """You are a VIP transportation booking agent.

When a client wants to book a service:
1. Collect: client name, service type, date
2. Calculate price
3. Confirm booking details
4. End your message with: BOOKING_READY: name | service | date | price

Available services: airport_sedan, airport_suv, hourly_sedan, hourly_suv"""

print("VIP Transportation Agent")
print("=" * 40)
print("Type 'quit' to exit\n")

messages = [{"role": "system", "content": system}]

while True:
    user_input = input("Client: ")
    if user_input.lower() == "quit":
        break
    
    messages.append({"role": "user", "content": user_input})
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    
    reply = response.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})
    
    print(f"\nAgent: {reply}\n")
    
    # Agent автоматически сохраняет когда готово
    if "BOOKING_READY:" in reply:
        parts = reply.split("BOOKING_READY:")[1].strip().split("|")
        if len(parts) == 4:
            save_booking(
                parts[0].strip(),
                parts[1].strip(), 
                parts[2].strip(),
                parts[3].strip()
            )