from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

MAX_TOKENS = 128000
WARNING_THRESHOLD = 0.8

def count_tokens(messages):
    # Примерный подсчёт: 1 токен ≈ 4 символа
    total_chars = sum(len(m["content"]) for m in messages)
    return total_chars // 4

def check_context(messages):
    used = count_tokens(messages)
    percent = used / MAX_TOKENS
    
    if percent >= WARNING_THRESHOLD:
        print(f"⚠️  WARNING: Context {percent:.0%} full ({used}/{MAX_TOKENS} tokens)")
    else:
        print(f"✓ Context: {percent:.1%} used ({used}/{MAX_TOKENS} tokens)")
    
    return used

def chat(messages, user_input):
    messages.append({"role": "user", "content": user_input})
    check_context(messages)
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    
    reply = response.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})
    return reply

def main():
    print("=== Context Window Monitor ===")
    print(f"Model: gpt-4o-mini | Max tokens: {MAX_TOKENS:,}\n")
    
    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "quit":
            break
        
        reply = chat(messages, user_input)
        print(f"AI: {reply}\n")

if __name__ == "__main__":
    main()