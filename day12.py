from openai import OpenAI
import os
from dotenv import load_dotenv
import json

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def agent(name, system, message):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": message}
        ]
    )
    result = response.choices[0].message.content
    print(f"\n🤖 {name}:\n{result}")
    return result

# Agent 1 — Planner
planner_system = """You are a transportation request analyzer.
Analyze the client request and respond ONLY with JSON:
{
  "service": "airport or hourly",
  "car": "sedan or suv",
  "urgency": "high or medium or low",
  "client_type": "VIP or Business or Standard"
}"""

# Agent 2 — Pricer
pricer_system = """You are a pricing specialist.
Given service details, calculate price and respond ONLY with JSON:
{
  "base_price": number,
  "vip_discount": number,
  "final_price": number,
  "reasoning": "brief explanation"
}

Pricing:
- airport sedan: $150, airport suv: $200
- hourly sedan: $100, hourly suv: $150
- VIP gets 10% discount"""

# Agent 3 — Responder  
responder_system = """You are a luxury transportation concierge.
Given client details and pricing, write a elegant confirmation message."""

print("Multi-Agent Transportation System")
print("=" * 40)

request = input("Client request: ")

# Agent 1 analyzes
print("\n--- Agent 1: Analyzing request ---")
analysis = agent("Planner", planner_system, request)

# Agent 2 calculates price
print("\n--- Agent 2: Calculating price ---")
pricing = agent("Pricer", pricer_system, analysis)

# Agent 3 responds to client
print("\n--- Agent 3: Writing response ---")
context = f"Client request: {request}\nAnalysis: {analysis}\nPricing: {pricing}"
response_text = agent("Responder", responder_system, context)