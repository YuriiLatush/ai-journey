from flask import Flask, render_template_string, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import json
import os
from datetime import datetime

load_dotenv()
client = OpenAI()
app = Flask(__name__)

PROFILE_FILE = "user_profile.json"
LOG_FILE = "outreach_log.json"

def load_profile():
    if os.path.exists(PROFILE_FILE):
        with open(PROFILE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_profile(profile):
    with open(PROFILE_FILE, "w") as f:
        json.dump(profile, f, indent=2)

def load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return []

def save_log(log):
    with open(LOG_FILE, "w") as f:
        json.dump(log, f, indent=2)

def research_company(company, context):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Research this company in 60 words. Be specific: what exactly they build, their tech, one recent development. No fluff."},
            {"role": "user", "content": "Company: " + company + "\nContext: " + context}
        ]
    )
    return response.choices[0].message.content

def generate_email(company, role, research, tone, resume):
    tone_map = {
        "friendly": "conversational and warm",
        "direct": "short and confident, zero fluff",
        "formal": "professional, respectful, still human"
    }
    tone_desc = tone_map.get(tone, "conversational and warm")

    prompt = (
        "You are Yurii Latushkin writing a cold outreach email.\n\n"
        "YOUR BACKGROUND:\n" + resume + "\n\n"
        "COMPANY: " + company + "\n"
        "ROLE: " + role + "\n"
        "RESEARCH: " + research + "\n"
        "TONE: " + tone_desc + "\n\n"
        "Write the email now.\n\n"
        "FORMAT:\n"
        "Subject: [specific to this company, not generic]\n\n"
        "[email body]\n\n"
        "Yurii Latushkin\n\n"
        "STRICT RULES:\n"
        "- Start with Good morning or Good afternoon\n"
        "- 3 short paragraphs only\n"
        "- Paragraph 1: one specific thing about their company from the research\n"
        "- Paragraph 2: who you are and what you built recently, keep it short\n"
        "- Paragraph 3: why this company and what you are looking for\n"
        "- End with: Would love a quick call if you are open to it.\n"
        "- Sign with: Yurii Latushkin\n"
        "- NEVER USE: impressed, excited, passionate, leverage, elevate, aligns with, great match, innovative, thrilled, eager\n"
        "- Sound like a real person wrote this\n"
        "- Body under 120 words"
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def score_chance(company, role, research, resume):
    prompt = (
        "You are a brutally honest recruiter. Rate the realistic chance of getting a response to this cold email.\n\n"
        "PERSON:\n" + resume + "\n\n"
        "COMPANY: " + company + "\n"
        "ROLE: " + role + "\n"
        "RESEARCH: " + research + "\n\n"
        "Be realistic. Consider: background relevance, formal experience, competition.\n"
        "10-25 = long shot, 26-50 = possible, 51-70 = decent, 71-85 = strong match.\n\n"
        "Respond with JSON only, no markdown:\n"
        '{"score": 35, "reason": "one honest sentence"}'
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    text = response.choices[0].message.content.strip()
    try:
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except:
        return {"score": 50, "reason": "Could not evaluate"}

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Outreach Agent</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:#f7f6f3;color:#1a1a1a;min-height:100vh}
.sidebar{position:fixed;left:0;top:0;width:240px;height:100vh;background:#fff;border-right:1px solid #ebe9e4;padding:28px 20px;display:flex;flex-direction:column;z-index:10}
.logo{font-size:16px;font-weight:700;margin-bottom:28px;color:#1a1a1a;display:flex;align-items:center;gap:8px}
.logo-dot{width:8px;height:8px;background:#1a1a1a;border-radius:50%;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.5);opacity:0.6}}
.stat-big{background:#f7f6f3;border-radius:12px;padding:16px;margin-bottom:12px}
.stat-num{font-size:36px;font-weight:700;line-height:1}
.stat-label{font-size:11px;color:#999;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px}
.stat-row{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:20px}
.stat-sm{background:#f7f6f3;border-radius:10px;padding:12px;text-align:center}
.stat-sm-num{font-size:22px;font-weight:700}
.stat-sm-label{font-size:11px;color:#999;margin-top:2px}
.divider{height:1px;background:#ebe9e4;margin:16px 0}
.nav-item{padding:9px 12px;border-radius:8px;cursor:pointer;font-size:13px;color:#666;transition:all 0.15s;display:flex;align-items:center;gap:8px;margin-bottom:2px}
.nav-item:hover{background:#f7f6f3;color:#1a1a1a}
.nav-item.active{background:#1a1a1a;color:#fff}
.main{margin-left:240px;padding:40px 48px;max-width:900px}
.page{display:none;animation:fadeIn 0.25s ease}
.page.active{display:block}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.page-header{margin-bottom:32px}
.page-title{font-size:28px;font-weight:700;margin-bottom:6px}
.page-desc{color:#999;font-size:14px}
.card{background:#fff;border:1px solid #ebe9e4;border-radius:16px;padding:28px;margin-bottom:20px}
.form-row{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}
.field{margin-bottom:16px}
label{display:block;font-size:11px;color:#999;margin-bottom:6px;font-weight:500;text-transform:uppercase;letter-spacing:0.4px}
input,textarea,select{width:100%;background:#faf9f7;border:1px solid #ebe9e4;border-radius:10px;padding:11px 14px;color:#1a1a1a;font-size:14px;outline:none;font-family:'Inter',sans-serif;transition:all 0.15s}
input:focus,textarea:focus{border-color:#1a1a1a;background:#fff}
textarea{resize:vertical;min-height:80px}
.tone-group{display:flex;gap:8px;margin-top:6px}
.tone-btn{padding:8px 18px;border-radius:20px;border:1.5px solid #ebe9e4;background:#fff;font-size:13px;font-weight:500;cursor:pointer;transition:all 0.15s;font-family:'Inter',sans-serif}
.tone-btn.active{background:#1a1a1a;color:#fff;border-color:#1a1a1a}
.btn{display:inline-flex;align-items:center;gap:8px;background:#1a1a1a;color:#fff;border:none;border-radius:10px;padding:12px 22px;font-size:14px;font-weight:600;cursor:pointer;transition:all 0.15s;font-family:'Inter',sans-serif}
.btn:hover{background:#333;transform:translateY(-1px)}
.btn:disabled{opacity:0.35;cursor:not-allowed;transform:none}
.btn-ghost{background:#fff;color:#1a1a1a;border:1.5px solid #ebe9e4}
.btn-ghost:hover{background:#f7f6f3}
.btn-danger{background:#fff;color:#dc2626;border:1.5px solid #fecaca}
.result-tag{display:inline-block;background:#f7f6f3;border-radius:20px;padding:4px 14px;font-size:11px;color:#999;margin-bottom:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px}
.result-box{background:#faf9f7;border:1px solid #ebe9e4;border-radius:12px;padding:20px;font-size:14px;line-height:1.8;white-space:pre-wrap;margin-bottom:16px}
.score-section{border-radius:12px;padding:20px;margin-bottom:20px}
.score-number{font-size:48px;font-weight:700;line-height:1}
.score-label{font-size:12px;color:#999;font-weight:500;margin-top:4px}
.score-track{border-radius:20px;height:8px;overflow:hidden;margin:12px 0}
.score-fill{height:8px;border-radius:20px;transition:width 1.2s cubic-bezier(0.4,0,0.2,1);width:0%}
.score-reason{font-size:13px;color:#777;line-height:1.5}
.loading-overlay{display:none;text-align:center;padding:40px}
.loading-overlay.show{display:block}
.spinner{width:32px;height:32px;border:2.5px solid #e8e6e1;border-top-color:#1a1a1a;border-radius:50%;animation:spin 0.8s linear infinite;margin:0 auto 12px}
@keyframes spin{to{transform:rotate(360deg)}}
.loading-text{font-size:13px;color:#999}
.loading-steps{display:flex;gap:16px;justify-content:center;margin-top:12px;font-size:12px;color:#bbb}
.entry{background:#fff;border:1px solid #ebe9e4;border-radius:12px;padding:16px 20px;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center}
.entry-co{font-size:14px;font-weight:600}
.entry-meta{font-size:12px;color:#aaa;margin-top:3px}
.badge{font-size:11px;padding:4px 12px;border-radius:20px;font-weight:500}
.pending{background:#fef9ec;color:#b45309}
.sent{background:#eff6ff;color:#1d4ed8}
.replied{background:#f0fdf4;color:#15803d}
.profile-saved{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:18px 22px;display:flex;justify-content:space-between;align-items:center}
.email-preview{background:#fff;border:1px solid #ebe9e4;border-radius:12px;padding:24px;font-size:14px;line-height:1.8;white-space:pre-wrap;font-family:'Inter',sans-serif;position:relative}
.email-preview::before{content:'EMAIL PREVIEW';position:absolute;top:-10px;left:16px;background:#fff;padding:0 8px;font-size:10px;color:#bbb;letter-spacing:1px}
.result-section{display:none}
.result-section.show{display:block;animation:fadeIn 0.3s ease}
</style>
</head>
<body>
<div class="sidebar">
  <div class="logo"><div class="logo-dot"></div>Outreach Agent</div>
  <div class="stat-big">
    <div class="stat-num" id="total-count">0</div>
    <div class="stat-label">Emails generated</div>
  </div>
  <div class="stat-row">
    <div class="stat-sm"><div class="stat-sm-num" id="sent-count">0</div><div class="stat-sm-label">Sent</div></div>
    <div class="stat-sm"><div class="stat-sm-num" id="replied-count">0</div><div class="stat-sm-label">Replied</div></div>
  </div>
  <div class="divider"></div>
  <div class="nav-item active" onclick="showPage('generate', this)">✉ Generate</div>
  <div class="nav-item" onclick="showPage('tracker',this)">◎ Tracker</div>
  <div class="nav-item" onclick="showPage('profile',this)">◈ My Profile</div>
</div>

<div class="main">
<div class="page active" id="page-generate">
  <div class="page-header">
    <div class="page-title">Generate email</div>
    <div class="page-desc">Research a company and write a personalized outreach email</div>
  </div>
  <div class="card">
    <div class="form-row">
      <div><label>Company</label><input type="text" id="company" placeholder="Vapi, Perplexity..."></div>
      <div><label>Role</label><input type="text" id="role" placeholder="AI Engineer Intern"></div>
    </div>
    <div class="field"><label>What they do</label><textarea id="context" rows="2" placeholder="One sentence about their product..."></textarea></div>
    <div class="field"><label>Tone</label>
      <div class="tone-group">
        <div class="tone-btn active" onclick="setTone('friendly',this)">Friendly</div>
        <div class="tone-btn" onclick="setTone('direct',this)">Direct</div>
        <div class="tone-btn" onclick="setTone('formal',this)">Formal</div>
      </div>
    </div>
    <button class="btn" onclick="generate()" id="gen-btn">✦ Generate email</button>
  </div>

  <div class="loading-overlay" id="loading">
    <div class="spinner"></div>
    <div class="loading-text">Working on it...</div>
    <div class="loading-steps">
      <span id="step1">◯ Researching</span>
      <span id="step2">◯ Writing</span>
      <span id="step3">◯ Scoring</span>
    </div>
  </div>

  <div class="result-section" id="result-section">
    <div class="card">
      <div class="result-tag">Research</div>
      <div class="result-box" id="research-out" style="color:#777;font-size:13px"></div>

      <div class="score-section" id="score-section">
        <div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:8px">
          <div>
            <div class="score-number" id="score-num">0</div>
            <div class="score-label">Chance of response</div>
          </div>
          <div style="font-size:13px;color:#aaa">%</div>
        </div>
        <div class="score-track" id="score-track"><div class="score-fill" id="score-fill"></div></div>
        <div class="score-reason" id="score-reason"></div>
      </div>

      <div class="result-tag">Email</div>
      <div class="email-preview" id="email-out"></div>

      <div style="display:flex;gap:10px;margin-top:20px">
        <button class="btn" id="copy-btn" onclick="copyEmail()">Copy email</button>
        <button class="btn btn-ghost" onclick="generate()">↻ Regenerate</button>
      </div>
    </div>
  </div>
</div>

<div class="page" id="page-tracker">
  <div class="page-header">
    <div class="page-title">Tracker</div>
    <div class="page-desc">All companies you reached out to</div>
  </div>
  <div id="tracker-list"></div>
</div>

<div class="page" id="page-profile">
  <div class="page-header">
    <div class="page-title">My Profile</div>
    <div class="page-desc">Your background personalizes every email</div>
  </div>
  <div class="card">
    <div id="profile-display"></div>
    <div id="profile-form" style="display:none">
      <div class="field"><label>Your background</label>
        <textarea id="resume-text" rows="12" placeholder="Name, background, what you built, skills, what you are looking for..."></textarea>
      </div>
      <button class="btn" onclick="saveProfile()">Save profile</button>
    </div>
  </div>
</div>
</div>

<script>
let currentTone = 'friendly';

function showPage(name, el) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  el.classList.add('active');
  if (name === 'tracker') loadTracker();
  if (name === 'profile') loadProfile();
}

function setTone(t, el) {
  currentTone = t;
  document.querySelectorAll('.tone-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
}

function getScoreColor(score) {
  if (score <= 25) return { bg: '#fef2f2', fill: '#ef4444', track: '#fecaca' };
  if (score <= 50) return { bg: '#fff7ed', fill: '#f97316', track: '#fed7aa' };
  if (score <= 70) return { bg: '#fefce8', fill: '#eab308', track: '#fef08a' };
  return { bg: '#f0fdf4', fill: '#22c55e', track: '#bbf7d0' };
}

function animateSteps() {
  const steps = ['step1','step2','step3'];
  let i = 0;
  const interval = setInterval(() => {
    if (i < steps.length) {
      document.getElementById(steps[i]).textContent = document.getElementById(steps[i]).textContent.replace('◯','●');
      i++;
    } else clearInterval(interval);
  }, 900);
}

function resetSteps() {
  ['step1','step2','step3'].forEach(s => {
    const el = document.getElementById(s);
    el.textContent = el.textContent.replace('●','◯');
  });
}

async function generate() {
  const company = document.getElementById('company').value.trim();
  const role = document.getElementById('role').value.trim();
  const context = document.getElementById('context').value.trim();
  if (!company || !role || !context) { alert('Please fill in all fields'); return; }

  document.getElementById('gen-btn').disabled = true;
  document.getElementById('loading').classList.add('show');
  document.getElementById('result-section').classList.remove('show');
  resetSteps();
  animateSteps();

  try {
    const res = await fetch('/generate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({company, role, context, tone: currentTone})
    });
    const data = await res.json();

    document.getElementById('research-out').textContent = data.research;
    document.getElementById('email-out').textContent = data.email;
    document.getElementById('score-reason').textContent = data.reason;

    const colors = getScoreColor(data.score);
    const section = document.getElementById('score-section');
    section.style.background = colors.bg;
    document.getElementById('score-fill').style.background = colors.fill;
    document.getElementById('score-track').style.background = colors.track;

    document.getElementById('score-num').textContent = '0';
    document.getElementById('score-fill').style.width = '0%';
    document.getElementById('result-section').classList.add('show');
    document.getElementById('loading').classList.remove('show');
    document.getElementById('gen-btn').disabled = false;

    setTimeout(() => {
      let current = 0;
      const target = data.score;
      const timer = setInterval(() => {
        current = Math.min(current + 2, target);
        document.getElementById('score-num').textContent = Math.round(current);
        document.getElementById('score-fill').style.width = current + '%';
        if (current >= target) clearInterval(timer);
      }, 20);
    }, 400);

    loadCounts();
  } catch(e) {
    document.getElementById('loading').classList.remove('show');
    document.getElementById('gen-btn').disabled = false;
  }
}

function copyEmail() {
  navigator.clipboard.writeText(document.getElementById('email-out').textContent);
  const btn = document.getElementById('copy-btn');
  btn.textContent = '✓ Copied';
  setTimeout(() => { btn.innerHTML = 'Copy email'; }, 2000);
}

async function loadCounts() {
  const res = await fetch('/counts');
  const d = await res.json();
  document.getElementById('total-count').textContent = d.total;
  document.getElementById('sent-count').textContent = d.sent;
  document.getElementById('replied-count').textContent = d.replied;
}

async function loadTracker() {
  const res = await fetch('/tracker');
  const d = await res.json();
  const el = document.getElementById('tracker-list');
  if (!d.entries.length) {
    el.innerHTML = '<p style="color:#aaa;font-size:14px;padding:20px 0">No emails yet.</p>';
    return;
  }
  el.innerHTML = d.entries.map((e, i) => {
    const score = e.score || 0;
    const colors = score <= 25 ? '#ef4444' : score <= 50 ? '#f97316' : score <= 70 ? '#eab308' : '#22c55e';
    return '<div class="entry"><div><div class="entry-co">' + e.company + '</div><div class="entry-meta">' + e.role + ' · ' + e.date + ' · <span style="color:' + colors + ';font-weight:600">' + score + '%</span></div></div><select onchange="updateStatus(' + e.idx + ',this.value)" style="width:100px;font-size:12px;padding:5px 8px;border-radius:8px"><option ' + (e.status==='pending'?'selected':'') + '>pending</option><option ' + (e.status==='sent'?'selected':'') + '>sent</option><option ' + (e.status==='replied'?'selected':'') + '>replied</option></select></div>';
  }).join('');
}

async function updateStatus(idx, status) {
  await fetch('/update_status', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({idx, status})});
  loadCounts();
}

async function loadProfile() {
  const res = await fetch('/profile');
  const d = await res.json();
  const display = document.getElementById('profile-display');
  const form = document.getElementById('profile-form');
  if (d.resume) {
    display.innerHTML = '<div class="profile-saved"><div><div style="font-size:14px;font-weight:600;margin-bottom:4px">Profile saved</div><div style="font-size:12px;color:#888">' + d.resume.substring(0,100) + '...</div></div><div style="display:flex;gap:8px"><button class="btn btn-ghost" onclick="editProfile()" style="padding:8px 14px;font-size:13px">Edit</button><button class="btn btn-danger" onclick="deleteProfile()" style="padding:8px 14px;font-size:13px">Delete</button></div></div>';
    form.style.display = 'none';
  } else {
    display.innerHTML = '<p style="color:#aaa;font-size:14px;margin-bottom:20px">No profile yet. Add your background so emails are personalized.</p>';
    form.style.display = 'block';
  }
}

function editProfile() {
  fetch('/profile').then(r=>r.json()).then(d => {
    document.getElementById('resume-text').value = d.resume || '';
    document.getElementById('profile-display').innerHTML = '';
    document.getElementById('profile-form').style.display = 'block';
  });
}

async function deleteProfile() {
  if (!confirm('Delete your profile?')) return;
  await fetch('/delete_profile', {method:'POST'});
  loadProfile();
}

async function saveProfile() {
  const resume = document.getElementById('resume-text').value.trim();
  if (!resume) return;
  await fetch('/save_profile', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({resume})});
  loadProfile();
}

loadCounts();
</script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    profile = load_profile()
    resume = profile.get('resume', 'Marketing background, building AI systems full time. Built LangGraph agents, RAG systems, PostgreSQL deployments on Railway.')
    research = research_company(data['company'], data['context'])
    email = generate_email(data['company'], data['role'], research, data.get('tone','friendly'), resume)
    chance = score_chance(data['company'], data['role'], research, resume)
    log = load_log()
    log.append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "company": data['company'],
        "role": data['role'],
        "email": email,
        "score": chance.get('score', 50),
        "status": "pending"
    })
    save_log(log)
    return jsonify({"research": research, "email": email, "score": chance.get('score',50), "reason": chance.get('reason','')})

@app.route('/counts')
def counts():
    log = load_log()
    return jsonify({"total": len(log), "sent": len([x for x in log if x.get("status")=="sent"]), "replied": len([x for x in log if x.get("status")=="replied"])})

@app.route('/tracker')
def tracker():
    log = load_log()
    entries = []
    for i, item in enumerate(reversed(log)):
        e = dict(item)
        e['idx'] = len(log) - 1 - i
        entries.append(e)
    return jsonify({"entries": entries})

@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.json
    log = load_log()
    idx = data.get('idx')
    if idx is not None and 0 <= idx < len(log):
        log[idx]['status'] = data['status']
        save_log(log)
    return jsonify({"ok": True})

@app.route('/profile')
def profile():
    return jsonify(load_profile())

@app.route('/save_profile', methods=['POST'])
def save_profile_route():
    data = request.json
    save_profile({"resume": data['resume']})
    return jsonify({"ok": True})

@app.route('/delete_profile', methods=['POST'])
def delete_profile():
    if os.path.exists(PROFILE_FILE):
        os.remove(PROFILE_FILE)
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host="0.0.0.0", port=port)