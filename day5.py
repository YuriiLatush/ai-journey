from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

pricing = """
Our pricing:
- First cleaning: $300 flat rate
- Regular weekly: $200 per visit
- Deep cleaning: $400 per visit
"""

clean_type = input("Type of service (luxury/standard/urgent): ")

if clean_type == "luxury":
    system = "You are a premium concierge cleaning service assistant. " + pricing + " Only answer questions about cleaning. Respond in an elegant tone."
elif clean_type == "urgent":
    system = "You are an emergency cleaning service assistant. " + pricing + " Only answer questions about cleaning. Respond quickly and efficiently."
else:
    system = "You are a professional cleaning service assistant. " + pricing + " Only answer questions about cleaning. Respond professionally."

print("Chat started. Type 'quit' to exit.\n")

messages = [{"role": "system", "content": system}]

while True:
    user_input = input("You: ")
    if user_input.lower() == "quit":
        break
    messages.append({"role": "user", "content": user_input})
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    reply = response.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})
    print(f"AI: {reply}\n")