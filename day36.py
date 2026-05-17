from openai import OpenAI
import os
import json
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Pricing rules
BASE_PRICES = {
    "airport_sedan": 150,
    "airport_suv": 200,
    "hourly_sedan": 100,
    "hourly_suv": 150
}

def calculate_price(service, client_type, hour, day_of_week, hours=1):
    price = BASE_PRICES.get(service, 150)
    
    # Night surcharge (10pm - 6am)
    if hour >= 22 or hour < 6:
        price *= 1.25
        surcharge = "Night surcharge +25%"
    else:
        surcharge = None
    
    # Weekend surcharge
    if day_of_week >= 5:  # Saturday=5, Sunday=6
        price *= 1.15
        weekend = "Weekend surcharge +15%"
    else:
        weekend = None
    
    # Hourly services
    if "hourly" in service:
        price *= hours
    
    # VIP discount
    if client_type == "VIP":
        price *= 0.9
        discount = "VIP discount -10%"
    else:
        discount = None
    
    adjustments = [x for x in [surcharge, weekend, discount] if x]
    
    return {
        "service": service,
        "base_price": BASE_PRICES.get(service, 150),
        "final_price": round(price),
        "adjustments": adjustments,
        "client_type": client_type
    }

def get_quote(customer_request):
    # AI extracts details from request
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """Extract transportation details and return ONLY JSON:
{
  "service": "airport_sedan or airport_suv or hourly_sedan or hourly_suv",
  "client_type": "VIP or Standard",
  "pickup_time": "HH:MM or unknown",
  "hours": 1,
  "details": "brief summary"
}"""},
            {"role": "user", "content": customer_request}
        ]
    )
    
    try:
        details = json.loads(response.choices[0].message.content)
    except:
        details = {"service": "airport_suv", "client_type": "Standard", "pickup_time": "12:00", "hours": 1}
    
    # Parse time
    try:
        hour = int(details.get("pickup_time", "12:00").split(":")[0])
    except:
        hour = 12
    
    now = datetime.now()
    pricing = calculate_price(
        details["service"],
        details["client_type"],
        hour,
        now.weekday(),
        details.get("hours", 1)
    )
    
    # Generate elegant quote
    quote_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a VIP transportation concierge. Present the quote elegantly."},
            {"role": "user", "content": f"Generate a quote for: {json.dumps(pricing)}"}
        ]
    )
    
    return pricing, quote_response.choices[0].message.content

print("🚗 AI Pricing Engine")
print("=" * 40)

while True:
    request = input("\nCustomer request: ")
    if request.lower() == "quit":
        break
    
    pricing, quote = get_quote(request)
    
    print(f"\n💰 PRICING BREAKDOWN:")
    print(f"   Service: {pricing['service']}")
    print(f"   Base price: ${pricing['base_price']}")
    if pricing['adjustments']:
        for adj in pricing['adjustments']:
            print(f"   {adj}")
    print(f"   Final price: ${pricing['final_price']}")
    print(f"\n📝 QUOTE:\n{quote}")