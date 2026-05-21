import psycopg2
import chromadb
import json
import os
from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from openai import OpenAI
from typing import TypedDict, Annotated
import operator
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
DATABASE_URL = os.getenv("DATABASE_URL")

# ChromaDB
chroma = chromadb.PersistentClient(path="./chroma_db_58")

docs = [
    "Airport sedan service costs $150. Available 24/7.",
    "Airport SUV service costs $200. Fits up to 6 passengers.",
    "Hourly sedan rental is $100 per hour. Minimum 2 hours.",
    "Hourly SUV rental is $150 per hour. Great for events.",
    "Night surcharge of 25% applies between 10 PM and 6 AM.",
    "Weekend surcharge of 15% applies on Saturday and Sunday.",
    "VIP clients receive 10% discount on all services.",
    "We serve LAX, BUR, LGB, ONT airports.",
    "Cancellations must be made 2 hours before pickup.",
    "All drivers are licensed, insured, and background checked.",
    "We accept cash, credit cards, and Venmo.",
    "Child seats available on request at no extra charge.",
]

def get_embedding(text):
    return client.embeddings.create(model="text-embedding-3-small", input=text).data[0].embedding

def load_kb():
    collection = chroma.get_or_create_collection("transportation_58")
    if collection.count() == 0:
        print("Loading knowledge base...")
        for i, doc in enumerate(docs):
            collection.add(documents=[doc], embeddings=[get_embedding(doc)], ids=[f"doc_{i}"])
        print(f"Loaded {len(docs)} docs")
    else:
        print(f"KB ready — {collection.count()} docs")
    return collection

def rag_search(collection, query, n=3):
    embedding = get_embedding(query)
    results = collection.query(query_embeddings=[embedding], n_results=n)
    return "\n".join(results["documents"][0])

# PostgreSQL
def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS production_sessions (
            session_id TEXT PRIMARY KEY,
            user_name TEXT DEFAULT 'Unknown',
            messages JSONB DEFAULT '[]',
            intent TEXT DEFAULT '',
            score TEXT DEFAULT 'COLD',
            msg_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def load_session(session_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT messages, intent, score, user_name FROM production_sessions WHERE session_id = %s", (session_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {"messages": row[0], "intent": row[1], "score": row[2], "user_name": row[3]}
    return {"messages": [], "intent": "", "score": "COLD", "user_name": "Unknown"}

def save_session(session_id, data):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO production_sessions (session_id, user_name, messages, intent, score, msg_count, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (session_id) DO UPDATE SET
            messages = EXCLUDED.messages,
            intent = EXCLUDED.intent,
            score = EXCLUDED.score,
            msg_count = EXCLUDED.msg_count,
            updated_at = NOW()
    """, (session_id, data["user_name"], json.dumps(data["messages"]), 
          data["intent"], data["score"], len(data["messages"])))
    conn.commit()
    cur.close()
    conn.close()

def get_score(messages):
    if len(messages) >= 6:
        return "HOT"
    elif len(messages) >= 3:
        return "WARM"
    return "COLD"

# State
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    intent: str
    session_id: str
    user_name: str
    score: str
    collection: object

def classify(state: AgentState):
    last = state["messages"][-1]["content"]
    response = llm.invoke([
        {"role": "system", "content": "Classify intent. Return ONLY: PRICING, BOOKING, CANCEL, or OTHER"},
        {"role": "user", "content": last}
    ])
    return {"intent": response.content.strip()}

def rag_respond(state: AgentState):
    last = state["messages"][-1]["content"]
    context = rag_search(state["collection"], last)
    score = get_score(state["messages"])
    
    response = llm.invoke([
        {"role": "system", "content": f"""You are Elite Transportation LA concierge.
Use ONLY this context:
{context}
Be professional and concise."""},
        *state["messages"]
    ])
    return {
        "messages": [{"role": "assistant", "content": response.content}],
        "score": score
    }

def persist(state: AgentState):
    save_session(state["session_id"], {
        "user_name": state["user_name"],
        "messages": state["messages"],
        "intent": state["intent"],
        "score": state["score"]
    })
    return {}

# Graph
graph = StateGraph(AgentState)
graph.add_node("classify", classify)
graph.add_node("respond", rag_respond)
graph.add_node("persist", persist)
graph.set_entry_point("classify")
graph.add_edge("classify", "respond")
graph.add_edge("respond", "persist")
graph.add_edge("persist", END)
app = graph.compile()

# Init
collection = load_kb()
init_db()

user_name = input("Your name: ").strip() or "User"
session_id = input("Session ID (Enter for new): ").strip()
if not session_id:
    session_id = f"{user_name.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"New session: {session_id}")

session = load_session(session_id)
history = session["messages"]
score = session["score"]

if history:
    print(f"Resumed — {len(history)} messages | Score: {score}")

score_emoji = {"HOT": "🔥", "WARM": "🌤", "COLD": "❄️"}

print(f"\n🚗 Elite Transportation AI — Production v2")
print(f"User: {user_name} | Session: {session_id}")
print("LangGraph + RAG + PostgreSQL + Lead Scoring\n")

while True:
    user_input = input("You: ")
    if user_input.lower() == "quit":
        break
    
    history.append({"role": "user", "content": user_input})
    
    result = app.invoke({
        "messages": history,
        "intent": "",
        "session_id": session_id,
        "user_name": user_name,
        "score": score,
        "collection": collection
    })
    
    reply = result["messages"][-1]["content"]
    score = result["score"]
    history.append({"role": "assistant", "content": reply})
    
    if len(history) > 20:
        history = history[-20:]
    
    print(f"Bot [{result['intent']}] {score_emoji.get(score, '')} {score}: {reply}\n")