import chromadb
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from openai import OpenAI
from typing import TypedDict, Annotated
import operator
import os
import json
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Setup ChromaDB
chroma = chromadb.PersistentClient(path="./chroma_db_54")

docs = [
    "We offer airport sedan service for $150. Available 24/7.",
    "Airport SUV service costs $200. Fits up to 6 passengers.",
    "Hourly sedan rental is $100 per hour. Minimum 2 hours.",
    "Hourly SUV rental is $150 per hour. Great for events.",
    "Night surcharge of 25% applies between 10 PM and 6 AM.",
    "Weekend surcharge of 15% applies on Saturday and Sunday.",
    "VIP clients receive 10% discount on all services.",
    "We serve all major LA airports: LAX, BUR, LGB, ONT.",
    "Cancellations must be made 2 hours before pickup.",
    "All drivers are licensed and insured. Background checked.",
    "We accept cash, credit cards, and Venmo.",
    "Child seats available on request at no extra charge.",
]

def get_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def load_kb():
    collection = chroma.get_or_create_collection("transportation_54")
    if collection.count() == 0:
        print("Loading knowledge base...")
        for i, doc in enumerate(docs):
            collection.add(
                documents=[doc],
                embeddings=[get_embedding(doc)],
                ids=[f"doc_{i}"]
            )
        print(f"Loaded {len(docs)} docs")
    else:
        print(f"KB ready — {collection.count()} docs")
    return collection

def rag_search(collection, query, n=3):
    embedding = get_embedding(query)
    results = collection.query(query_embeddings=[embedding], n_results=n)
    return "\n".join(results["documents"][0])

collection = load_kb()

# State
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    intent: str

# Nodes
def classify(state: AgentState):
    last = state["messages"][-1]["content"]
    response = llm.invoke([
        {"role": "system", "content": "Classify intent. Return ONLY: PRICING, BOOKING, CANCEL, or OTHER"},
        {"role": "user", "content": last}
    ])
    return {"intent": response.content.strip()}

def rag_agent(state: AgentState):
    last = state["messages"][-1]["content"]
    context = rag_search(collection, last)
    
    response = llm.invoke([
        {"role": "system", "content": f"""You are Elite Transportation LA concierge.
Answer ONLY from this context:

{context}

If not in context, say "I don't have that information." Be professional."""},
        *state["messages"]
    ])
    return {"messages": [{"role": "assistant", "content": response.content}]}

def route(state: AgentState):
    intent = state.get("intent", "OTHER")
    if intent in ["PRICING", "BOOKING", "CANCEL"]:
        return "rag"
    return "rag"

# Graph
graph = StateGraph(AgentState)
graph.add_node("classifier", classify)
graph.add_node("rag", rag_agent)
graph.set_entry_point("classifier")
graph.add_conditional_edges("classifier", route, {"rag": "rag"})
graph.add_edge("rag", END)

app = graph.compile()

print("\n🚗 LangGraph + RAG System")
print("Type 'quit' to exit\n")

history = []

while True:
    user_input = input("You: ")
    if user_input.lower() == "quit":
        break
    
    history.append({"role": "user", "content": user_input})
    
    result = app.invoke({
        "messages": history,
        "intent": ""
    })
    
    reply = result["messages"][-1]["content"]
    history.append({"role": "assistant", "content": reply})
    
    print(f"Bot [{result['intent']}]: {reply}\n")