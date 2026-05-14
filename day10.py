from openai import OpenAI
import os
from dotenv import load_dotenv
import json

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

system = """You are a VIP transportation lead qualifier.

Analyze the client message and respond ONLY with a JSON object, nothing else:

{
  "client_name": "extracted name or Unknown",
  "client_type": "VIP or Business or Standard",
  "service_needed": "airport_suv or airport_sedan or hourly_suv or hourly_sedan",
  "urgency": "high or medium or low",
  "estimated_price": number,
  "follow_up_needed": true or false,
  "notes": "brief note about the client"
}

Pricing rules:
- airport_sedan: 150
- airport_suv: 200
- hourly_sedan: 100 per hour
- hourly_suv: 150 per hour

Return ONLY the JSON, no other text."""

print("Lead Qualifier - Structured Output")
print("=" * 40)

message = input("Client message: ")

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": system},
        {"role": "user", "content": message}
    ]
)

raw = response.choices[0].message.content

try:
    data = json.loads(raw)
    print("\n✅ LEAD QUALIFIED:")
    print(json.dumps(data, indent=2))
    
    print(f"\n📊 SUMMARY:")
    print(f"Client: {data['client_name']} ({data['client_type']})")
    print(f"Service: {data['service_needed']}")
    print(f"Price: ${data['estimated_price']}")
    print(f"Urgency: {data['urgency']}")
    print(f"Follow up: {data['follow_up_needed']}")
    
except:
    print("Error parsing response")
    print(raw)