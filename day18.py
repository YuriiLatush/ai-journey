from openai import OpenAI
import os
from dotenv import load_dotenv
import json
import time

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Стоимость gpt-4o-mini за 1000 токенов
COST_PER_1K_INPUT = 0.00015
COST_PER_1K_OUTPUT = 0.0006

# Кэш для частых вопросов
cache = {}

total_tokens = 0
total_cost = 0

def calculate_cost(input_tokens, output_tokens):
    cost = (input_tokens / 1000 * COST_PER_1K_INPUT) + \
           (output_tokens / 1000 * COST_PER_1K_OUTPUT)
    return round(cost, 6)

def ai_call(messages, use_cache=True):
    global total_tokens, total_cost
    
    # Проверяем кэш
    last_message = messages[-1]["content"]
    cache_key = last_message.lower().strip()
    
    if use_cache and cache_key in cache:
        print(f"💾 CACHE HIT — saved API call")
        return cache[cache_key], 0, 0
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    
    reply = response.choices[0].message.content
    input_tokens = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens
    cost = calculate_cost(input_tokens, output_tokens)
    
    total_tokens += input_tokens + output_tokens
    total_cost += cost
    
    print(f"💰 Cost: ${cost} | Tokens: {input_tokens}in + {output_tokens}out")
    
    # Сохраняем в кэш
    cache[cache_key] = reply
    
    return reply, input_tokens, output_tokens

system = """You are a VIP transportation assistant.
Pricing: airport sedan $150, airport SUV $200, hourly sedan $100, hourly SUV $150.
Keep responses concise to minimize token usage."""

print("Cost Optimization Demo")
print("=" * 40)
print("Type 'quit' to exit\n")

messages = [{"role": "system", "content": system}]

while True:
    user_input = input("Client: ")
    if user_input.lower() == "quit":
        break
    
    messages.append({"role": "user", "content": user_input})
    reply, _, _ = ai_call(messages)
    messages.append({"role": "assistant", "content": reply})
    
    print(f"\nAssistant: {reply}\n")
    print(f"📊 Session total: ${round(total_cost, 6)} | {total_tokens} tokens\n")

print(f"\n💰 FINAL COST: ${round(total_cost, 4)}")
print(f"📊 TOTAL TOKENS: {total_tokens}")
print(f"💾 CACHE SIZE: {len(cache)} responses saved")