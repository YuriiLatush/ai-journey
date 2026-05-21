import psycopg2
import json
import os
from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from typing import TypedDict, Annotated
import operator
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
DATABASE_URL = os.getenv("DATABASE_URL")

# DB setup
def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            session_id TEXT PRIMARY KEY,
            messages JSONB DEFAULT '[]',
            intent TEXT DEFAULT '',
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
    cur.execute("SELECT messages, intent FROM conversations WHERE session_id = %s", (session_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {"messages": row[0], "intent": row[1]}
    return {"messages": [], "intent": ""}

def save_session(session_id, messages, intent):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO conversations (session_id, messages, intent, updated_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (session_id) DO UPDATE SET
            messages = EXCLUDED.messages,
            intent = EXCLUDED.intent,
            updated_at = NOW()
    """, (session_id, json.dumps(messages), intent))
    conn.commit()
    cur.close()
    conn.close()

# State
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    intent: str
    session_id: str

# Nodes
def classify(state: AgentState):
    last = state["messages"][-1]["content"]
    response = llm.invoke([
        {"role": "system", "content": "Classify intent. Return ONLY: PRICING, BOOKING, CANCEL, or OTHER"},
        {"role": "user", "content": last}
    ])
    return {"intent": response.content.strip()}

def respond(state: AgentState):
    intent = state.get("intent", "OTHER")
    
    system_prompts = {
        "PRICING": "You are a pricing agent for Elite Transportation LA. Prices: Sedan $150, SUV $200, Hourly Sedan $100/hr, Hourly SUV $150/hr. Night +25%, Weekend +15%, VIP -10%.",
        "BOOKING": "You are a booking agent. Collect pickup, destination, date, time, vehicle type. Be concise.",
        "CANCEL": "You handle cancellations. Policy: 2 hours before pickup. Ask for booking reference.",
        "OTHER": "You are a helpful transportation concierge for Elite Transportation LA."
    }
    
    system = system_prompts.get(intent, system_prompts["OTHER"])
    
    response = llm.invoke([
        {"role": "system", "content": system},
        *state["messages"]
    ])
    
    return {"messages": [{"role": "assistant", "content": response.content}]}

def save_to_db(state: AgentState):
    save_session(state["session_id"], state["messages"], state["intent"])
    return {}

# Graph
graph = StateGraph(AgentState)
graph.add_node("classifier", classify)
graph.add_node("respond", respond)
graph.add_node("save", save_to_db)

graph.set_entry_point("classifier")
graph.add_edge("classifier", "respond")
graph.add_edge("respond", "save")
graph.add_edge("save", END)

app = graph.compile()

# Main
init_db()

session_id = input("Session ID (press Enter for new): ").strip()
if not session_id:
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"New session: {session_id}")

session = load_session(session_id)
history = session["messages"]

if history:
    print(f"Loaded {len(history)} messages from previous session")

print("\n🚗 Transportation Agent with PostgreSQL Memory")
print(f"Session: {session_id}")
print("Type 'quit' to exit\n")

while True:
    user_input = input("You: ")
    if user_input.lower() == "quit":
        break
    
    history.append({"role": "user", "content": user_input})
    
    result = app.invoke({
        "messages": history,
        "intent": "",
        "session_id": session_id
    })
    
    reply = result["messages"][-1]["content"]
    history.append({"role": "assistant", "content": reply})
    
    if len(history) > 20:
        history = history[-20:]
    
    print(f"Bot [{result['intent']}]: {reply}\n")