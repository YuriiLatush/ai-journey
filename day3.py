from openai import OpenAI

client = OpenAI(api_key="YOUR_API_KEY")

message = "Need move out cleaning tomorrow"

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a professional cleaning service assistant. Reply professionally and helpfully."},
        {"role": "user", "content": message}
    ]
)

print(response.choices[0].message.content)