from openai import OpenAI

client = OpenAI(api_key="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")

message = "Need move out cleaning tomorrow"

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a professional cleaning service assistant. Reply professionally and helpfully."},
        {"role": "user", "content": message}
    ]
)

print(response.choices[0].message.content)