from openai import OpenAI
from dotenv import load_dotenv
import json
import os
from datetime import datetime

load_dotenv()
client = OpenAI()

def generate_message(company: str, role: str, context: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """You write cold outreach messages for AI jobs.
Rules:
- 3-4 sentences MAX, no exceptions
- First sentence: specific thing about their product or company
- Second sentence: what you built that is relevant (agents, RAG, voice, LangGraph)
- Third sentence: mention actual tech (WebRTC, LLM routing, latency, vector DB)
- Last sentence: Open to a quick call? Nothing else.
- NO filler words, NO sign-offs, NO placeholders like [Name]
- Write the full message, ready to send"""
            },
            {
                "role": "user",
                "content": f"Company: {company}\nRole: {role}\nContext: {context}\n\nWrite a LinkedIn message."
            }
        ]
    )
    return response.choices[0].message.content

def save_outreach(company: str, role: str, message: str):
    data = []
    if os.path.exists("outreach_log.json"):
        with open("outreach_log.json", "r") as f:
            data = json.load(f)
    
    data.append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "company": company,
        "role": role,
        "message": message,
        "status": "pending"
    })
    
    with open("outreach_log.json", "w") as f:
        json.dump(data, f, indent=2)

def main():
    print("=== Cold Outreach AI Agent ===\n")
    
    company = input("Company name: ")
    role = input("Role: ")
    context = input("What they do (1 sentence): ")
    
    print("\nGenerating message...\n")
    message = generate_message(company, role, context)
    
    print("--- MESSAGE ---")
    print(message)
    print("---------------\n")
    
    save = input("Save to log? (y/n): ")
    if save == "y":
        save_outreach(company, role, message)
        print("Saved to outreach_log.json")

if __name__ == "__main__":
    main()