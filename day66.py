from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

def generate_subject_lines(company, role, context):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Generate 3 cold email subject lines for a job seeker. Must be specific to the company, no generic phrases like 'unlock potential' or 'join us'. Sound like a real person wrote it. Short, max 8 words each. Return as numbered list."},
            {"role": "user", "content": f"Company: {company}\nRole: {role}\nContext: {context}"}
        ]
    )
    return response.choices[0].message.content

def main():
    print("=== Email Subject Line Generator ===\n")
    company = input("Company: ")
    role = input("Role: ")
    context = input("What they do (one sentence): ")
    
    print("\nGenerating subject lines...\n")
    result = generate_subject_lines(company, role, context)
    print(result)

if __name__ == "__main__":
    main()