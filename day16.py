from openai import OpenAI
import os
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Реальные функции которые AI может вызывать
def get_price(service_type, client_type):
    prices = {
        "airport_sedan": 150,
        "airport_suv": 200,
        "hourly_sedan": 100,
        "hourly_suv": 150
    }
    price = prices.get(service_type, 0)
    if client_type == "VIP":
        price = price * 0.9
    return {"price": price, "currency": "USD"}

def create_booking(client_name, service_type, pickup_time, pickup_location):
    booking_id = datetime.now().strftime("%Y%m%d%H%M%S")
    booking = {
        "booking_id": booking_id,
        "client": client_name,
        "service": service_type,
        "pickup_time": pickup_time,
        "pickup_location": pickup_location,
        "status": "confirmed"
    }
    print(f"\n✅ BOOKING CREATED: {json.dumps(booking, indent=2)}\n")
    return booking

def check_availability(date, service_type):
    return {"available": True, "slots": ["6:00 AM", "10:00 AM", "2:00 PM", "6:00 PM"]}

# Описание инструментов для AI
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_price",
            "description": "Get price for transportation service",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_type": {"type": "string", "enum": ["airport_sedan", "airport_suv", "hourly_sedan", "hourly_suv"]},
                    "client_type": {"type": "string", "enum": ["VIP", "Business", "Standard"]}
                },
                "required": ["service_type", "client_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_booking",
            "description": "Create a booking for transportation",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_name": {"type": "string"},
                    "service_type": {"type": "string"},
                    "pickup_time": {"type": "string"},
                    "pickup_location": {"type": "string"}
                },
                "required": ["client_name", "service_type", "pickup_time", "pickup_location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check available time slots",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "service_type": {"type": "string"}
                },
                "required": ["date", "service_type"]
            }
        }
    }
]

system = """You are a VIP transportation booking assistant.
Use the available tools to get prices, check availability, and create bookings.
Always use tools when clients ask about prices or want to make a booking."""

print("Tool Calling Transportation Agent")
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
        messages=messages,
        tools=tools
    )
    
    message = response.choices[0].message
    
    # Если AI хочет вызвать функцию
    if message.tool_calls:
        messages.append(message)
        
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            
            print(f"🔧 AI calling: {func_name}({func_args})")
            
            if func_name == "get_price":
                result = get_price(**func_args)
            elif func_name == "create_booking":
                result = create_booking(**func_args)
            elif func_name == "check_availability":
                result = check_availability(**func_args)
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })
        
        final_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        reply = final_response.choices[0].message.content
    else:
        reply = message.content
    
    messages.append({"role": "assistant", "content": reply})
    print(f"\nAssistant: {reply}\n")