from openai import OpenAI
import os
from dotenv import load_dotenv
import json

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Это наша "база данных" клиентов — это и есть RAG
clients_db = {
    "john smith": {
        "name": "John Smith",
        "type": "VIP",
        "total_bookings": 12,
        "preferred_car": "SUV",
        "last_booking": "2026-05-10",
        "notes": "Always tips well, prefers quiet drivers"
    },
    "mike johnson": {
        "name": "Mike Johnson", 
        "type": "Business",
        "total_bookings": 3,
        "preferred_car": "Sedan",
        "last_booking": "2026-04-20",
        "notes": "Usually airport transfers early morning"
    }
}

def find_client(name):
    return clients_db.get(name.lower(), None)

system = """You are a VIP transportation concierge with access to client history.

When you receive client information, use it to personalize your response.
Address VIP clients with extra care and mention their preferences.
For new clients, welcome them warmly."""

print("VIP Transportation - Client Memory System")
print("=" * 40)

client_name = input("Client name: ")
client_data = find_client(client_name)

if client_data:
    context = f"CLIENT FOUND IN DATABASE: {json.dumps(client_data)}"
    print(f"\n✅ Returning client detected: {client_data['type']}\n")
else:
    context = "NEW CLIENT - no history found"
    print(f"\n👋 New client\n")

messages = [
    {"role": "system", "content": system},
    {"role": "system", "content": context}
]

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