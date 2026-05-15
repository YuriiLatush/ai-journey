from openai import OpenAI
import os
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================================
# AI BUSINESS OPERATIONS SYSTEM
# Combines: RAG + Agents + Harness + Dashboard
# ============================================

# RAG — база клиентов
CLIENTS_DB = {
    "john smith": {"name": "John Smith", "type": "VIP", "car": "SUV", "bookings": 15},
    "mike johnson": {"name": "Mike Johnson", "type": "Business", "car": "Sedan", "bookings": 4},
}

# Pricing
PRICING = {
    "airport_sedan": 150, "airport_suv": 200,
    "hourly_sedan": 100, "hourly_suv": 150
}

# Dashboard
stats = {"requests": 0, "success": 0, "cost": 0, "tokens": 0}

def update_stats(tokens, cost):
    stats["requests"] += 1
    stats["success"] += 1
    stats["tokens"] += tokens
    stats["cost"] += cost

def show_dashboard():
    print("\n📊 DASHBOARD")
    print(f"Requests: {stats['requests']} | Cost: ${round(stats['cost'], 6)} | Tokens: {stats['tokens']}")

# Tool functions
def get_client(name):
    return CLIENTS_DB.get(name.lower(), None)

def get_price(service, client_type):
    price = PRICING.get(service, 0)
    if client_type == "VIP":
        price = price * 0.9
    return round(price)

def create_booking(name, service, time, location):
    booking_id = datetime.now().strftime("%Y%m%d%H%M%S")
    print(f"\n✅ BOOKING: {name} | {service} | {time} | {location} | ID:{booking_id}\n")
    return booking_id

# AI call with tracking
def ai_call(messages, system_override=None):
    sys = system_override or """You are a VIP transportation concierge.
Always be elegant. Use client name if known.
Pricing: airport sedan $150, airport SUV $200, hourly sedan $100, hourly SUV $150.
VIP clients get 10% discount."""

    all_messages = [{"role": "system", "content": sys}] + messages

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=all_messages
    )

    reply = response.choices[0].message.content
    cost = (response.usage.prompt_tokens * 0.00015 +
            response.usage.completion_tokens * 0.0006) / 1000
    update_stats(response.usage.total_tokens, cost)
    return reply

# Harness — topic check
def is_transport_related(message):
    result = ai_call(
        [{"role": "user", "content": message}],
        system_override="Is this about transportation? Answer YES or NO only."
    )
    return "YES" in result.upper()

# Main agent
def process_request(user_input, history, client_context=""):
    if not is_transport_related(user_input):
        return "I can only assist with transportation services."

    context = f"\nCLIENT CONTEXT: {client_context}\n" if client_context else ""
    messages = history + [{"role": "user", "content": user_input}]

    return ai_call(messages, system_override=f"""You are a VIP transportation concierge.
{context}
Pricing: airport sedan $150, airport SUV $200, hourly sedan $100, hourly SUV $150.
VIP clients get 10% discount. Be elegant and use client name if known.""")

# ============================================
print("🚗 AI Business Operations System")
print("=" * 40)
print("Commands: 'stats', 'quit'")
print("Start with your name for personalization\n")

client_name = input("Your name: ").strip()
client_data = get_client(client_name)

if client_data:
    client_context = f"Name: {client_data['name']}, Type: {client_data['type']}, Preferred car: {client_data['car']}, Past bookings: {client_data['bookings']}"
    print(f"\n✅ Welcome back, {client_data['name']}! ({client_data['type']} client)\n")
else:
    client_context = f"New client: {client_name}"
    print(f"\n👋 Welcome, {client_name}!\n")

history = []

while True:
    user_input = input(f"{client_name}: ").strip()

    if user_input.lower() == "quit":
        break
    if user_input.lower() == "stats":
        show_dashboard()
        continue
    if not user_input:
        continue

    reply = process_request(user_input, history, client_context)
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": reply})

    print(f"\nAssistant: {reply}\n")

show_dashboard()
print("\nThank you for using AI Business Operations System!")