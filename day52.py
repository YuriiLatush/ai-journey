from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from typing import TypedDict, Annotated
import operator
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))

# State definition
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    intent: str
    price: float
    confirmed: bool

# Nodes
def classify_intent(state: AgentState):
    last_message = state["messages"][-1]
    response = llm.invoke([
        {"role": "system", "content": """Classify the user intent. Return ONLY one word:
- PRICING (asking about prices)
- BOOKING (wants to book)
- CANCEL (wants to cancel)
- OTHER"""},
        {"role": "user", "content": last_message}
    ])
    return {"intent": response.content.strip()}

def handle_pricing(state: AgentState):
    last_message = state["messages"][-1]
    response = llm.invoke([
        {"role": "system", "content": """You are a pricing agent for Elite Transportation LA.
Prices: Airport Sedan $150, Airport SUV $200, Hourly Sedan $100/hr, Hourly SUV $150/hr.
Night surcharge 25%, Weekend 15%, VIP discount 10%."""},
        {"role": "user", "content": last_message}
    ])
    return {"messages": [f"Pricing Agent: {response.content}"]}

def handle_booking(state: AgentState):
    last_message = state["messages"][-1]
    response = llm.invoke([
        {"role": "system", "content": "You are a booking agent. Collect pickup location, destination, date, time, and vehicle type. Be concise."},
        {"role": "user", "content": last_message}
    ])
    return {"messages": [f"Booking Agent: {response.content}"]}

def handle_cancel(state: AgentState):
    return {"messages": ["Cancel Agent: Cancellations must be made 2 hours before pickup. Please provide your booking reference."]}

def handle_other(state: AgentState):
    response = llm.invoke([
        {"role": "system", "content": "You are a helpful transportation concierge. Be brief."},
        {"role": "user", "content": state["messages"][-1]}
    ])
    return {"messages": [f"General Agent: {response.content}"]}

# Router
def route(state: AgentState):
    intent = state.get("intent", "OTHER")
    if intent == "PRICING":
        return "pricing"
    elif intent == "BOOKING":
        return "booking"
    elif intent == "CANCEL":
        return "cancel"
    else:
        return "other"

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

graph.add_edge("pricing", END)
graph.add_edge("booking", END)
graph.add_edge("cancel", END)
graph.add_edge("other", END)

app = graph.compile()

# Run
print("🚗 LangGraph Transportation Agent")
print("Type 'quit' to exit\n")

while True:
    user_input = input("You: ")
    if user_input.lower() == "quit":
        break
    
    result = app.invoke({
        "messages": [user_input],
        "intent": "",
        "price": 0.0,
        "confirmed": False
    })
    
    last_message = result["messages"][-1]
    print(f"Bot: {last_message}\n")
    print(f"[Intent: {result['intent']}]\n")