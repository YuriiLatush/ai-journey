from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

history = []

print("Simple AI Chatbot (type 'quit' to exit)\n")

while True:
    user_input = input("You: ").strip()

    if user_input.lower() == "quit":
        break
    if not user_input:
        continue

    history.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=history
    )

    reply = response.choices[0].message.content
    history.append({"role": "assistant", "content": reply})

    print(f"AI: {reply}\n")

print("Goodbye!")
