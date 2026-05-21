from openai import OpenAI
from dotenv import load_dotenv
import json
import os
from datetime import datetime

load_dotenv()
client = OpenAI()

MY_PROFILE = """
Name: Yurii Latushkin
Location: Los Angeles, CA
Background: Marketing (Prague) switched to AI full time
Looking for: AI internship or entry-level role at an AI startup

What I built:
- AI sales agent with LangGraph + RAG + PostgreSQL deployed on Railway
- Telegram bot with lead scoring HOT/WARM/COLD running 24/7
- RAG system with ChromaDB hybrid retrieval and reranking
- Multi-agent pipelines with LangGraph
- Cold outreach agent with company research and status tracking

Tech stack: Python, OpenAI, LangGraph, ChromaDB, PostgreSQL, Railway, Telegram Bot API

What I want: hands-on role where I build real AI systems not just demos
"""

SYSTEM_PROMPT = "You write cold outreach messages for AI jobs.\n\nSENDER PROFILE:\n" + MY_PROFILE + "\nRules:\n- 3-4 sentences MAX\n- First sentence: direct observation about their product\n- Second sentence: pick the most relevant project from sender background\n- Third sentence: connect sender experience to their specific problem\n- Last sentence: Open to a quick call? Nothing else.\n- NO filler, NO sign-offs, NO placeholders\n- NEVER use: aligns with, potential fit, I noticed that, impressive\n- Sound human not robotic\n- Ready to send"

def research_company(company, context):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Research the company. Under 100 words. What they build, tech stack, recent focus, why an AI engineer would want to work there."},
            {"role": "user", "content": "Company: " + company + "\nContext: " + context}
        ]
    )
    return response.choices[0].message.content

def generate_message(company, role, research):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Company: " + company + "\nRole: " + role + "\nResearch: " + research + "\n\nWrite a LinkedIn message."}
        ]
    )
    return response.choices[0].message.content

def save_outreach(company, role, research, message):
    data = []
    if os.path.exists("outreach_log.json"):
        with open("outreach_log.json", "r") as f:
            data = json.load(f)
    data.append({"date": datetime.now().strftime("%Y-%m-%d"), "company": company, "role": role, "research": research, "message": message, "status": "pending"})
    with open("outreach_log.json", "w") as f:
        json.dump(data, f, indent=2)

def show_status():
    if not os.path.exists("outreach_log.json"):
        print("No log found.")
        return
    with open("outreach_log.json", "r") as f:
        data = json.load(f)
    print("\n=== Outreach Tracker ===")
    print("Pending: " + str(len([x for x in data if x["status"] == "pending"])))
    print("Sent:    " + str(len([x for x in data if x["status"] == "sent"])))
    print("Replied: " + str(len([x for x in data if x["status"] == "replied"])))
    print("Total:   " + str(len(data)) + "\n")
    for item in data:
        print("[" + item["status"].upper() + "] " + item["company"] + " — " + item["role"] + " (" + item["date"] + ")")

def update_status(company, new_status):
    if not os.path.exists("outreach_log.json"):
        print("No log found.")
        return
    with open("outreach_log.json", "r") as f:
        data = json.load(f)
    for item in data:
        if item["company"].lower() == company.lower():
            item["status"] = new_status
            print("Updated " + company + " to " + new_status)
    with open("outreach_log.json", "w") as f:
        json.dump(data, f, indent=2)

def main():
    print("=== Cold Outreach AI Agent v3 ===")
    print("1. Generate message")
    print("2. Show status")
    print("3. Update status")
    choice = input("\nChoice (1/2/3): ")
    if choice == "1":
        company = input("Company name: ")
        role = input("Role: ")
        context = input("What they do (1 sentence): ")
        print("\nResearching company...")
        research = research_company(company, context)
        print("\n--- RESEARCH ---\n" + research + "\n----------------\n")
        print("Generating message...")
        message = generate_message(company, role, research)
        print("\n--- MESSAGE ---\n" + message + "\n---------------\n")
        save = input("Save to log? (y/n): ")
        if save == "y":
            save_outreach(company, role, research, message)
            print("Saved")
    elif choice == "2":
        show_status()
    elif choice == "3":
        company = input("Company name: ")
        new_status = input("New status (sent/replied/pending): ")
        update_status(company, new_status)

if __name__ == "__main__":
    main()
