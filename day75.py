import re
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    route: str        # "price" | "booking" | "general" | ""
    price_step: int   # 0=fresh  1=asked client type  2=asked hours
    client_type: str  # "new" | "vip"
    hours: float
    booking_step: int # 0=fresh  1=date  2=pickup  3=dest  4=name
    booking_data: dict


# ── helpers ──────────────────────────────────────────────────────────────────

def last_human(messages: list) -> str:
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""

def extract_hours(text: str) -> float:
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:hour|hr|h)\b', text.lower())
    if m:
        return float(m.group(1))
    m = re.search(r'\b(\d+(?:\.\d+)?)\b', text)
    return float(m.group(1)) if m else 0.0


# ── nodes ─────────────────────────────────────────────────────────────────────

def router_node(state: State) -> dict:
    msg = last_human(state["messages"]).lower()
    if any(kw in msg for kw in ["price", "cost", "how much", "rate", "charge"]):
        route = "price"
    elif any(kw in msg for kw in ["book", "reserve", "schedule", "ride", "trip"]):
        route = "booking"
    else:
        route = "general"
    return {"route": route}


def price_node(state: State) -> dict:
    step = state.get("price_step", 0)
    msg  = last_human(state["messages"]).lower()

    if step == 0:
        hours = extract_hours(msg)
        return {
            "messages":   [AIMessage("First time with us?")],
            "price_step": 1,
            "hours":      hours,
            "route":      "price",
        }

    if step == 1:
        client_type = "vip" if any(kw in msg for kw in ["vip", "no", "returning", "regular"]) else "new"
        rate  = 115 if client_type == "vip" else 150
        hours = state.get("hours", 0.0)

        if hours:
            total = hours * rate
            h = int(hours) if hours == int(hours) else hours
            return {
                "messages":   [AIMessage(f"{h} hour{'s' if hours != 1 else ''} × ${rate}/hr = ${total:.0f}\n\nWant to book a ride?")],
                "price_step": 0,
                "client_type": client_type,
                "route":      "",
            }
        return {
            "messages":    [AIMessage("How many hours do you need?")],
            "price_step":  2,
            "client_type": client_type,
            "route":       "price",
        }

    # step == 2
    hours       = extract_hours(msg) or 1.0
    client_type = state.get("client_type", "new")
    rate        = 115 if client_type == "vip" else 150
    total       = hours * rate
    h           = int(hours) if hours == int(hours) else hours
    return {
        "messages":   [AIMessage(f"{h} hour{'s' if hours != 1 else ''} × ${rate}/hr = ${total:.0f}\n\nWant to book a ride?")],
        "price_step": 0,
        "route":      "",
    }


def booking_node(state: State) -> dict:
    step    = state.get("booking_step", 0)
    msg     = last_human(state["messages"])
    booking = dict(state.get("booking_data") or {})

    if step == 0:
        return {
            "messages":     [AIMessage("Sure! What date and time works for you?")],
            "booking_step": 1,
            "booking_data": {},
            "route":        "booking",
        }
    if step == 1:
        booking["datetime"] = msg
        return {
            "messages":     [AIMessage("Got it. What's the pickup address?")],
            "booking_step": 2,
            "booking_data": booking,
            "route":        "booking",
        }
    if step == 2:
        booking["pickup"] = msg
        return {
            "messages":     [AIMessage("And the destination?")],
            "booking_step": 3,
            "booking_data": booking,
            "route":        "booking",
        }
    if step == 3:
        booking["destination"] = msg
        return {
            "messages":     [AIMessage("Your name?")],
            "booking_step": 4,
            "booking_data": booking,
            "route":        "booking",
        }

    # step == 4
    booking["name"] = msg
    summary = (
        f"Perfect, {booking['name']}! Here's your booking:\n"
        f"  Date/time:   {booking['datetime']}\n"
        f"  Pickup:      {booking['pickup']}\n"
        f"  Destination: {booking['destination']}\n\n"
        f"I'll send this to Nick. He'll confirm within 15 minutes."
    )
    return {
        "messages":     [AIMessage(summary)],
        "booking_step": 0,
        "booking_data": {},
        "route":        "",
    }


def general_node(state: State) -> dict:
    msg = last_human(state["messages"]).lower()

    if any(kw in msg for kw in ["fleet", "car", "vehicle", "escalade", "suv"]):
        reply = "We run a Cadillac Escalade fleet — spacious, comfortable, and perfect for VIP service."
    elif any(kw in msg for kw in ["airport", "lax", "burbank", "area", "where", "serve", "location"]):
        reply = "We cover all of LA — LAX, Burbank, Long Beach, Van Nuys, city rides, and getaway trips. Available 24/7."
    elif any(kw in msg for kw in ["hour", "available", "24", "open", "time"]):
        reply = "TNavigator is available 24/7. Reach out any time and we'll make it happen."
    else:
        reply = (
            "TNavigator VIP Transportation — premium Cadillac Escalade service across Los Angeles. "
            "Airport transfers, city rides, getaways. Available 24/7.\n\n"
            "Ask about pricing or type 'book' to reserve a ride."
        )

    return {"messages": [AIMessage(reply)], "route": ""}


# ── routing logic ─────────────────────────────────────────────────────────────

def dispatch(state: State) -> str:
    """Skip the router if we're mid-conversation in price or booking."""
    route = state.get("route", "")
    if route == "price"   and state.get("price_step",   0) > 0:
        return "price"
    if route == "booking" and state.get("booking_step", 0) > 0:
        return "booking"
    return "router"

def after_router(state: State) -> str:
    return state["route"]


# ── build graph ───────────────────────────────────────────────────────────────

builder = StateGraph(State)
builder.add_node("router",  router_node)
builder.add_node("price",   price_node)
builder.add_node("booking", booking_node)
builder.add_node("general", general_node)

builder.add_conditional_edges(START, dispatch, {
    "router":  "router",
    "price":   "price",
    "booking": "booking",
})

builder.add_conditional_edges("router", after_router, {
    "price":   "price",
    "booking": "booking",
    "general": "general",
})

builder.add_edge("price",   END)
builder.add_edge("booking", END)
builder.add_edge("general", END)

graph  = builder.compile(checkpointer=MemorySaver())
config = {"configurable": {"thread_id": "session"}}


# ── chat loop ─────────────────────────────────────────────────────────────────

print("TNavigator AI  |  type 'exit' to quit\n" + "-" * 40)

while True:
    try:
        user_input = input("\nYou: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye!")
        break

    if not user_input:
        continue
    if user_input.lower() == "exit":
        print("Goodbye!")
        break

    result = graph.invoke({"messages": [HumanMessage(user_input)]}, config)

    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage):
            print(f"\nTNavigator: {msg.content}")
            break
