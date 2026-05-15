from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Полный контекстный пакет — context engineering
def build_context(client_data, business_data, examples):
    return f"""
## WHO YOU ARE
{business_data['name']} - {business_data['description']}
Tone: {business_data['tone']}

## BUSINESS RULES
{chr(10).join(business_data['rules'])}

## PRICING
{chr(10).join([f"- {k}: ${v}" for k, v in business_data['pricing'].items()])}

## CLIENT PROFILE
Name: {client_data['name']}
Type: {client_data['type']}
Preferences: {', '.join(client_data['preferences'])}
History: {client_data['history']}

## EXAMPLES OF GOOD RESPONSES
{chr(10).join([f"Q: {e['q']}{chr(10)}A: {e['a']}" for e in examples])}

## YOUR TASK
Help this specific client with their transportation needs.
Use their name. Reference their preferences. Be consistent with examples above.
"""

# Данные бизнеса
business = {
    "name": "Elite Transportation LA",
    "description": "Premium VIP transportation service in Los Angeles",
    "tone": "Elegant, professional, personalized",
    "rules": [
        "Always address VIP clients by last name",
        "Always confirm pickup time and location",
        "Always mention their preferred vehicle",
        "Never discuss competitor services"
    ],
    "pricing": {
        "airport_sedan": 150,
        "airport_suv": 200,
        "hourly_sedan": 100,
        "hourly_suv": 150
    }
}

# Данные клиента
client_profile = {
    "name": "Mr. Anderson",
    "type": "VIP",
    "preferences": ["SUV", "quiet driver", "cold water in car"],
    "history": "12 bookings, always tips 20%, prefers 6am pickups"
}

# Примеры правильных ответов
examples = [
    {
        "q": "I need a car tomorrow",
        "a": "Good evening, Mr. Anderson. I'd be delighted to arrange your preferred SUV for tomorrow. Shall I schedule your usual 6am pickup?"
    },
    {
        "q": "What's the price?",
        "a": "For your preferred SUV service, Mr. Anderson, the airport transfer is $200. As always, your cold water will be ready."
    }
]

# Строим контекст
context = build_context(client_profile, business, examples)

print("Context Engineering Demo")
print("=" * 40)
print(f"Context built: {len(context)} characters\n")

messages = [{"role": "system", "content": context}]

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
    print(f"\nAssistant: {reply}\n")