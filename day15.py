from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from dotenv import load_dotenv
import os

load_dotenv()

# LangChain версия того что мы делали вручную
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY")
)

system = SystemMessage(content="""You are a VIP transportation concierge.
Pricing: airport sedan $150, airport SUV $200, hourly sedan $100, hourly SUV $150.
Always be elegant and professional.""")

print("LangChain Transportation Assistant")
print("=" * 40)
print("Type 'quit' to exit\n")

history = [system]

while True:
    user_input = input("Client: ")
    if user_input.lower() == "quit":
        break
    
    history.append(HumanMessage(content=user_input))
    
    response = llm.invoke(history)
    
    history.append(AIMessage(content=response.content))
    
    print(f"\nAssistant: {response.content}\n")