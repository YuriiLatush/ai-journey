from openai import OpenAI
import os
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Dashboard — отслеживает всё
class AIDashboard:
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_cost = 0
        self.total_tokens = 0
        self.response_times = []
        self.errors = []

    def track_request(self, success, cost=0, tokens=0, response_time=0, error=None):
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
            if error:
                self.errors.append(error)
        self.total_cost += cost
        self.total_tokens += tokens
        self.response_times.append(response_time)

    def show(self):
        avg_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        success_rate = (self.successful_requests / self.total_requests * 100) if self.total_requests else 0
        
        print("\n" + "=" * 40)
        print("📊 AI OPERATIONS DASHBOARD")
        print("=" * 40)
        print(f"✅ Success rate:    {round(success_rate)}%")
        print(f"📨 Total requests:  {self.total_requests}")
        print(f"✅ Successful:      {self.successful_requests}")
        print(f"❌ Failed:          {self.failed_requests}")
        print(f"⚡ Avg response:    {round(avg_time, 2)}s")
        print(f"💰 Total cost:      ${round(self.total_cost, 6)}")
        print(f"📝 Total tokens:    {self.total_tokens}")
        if self.errors:
            print(f"🚨 Last error:      {self.errors[-1]}")
        print("=" * 40 + "\n")

dashboard = AIDashboard()

system = """You are a VIP transportation assistant.
Pricing: airport sedan $150, airport SUV $200, hourly sedan $100, hourly SUV $150."""

print("AI Operations Dashboard Demo")
print("=" * 40)
print("Type 'quit' to exit, 'stats' to see dashboard\n")

messages = [{"role": "system", "content": system}]

while True:
    user_input = input("Client: ")
    
    if user_input.lower() == "quit":
        break
    
    if user_input.lower() == "stats":
        dashboard.show()
        continue
    
    start_time = datetime.now()
    
    try:
        messages.append({"role": "user", "content": user_input})
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        
        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
        
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds()
        
        cost = (response.usage.prompt_tokens / 1000 * 0.00015) + \
               (response.usage.completion_tokens / 1000 * 0.0006)
        
        dashboard.track_request(
            success=True,
            cost=cost,
            tokens=response.usage.total_tokens,
            response_time=response_time
        )
        
        print(f"\nAssistant: {reply}\n")
        
    except Exception as e:
        dashboard.track_request(success=False, error=str(e))
        print(f"\n❌ Error: {e}\n")

dashboard.show()