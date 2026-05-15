from openai import OpenAI
import os
from dotenv import load_dotenv
import json

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Это наши тестовые случаи — eval система
test_cases = [
    {
        "input": "I need a car to the airport tomorrow",
        "expected_service": "airport_sedan or airport_suv",
        "expected_urgency": "medium or high"
    },
    {
        "input": "I want the most luxurious option available tonight",
        "expected_service": "airport_suv or hourly_suv",
        "expected_urgency": "high"
    },
    {
        "input": "Budget option please, just need to get downtown",
        "expected_service": "hourly_sedan",
        "expected_urgency": "low or medium"
    }
]

system = """Analyze the client request and respond ONLY with JSON:
{
  "service": "airport_sedan or airport_suv or hourly_sedan or hourly_suv",
  "urgency": "high or medium or low",
  "client_type": "VIP or Business or Standard"
}"""

print("AI Eval System")
print("=" * 40)

passed = 0
failed = 0

for i, test in enumerate(test_cases):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": test["input"]}
        ]
    )
    
    raw = response.choices[0].message.content
    
    try:
        result = json.loads(raw)
        
        service_ok = any(s in result["service"] for s in test["expected_service"].split(" or "))
        urgency_ok = any(u in result["urgency"] for u in test["expected_urgency"].split(" or "))
        
        if service_ok and urgency_ok:
            print(f"✅ Test {i+1} PASSED: {test['input'][:40]}")
            passed += 1
        else:
            print(f"❌ Test {i+1} FAILED: {test['input'][:40]}")
            print(f"   Expected: {test['expected_service']} | Got: {result['service']}")
            failed += 1
            
    except:
        print(f"❌ Test {i+1} ERROR: Could not parse response")
        failed += 1

print(f"\n📊 Results: {passed} passed, {failed} failed")
print(f"Success rate: {round(passed/(passed+failed)*100)}%")