import psycopg2
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db():
    return psycopg2.connect(DATABASE_URL)

def show_dashboard():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT session_id, intent, 
               jsonb_array_length(messages) as msg_count,
               created_at, updated_at
        FROM conversations
        ORDER BY updated_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    print("\n📊 CONVERSATION DASHBOARD")
    print("=" * 60)
    print(f"{'Session':<30} {'Intent':<10} {'Messages':<10} {'Last Active'}")
    print("-" * 60)
    
    for row in rows:
        session_id, intent, msg_count, created_at, updated_at = row
        print(f"{session_id:<30} {intent:<10} {msg_count:<10} {updated_at.strftime('%Y-%m-%d %H:%M')}")
    
    print(f"\nTotal sessions: {len(rows)}")

def show_session(session_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT messages FROM conversations WHERE session_id = %s", (session_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if not row:
        print(f"Session {session_id} not found")
        return
    
    messages = row[0]
    print(f"\n💬 Session: {session_id}")
    print("=" * 60)
    for msg in messages:
        role = "You" if msg["role"] == "user" else "Bot"
        print(f"{role}: {msg['content'][:100]}...")

def show_stats():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            COUNT(*) as total_sessions,
            SUM(jsonb_array_length(messages)) as total_messages,
            AVG(jsonb_array_length(messages)) as avg_messages,
            MAX(updated_at) as last_activity
        FROM conversations
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    total, total_msgs, avg_msgs, last = row
    print("\n📈 STATS")
    print("=" * 40)
    print(f"Total sessions:   {total}")
    print(f"Total messages:   {total_msgs}")
    print(f"Avg msgs/session: {float(avg_msgs):.1f}")
    print(f"Last activity:    {last.strftime('%Y-%m-%d %H:%M')}")

# Main menu
while True:
    print("\n🚗 Transportation Agent Dashboard")
    print("1. Show all sessions")
    print("2. View session details")
    print("3. Show stats")
    print("4. Exit")
    
    choice = input("\nChoice: ").strip()
    
    if choice == "1":
        show_dashboard()
    elif choice == "2":
        session_id = input("Session ID: ").strip()
        show_session(session_id)
    elif choice == "3":
        show_stats()
    elif choice == "4":
        break