from flask import Flask, render_template_string, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import json
import os
from datetime import datetime

load_dotenv()
client = OpenAI()
app = Flask(__name__)

MY_PROFILE = """
Name: Yurii Latushkin
Location: Los Angeles, CA
Background: Marketing switched to AI full time
Looking for: AI internship or entry-level role at an AI startup
Built: AI sales agent LangGraph RAG PostgreSQL, Telegram bot lead scoring, ChromaDB hybrid retrieval, multi-agent pipelines
Tech: Python OpenAI LangGraph ChromaDB PostgreSQL Railway Telegram
"""

def research_company(company, context):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Research the company in under 80 words. What they build, tech stack, recent focus."},
            {"role": "user", "content": "Company: " + company + "\nContext: " + context}
        ]
    )
    return response.choices[0].message.content

def generate_message(company, role, research):
    prompt = "Write a 3 sentence LinkedIn outreach message.\nSender profile:\n" + MY_PROFILE + "\nCompany research:\n" + research + "\nRules: no greeting, no sign-off, no words like aligns excited passion mission contribute innovative. First sentence: one specific fact about their product. Second sentence: one specific thing sender built that relates. Third sentence: Open to a quick call?"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

def save_outreach(company, role, research, message):
    data = []
    if os.path.exists("outreach_log.json"):
        with open("outreach_log.json", "r") as f:
            data = json.load(f)
    data.append({"date": datetime.now().strftime("%Y-%m-%d"), "company": company, "role": role, "research": research, "message": message, "status": "pending"})
    with open("outreach_log.json", "w") as f:
        json.dump(data, f, indent=2)

HTML = """<!DOCTYPE html>
<html>
<head>
<title>Outreach Agent</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, sans-serif; background: #0f0f0f; color: #e0e0e0; min-height: 100vh; padding: 40px 20px; }
.container { max-width: 700px; margin: 0 auto; }
h1 { font-size: 24px; font-weight: 600; margin-bottom: 8px; color: #fff; }
.subtitle { color: #666; font-size: 14px; margin-bottom: 32px; }
.card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 12px; padding: 24px; margin-bottom: 16px; }
label { display: block; font-size: 12px; color: #888; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
input, textarea { width: 100%; background: #111; border: 1px solid #2a2a2a; border-radius: 8px; padding: 12px; color: #e0e0e0; font-size: 14px; outline: none; }
textarea { resize: vertical; min-height: 80px; }
button { width: 100%; background: #fff; color: #000; border: none; border-radius: 8px; padding: 14px; font-size: 14px; font-weight: 600; cursor: pointer; margin-top: 16px; }
button:disabled { opacity: 0.4; cursor: not-allowed; }
.result { display: none; }
.result.show { display: block; }
.box { background: #111; border: 1px solid #2a2a2a; border-radius: 8px; padding: 16px; font-size: 14px; line-height: 1.7; margin-bottom: 12px; }
.tag { display: inline-block; background: #222; border: 1px solid #333; border-radius: 20px; padding: 4px 12px; font-size: 12px; color: #888; margin-bottom: 8px; }
.copy-btn { background: #1a1a1a; color: #e0e0e0; border: 1px solid #2a2a2a; }
.loading { text-align: center; color: #555; font-size: 14px; padding: 20px; display: none; }
.loading.show { display: block; }
.tracker { margin-top: 32px; }
.tracker h2 { font-size: 16px; color: #fff; margin-bottom: 16px; }
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
.stat { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px; padding: 16px; text-align: center; }
.stat-num { font-size: 28px; font-weight: 600; color: #fff; }
.stat-label { font-size: 12px; color: #666; margin-top: 4px; }
.entry { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px; padding: 12px 16px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
.entry-company { font-size: 14px; color: #fff; }
.entry-meta { font-size: 12px; color: #666; }
.badge { font-size: 11px; padding: 3px 10px; border-radius: 20px; font-weight: 500; }
.pending { background: #2a1f00; color: #f59e0b; }
.sent { background: #001a2a; color: #3b82f6; }
.replied { background: #001a0f; color: #10b981; }
</style>
</head>
<body>
<div class="container">
<h1>Outreach Agent</h1>
<p class="subtitle">Generates personalized messages based on your background</p>
<div class="card">
<div style="margin-bottom:16px"><label>Company</label><input type="text" id="company" placeholder="Vapi"></div>
<div style="margin-bottom:16px"><label>Role</label><input type="text" id="role" placeholder="AI Engineer"></div>
<div><label>What they do</label><textarea id="context" placeholder="One sentence about their product..."></textarea></div>
<button onclick="generate()" id="btn">Generate message</button>
</div>
<div class="loading" id="loading">Researching and generating...</div>
<div class="card result" id="result">
<div class="tag">Research</div>
<div class="box" id="research-text" style="color:#888"></div>
<div class="tag">Message</div>
<div class="box" id="message-text"></div>
<button class="copy-btn" onclick="copy()">Copy message</button>
</div>
<div class="tracker">
<h2>Tracker</h2>
<div class="stats">
<div class="stat"><div class="stat-num" id="cp">0</div><div class="stat-label">Pending</div></div>
<div class="stat"><div class="stat-num" id="cs">0</div><div class="stat-label">Sent</div></div>
<div class="stat"><div class="stat-num" id="cr">0</div><div class="stat-label">Replied</div></div>
</div>
<div id="entries"></div>
</div>
</div>
<script>
loadTracker();
async function generate() {
    const company = document.getElementById('company').value;
    const role = document.getElementById('role').value;
    const context = document.getElementById('context').value;
    if (!company || !role || !context) return;
    document.getElementById('btn').disabled = true;
    document.getElementById('loading').classList.add('show');
    document.getElementById('result').classList.remove('show');
    const res = await fetch('/generate', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({company, role, context})});
    const data = await res.json();
    document.getElementById('research-text').innerText = data.research;
    document.getElementById('message-text').innerText = data.message;
    document.getElementById('result').classList.add('show');
    document.getElementById('loading').classList.remove('show');
    document.getElementById('btn').disabled = false;
    loadTracker();
}
async function loadTracker() {
    const res = await fetch('/tracker');
    const data = await res.json();
    document.getElementById('cp').innerText = data.pending;
    document.getElementById('cs').innerText = data.sent;
    document.getElementById('cr').innerText = data.replied;
    document.getElementById('entries').innerHTML = data.entries.map(e =>
        '<div class="entry"><div><div class="entry-company">'+e.company+'</div><div class="entry-meta">'+e.role+' · '+e.date+'</div></div><span class="badge '+e.status+'">'+e.status+'</span></div>'
    ).join('');
}
function copy() {
    navigator.clipboard.writeText(document.getElementById('message-text').innerText);
}
</script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    research = research_company(data['company'], data['context'])
    message = generate_message(data['company'], data['role'], research)
    save_outreach(data['company'], data['role'], research, message)
    return jsonify({"research": research, "message": message})

@app.route('/tracker')
def tracker():
    if not os.path.exists("outreach_log.json"):
        return jsonify({"pending": 0, "sent": 0, "replied": 0, "entries": []})
    with open("outreach_log.json", "r") as f:
        log = json.load(f)
    return jsonify({
        "pending": len([x for x in log if x["status"] == "pending"]),
        "sent": len([x for x in log if x["status"] == "sent"]),
        "replied": len([x for x in log if x["status"] == "replied"]),
        "entries": log[::-1]
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)
