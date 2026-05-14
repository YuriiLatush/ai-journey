from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

pricing = """
VIP Transportation Pricing:
- Airport transfer (sedan): $150
- Airport transfer (SUV): $200  
- Hourly chauffeur (sedan): $100/hr
- Hourly chauffeur (SUV): $150/hr
- Long distance (per mile): $5
"""

system = """You are a luxury VIP transportation concierge assistant.

""" + pricing + """

Your job:
1. Greet the client elegantly
2. Understand their transportation need
3. Classify client as: VIP, Business, or Standard
4. Provide pricing based on their request
5. Always respond in a sophisticated, luxury tone

Never discuss anything outside of transportation services."""

print("VIP Transportation Assistant")
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
    print(f"\nAssistant: {reply}\n")