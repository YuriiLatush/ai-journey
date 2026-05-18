from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from typing import TypedDict, Annotated, List
import operator
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    intent: str
    booking_complete: bool
    collected: dict

def classify_intent(state: AgentState):
    last_message = state["messages"][-1]["content"]
    response = llm.invoke([
        {"role": "system", "content": """Classify intent. Return ONLY one word:
PRICING, BOOKING, CANCEL, CONFIRM, OTHER"""},
        {"role": "user", "content": last_message}
    ])
    return {"intent": response.content.strip()}

def handle_pricing(state: AgentState):
    last_message = state["messages"][-1]["content"]
    response = llm.invoke([
        {"role": "system", "content": """Pricing agent for Elite Transportation LA.
Prices: Airport Sedan $150, Airport SUV $200, Hourly Sedan $100/hr, Hourly SUV $150/hr.
Night +25%, Weekend +15%, VIP -10%. Be concise."""},
        {"role": "user", "content": last_message}
    ])
    return {"messages": [{"role": "assistant", "content": response.content}]}

def handle_booking(state: AgentState):
    collected = state.get("collected", {})
    history = state["messages"]
    
    response = llm.invoke([
        {"role": "system", "content": f"""You are a booking agent. 
Already collected: {collected}
Still need: pickup, destination, date, time, vehicle (if not collected).
Ask for ONE missing piece. If all collected, say BOOKING_COMPLETE and summarize."""},
        *history
    ])
    
    reply = response.content
    complete = "BOOKING_COMPLETE" in reply
    
    return {
        "messages": [{"role": "assistant", "content": reply}],
        "booking_complete": complete
    }

def handle_cancel(state: AgentState):
    return {"messages": [{"role": "assistant", "content": "Cancellations require 2 hours notice. Please provide your booking reference number."}]}

def handle_other(state: AgentState):
    response = llm.invoke([
        {"role": "system", "content": "You are a transportation concierge. Be brief and helpful."},
        *state["messages"]
    ])
    return {"messages": [{"role": "assistant", "content": response.content}]}

def should_continue(state: AgentState):
    if state.get("booking_complete"):
        return END
    return END

def route(state: AgentState):
    intent = state.get("intent", "OTHER")
    routes = {
        "PRICING": "pricing",
        "BOOKING": "booking", 
        "CANCEL": "cancel",
        "CONFIRM": "booking",
    }
    return routes.get(intent, "other")

# Build graph
graph = StateGraph(AgentState)
graph.add_node("classifier", classify_intent)
graph.add_node("pricing", handle_pricing)
graph.add_node("booking", handle_booking)
graph.add_node("cancel", handle_cancel)
graph.add_node("other", handle_other)

graph.set_entry_point("classifier")
graph.add_conditional_edges("classifier", route, {
    "pricing": "pricing",
    "booking": "booking",
    "cancel": "cancel",
    "other": "other"
})

for node in ["pricing", "booking", "cancel", "other"]:
    graph.add_edge(node, END)

app = graph.compile()

# Run with persistent history
print("🚗 LangGraph Agent with Memory")
print("Type 'quit' to exit\n")

history = []

while True:
    user_input = input("You: ")
    if user_input.lower() == "quit":
        break
    
    history.append({"role": "user", "content": user_input})
    
    result = app.invoke({
        "messages": history,
        "intent": "",
        "booking_complete": False,
        "collected": {}
    })
    
    last = result["messages"][-1]["content"]
    history.append({"role": "assistant", "content": last})
    
    print(f"Bot [{result['intent']}]: {last}\n")