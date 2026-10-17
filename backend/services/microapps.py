"""Bespoke, self-contained interactive micro-applications synthesized for each domain."""
import json
from html import escape
from pathlib import Path

def get_base_styles():
    return """
    :root {
      --bg: #0b1220;
      --surface: #142033;
      --surface-hover: #1a2a44;
      --border: #23354e;
      --cyan: #67e8f9;
      --cyan-glow: rgba(103, 232, 249, 0.25);
      --amber: #fcd34d;
      --red: #f87171;
      --emerald: #34d399;
      --text: #f1f5f9;
      --muted: #94a3b8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 16px;
      font-size: 14px;
    }
    .app-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px;
      margin-bottom: 12px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
      transition: all 0.2s ease;
    }
    .app-card:hover {
      border-color: rgba(103, 232, 249, 0.4);
    }
    .badge {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 3px 8px;
      border-radius: 999px;
    }
    .badge-red { background: rgba(248, 113, 113, 0.2); color: var(--red); border: 1px solid rgba(248, 113, 113, 0.4); }
    .badge-cyan { background: rgba(103, 232, 249, 0.15); color: var(--cyan); border: 1px solid rgba(103, 232, 249, 0.3); }
    .badge-amber { background: rgba(252, 211, 77, 0.2); color: var(--amber); border: 1px solid rgba(252, 211, 77, 0.4); }
    .badge-green { background: rgba(52, 211, 153, 0.2); color: var(--emerald); border: 1px solid rgba(52, 211, 153, 0.4); }
    
    .btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      width: 100%;
      padding: 10px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      border: none;
      cursor: pointer;
      transition: all 0.15s ease;
      background: #087b89;
      color: #fff;
    }
    .btn:hover { background: #0b93a4; box-shadow: 0 0 14px var(--cyan-glow); }
    .btn-red { background: #dc2626; }
    .btn-red:hover { background: #ef4444; }
    .btn-ghost { background: transparent; border: 1px solid var(--border); color: var(--text); }
    .btn-ghost:hover { background: var(--surface-hover); border-color: var(--cyan); }
    
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .metric { text-align: center; padding: 8px; background: rgba(11, 18, 32, 0.6); border-radius: 8px; }
    .metric-val { font-size: 18px; font-weight: 700; color: var(--cyan); font-family: ui-monospace, monospace; }
    .metric-lbl { font-size: 11px; color: var(--muted); }
    
    .check-item {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 8px 10px;
      border-radius: 6px;
      cursor: pointer;
      user-select: none;
      margin-bottom: 4px;
      background: rgba(11, 18, 32, 0.4);
      transition: background 0.15s;
    }
    .check-item:hover { background: var(--surface-hover); }
    .check-item input { accent-color: var(--cyan); width: 16px; height: 16px; margin-top: 2px; }
    .check-item.done span { text-decoration: line-through; opacity: 0.6; }
    
    .slider-box { margin: 10px 0; }
    .slider-box label { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px; color: var(--muted); }
    .slider-box input[type=range] { width: 100%; accent-color: var(--cyan); }
    
    .toast {
      padding: 8px 12px;
      border-radius: 6px;
      background: rgba(103, 232, 249, 0.15);
      border: 1px solid var(--cyan);
      color: var(--cyan);
      font-size: 12px;
      margin-top: 8px;
      text-align: center;
      display: none;
    }
    """

def generate_awareness_app(metadata, rules):
    title = metadata.get("title") or "Monsoon Public Health Advisory"
    speaker = metadata.get("speaker") or "District Health Administration"
    rules_json = json.dumps([r.model_dump() if hasattr(r, "model_dump") else r for r in rules])
    
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    {get_base_styles()}
    .timer-display {{
      font-size: 32px;
      font-weight: 800;
      color: var(--cyan);
      font-family: ui-monospace, monospace;
      text-align: center;
      margin: 8px 0;
      letter-spacing: 2px;
    }}
  </style>
</head>
<body>
  <div class="app-card" style="border-left: 4px solid var(--red);">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
      <span class="badge badge-red">🚨 Active Red Alert</span>
      <span style="font-size:11px; color:var(--muted);">{escape(speaker)}</span>
    </div>
    <h2 style="font-size:16px; margin-bottom:4px;">{escape(title)}</h2>
    <p style="font-size:12px; color:var(--muted);">Verified Public Health Directives · Direct Citizen Action Portal</p>
  </div>

  <div class="app-card">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
      <strong style="font-size:13px; color:var(--cyan);">⏱️ Water-Boiling Safety Timer</strong>
      <span class="badge badge-cyan" id="timerStatus">Ready</span>
    </div>
    <p style="font-size:12px; color:var(--muted); margin-bottom:8px;">Boil river water continuously for 3 minutes before drinking to neutralize pathogens.</p>
    <div class="timer-display" id="timer">03:00</div>
    <div class="grid-2">
      <button class="btn" id="startBtn" onclick="toggleTimer()">▶ Start Timer</button>
      <button class="btn btn-ghost" onclick="resetTimer()">↺ Reset</button>
    </div>
  </div>

  <div class="app-card">
    <strong style="font-size:13px; color:var(--cyan); display:block; margin-bottom:6px;">🧪 Chlorine Solution Dilution Calculator</strong>
    <div class="slider-box">
      <label><span>Water Volume</span><b id="waterVolLabel" style="color:var(--text);">20 Litres</b></label>
      <input type="range" id="waterSlider" min="5" max="100" step="5" value="20" oninput="updateChlorine(this.value)">
    </div>
    <div class="metric" style="background:rgba(103, 232, 249, 0.08); border:1px solid rgba(103, 232, 249, 0.2);">
      <div class="metric-val" id="chlorineResult">4 Drops (0.2 mL)</div>
      <div class="metric-lbl">Recommended 0.5% Chlorine Solution</div>
    </div>
  </div>

  <div class="app-card">
    <strong style="font-size:13px; color:var(--cyan); display:block; margin-bottom:8px;">✅ Citizen Precaution Checklist</strong>
    <div id="checkList">
      <label class="check-item"><input type="checkbox" onchange="toggleCheck(this)"><span>Boil all drinking and cooking water for at least 3 minutes.</span></label>
      <label class="check-item"><input type="checkbox" onchange="toggleCheck(this)"><span>Drain open containers, coolers, and planters every Sunday.</span></label>
      <label class="check-item"><input type="checkbox" onchange="toggleCheck(this)"><span>Escalate body temperature &gt; 101°F immediately to nearest PHC.</span></label>
    </div>
  </div>

  <div class="app-card">
    <strong style="font-size:13px; color:var(--cyan); display:block; margin-bottom:8px;">📞 1-Tap Emergency Actions</strong>
    <div class="grid-2" style="margin-bottom:8px;">
      <a href="tel:104" class="btn" style="text-decoration:none;">📞 Call 104 Helpline</a>
      <a href="tel:108" class="btn btn-red" style="text-decoration:none;">🚑 Call 108 Ambulance</a>
    </div>
    <button class="btn btn-ghost" onclick="findPHC()">📍 Route to Nearest Primary Health Center ↗</button>
    <div id="actionToast" class="toast"></div>
  </div>

  <script>
    let timerSec = 180, timerInterval = null, isRunning = false;
    function updateTimerDisplay() {{
      const m = String(Math.floor(timerSec / 60)).padStart(2, '0');
      const s = String(timerSec % 60).padStart(2, '0');
      document.getElementById('timer').textContent = `${{m}}:${{s}}`;
    }}
    function toggleTimer() {{
      if (isRunning) {{
        clearInterval(timerInterval);
        isRunning = false;
        document.getElementById('startBtn').textContent = '▶ Resume';
        document.getElementById('timerStatus').textContent = 'Paused';
      }} else {{
        isRunning = true;
        document.getElementById('startBtn').textContent = '⏸ Pause';
        document.getElementById('timerStatus').textContent = 'Boiling...';
        timerInterval = setInterval(() => {{
          if (timerSec > 0) {{
            timerSec--;
            updateTimerDisplay();
          }} else {{
            clearInterval(timerInterval);
            isRunning = false;
            document.getElementById('timerStatus').textContent = 'Completed!';
            document.getElementById('startBtn').textContent = '✓ Done';
            showToast('Water boiled safely! Pathogens eliminated.');
          }}
        }}, 1000);
      }}
    }}
    function resetTimer() {{
      clearInterval(timerInterval);
      isRunning = false;
      timerSec = 180;
      updateTimerDisplay();
      document.getElementById('startBtn').textContent = '▶ Start Timer';
      document.getElementById('timerStatus').textContent = 'Ready';
    }}
    function updateChlorine(litres) {{
      document.getElementById('waterVolLabel').textContent = `${{litres}} Litres`;
      const drops = Math.round(litres * 0.2);
      document.getElementById('chlorineResult').textContent = `${{drops}} Drops (${{(litres * 0.01).toFixed(1)}} mL)`;
    }}
    function toggleCheck(el) {{
      el.parentElement.classList.toggle('done', el.checked);
    }}
    function findPHC() {{
      window.open('https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent('primary health center near me'), '_blank');
    }}
    function showToast(msg) {{
      const t = document.getElementById('actionToast');
      t.textContent = msg;
      t.style.display = 'block';
      setTimeout(() => {{ t.style.display = 'none'; }}, 4000);
    }}
  </script>
</body>
</html>"""

def generate_audit_app(metadata, rules):
    asset = metadata.get("asset") or "Bridge Pier 4, Mumbai-Goa Highway"
    inspector = metadata.get("inspector") or "Structural Engineering Auditor"
    
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Structural Audit Dashboard</title>
  <style>
    {get_base_styles()}
    .schematic-box {{
      background: #060b13;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      text-align: center;
      margin: 10px 0;
    }}
    .defect-pin {{
      cursor: pointer;
      transition: transform 0.2s;
    }}
    .defect-pin:hover {{
      transform: scale(1.3);
    }}
  </style>
</head>
<body>
  <div class="app-card" style="border-left: 4px solid var(--amber);">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
      <span class="badge badge-amber">Field Inspection Active</span>
      <span style="font-size:11px; color:var(--muted);">{escape(inspector)}</span>
    </div>
    <h2 style="font-size:16px;">{escape(asset)}</h2>
    <p style="font-size:12px; color:var(--muted);">GPS: 18.5204° N, 73.8567° E · Section 65B Voice Audit Trail</p>
  </div>

  <div class="app-card">
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <strong style="font-size:13px; color:var(--cyan);">🔍 Interactive Pier Defect Schematic</strong>
      <span style="font-size:11px; color:var(--muted);">Tap hotspots to inspect</span>
    </div>
    <div class="schematic-box">
      <svg viewBox="0 0 300 160" width="100%" height="150" xmlns="http://www.w3.org/2000/svg">
        <rect x="20" y="20" width="260" height="20" rx="4" fill="#1e324a" stroke="#3b597c" stroke-width="2"/>
        <text x="150" y="34" fill="#94a3b8" font-size="10" text-anchor="middle">BRIDGE DECK SLAB (COMPLIANT)</text>
        <rect x="80" y="40" width="45" height="90" fill="#182638" stroke="#2a4261" stroke-width="1.5"/>
        <rect x="175" y="40" width="45" height="90" fill="#241b24" stroke="#683434" stroke-width="1.5"/>
        <rect x="40" y="130" width="220" height="18" rx="3" fill="#111c2a" stroke="#22374e"/>
        <!-- Hotspots -->
        <circle id="pin1" class="defect-pin" cx="197" cy="75" r="9" fill="#ef4444" stroke="#fff" stroke-width="2" onclick="showDefect('4mm Vertical Crack', 'CRITICAL: Northern load-bearing pillar has 4mm vertical crack. Immediate 15T restriction recommended.', 'critical')">
          <animate attributeName="r" values="8;11;8" dur="1.8s" repeatCount="indefinite"/>
        </circle>
        <circle id="pin2" class="defect-pin" cx="197" cy="110" r="7" fill="#f59e0b" stroke="#fff" stroke-width="1.5" onclick="showDefect('Concrete Spalling & Rebar', 'MODERATE: Concrete spalling observed with rebar exposure. Corrosion inhibitor required.', 'moderate')"/>
        <circle id="pin3" class="defect-pin" cx="102" cy="85" r="6" fill="#10b981" stroke="#fff" stroke-width="1" onclick="showDefect('South Pillar', 'COMPLIANT: No structural movement or micro-cracking observed.', 'compliant')"/>
      </svg>
    </div>
    <div id="defectDetail" class="metric" style="text-align:left; background:rgba(239, 68, 68, 0.1); border:1px solid rgba(239, 68, 68, 0.3);">
      <div style="font-weight:700; color:var(--red);" id="defectTitle">🔴 CRITICAL: 4mm Vertical Crack</div>
      <div style="font-size:12px; color:var(--text); margin-top:3px;" id="defectDesc">Northern load-bearing pillar. Immediate 15-tonne restriction recommended. Heavy trailers diverted to bypass.</div>
    </div>
  </div>

  <div class="app-card">
    <strong style="font-size:13px; color:var(--cyan); display:block; margin-bottom:8px;">📊 Real-Time Structural Telemetry</strong>
    <div class="grid-2">
      <div class="metric"><div class="metric-val" style="color:var(--red);">4.0 mm</div><div class="metric-lbl">Max Crack Width</div></div>
      <div class="metric"><div class="metric-val" style="color:var(--amber);">15 T</div><div class="metric-lbl">Enforced Load Limit</div></div>
    </div>
  </div>

  <div class="app-card">
    <strong style="font-size:13px; color:var(--cyan); display:block; margin-bottom:8px;">⚡ Work-Order Dispatch Workflow</strong>
    <button class="btn btn-red" id="dispatchBtn" onclick="dispatchTicket()">🚨 Dispatch Emergency Maintenance Ticket</button>
    <div id="ticketToast" class="toast"></div>
  </div>

  <script>
    function showDefect(title, desc, level) {{
      const box = document.getElementById('defectDetail');
      const t = document.getElementById('defectTitle');
      const d = document.getElementById('defectDesc');
      t.textContent = title;
      d.textContent = desc;
      if (level === 'critical') {{
        box.style.borderColor = 'rgba(239, 68, 68, 0.4)';
        box.style.background = 'rgba(239, 68, 68, 0.1)';
        t.style.color = '#ef4444';
      }} else if (level === 'moderate') {{
        box.style.borderColor = 'rgba(245, 158, 11, 0.4)';
        box.style.background = 'rgba(245, 158, 11, 0.1)';
        t.style.color = '#f59e0b';
      }} else {{
        box.style.borderColor = 'rgba(16, 185, 129, 0.4)';
        box.style.background = 'rgba(16, 185, 129, 0.1)';
        t.style.color = '#10b981';
      }}
    }}
    function dispatchTicket() {{
      const b = document.getElementById('dispatchBtn');
      const t = document.getElementById('ticketToast');
      b.disabled = true;
      b.textContent = '⏳ Dispatching Work Order...';
      setTimeout(() => {{
        b.textContent = '✓ Work Order #WRK-9412 Dispatched';
        b.style.background = '#10b981';
        t.textContent = 'Ticket dispatched to Highway Authority Repair Depot. SLA: 24 Hours.';
        t.style.display = 'block';
      }}, 800);
    }}
  </script>
</body>
</html>"""

def generate_deals_app(metadata, rules):
    buyer = metadata.get("buyer") or "Suresh Textiles"
    goods = metadata.get("goods") or "Grade-A Cotton Fabric (5000m)"
    
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>B2B Deal & Milestone Tracker</title>
  <style>
    {get_base_styles()}
    .progress-bar-box {{
      height: 8px;
      background: rgba(255,255,255,0.1);
      border-radius: 4px;
      overflow: hidden;
      margin: 8px 0;
    }}
    .progress-fill {{
      height: 100%;
      background: linear-gradient(90deg, #087b89, var(--cyan));
      width: 25%;
      transition: width 0.3s;
    }}
  </style>
</head>
<body>
  <div class="app-card" style="border-left: 4px solid var(--emerald);">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
      <span class="badge badge-green">Commercial Deal Locked</span>
      <span style="font-size:11px; color:var(--muted);">{escape(buyer)}</span>
    </div>
    <h2 style="font-size:16px;">{escape(goods)}</h2>
    <p style="font-size:12px; color:var(--muted);">5,000m @ ₹120/m · Total Agreed: ₹6,00,000</p>
  </div>

  <div class="app-card">
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <strong style="font-size:13px; color:var(--cyan);">📈 Milestone Progress Tracker</strong>
      <span id="milestoneLabel" style="font-size:12px; color:var(--cyan); font-weight:700;">Stage 1 / 4</span>
    </div>
    <div class="progress-bar-box">
      <div class="progress-fill" id="progressBar"></div>
    </div>
    <div id="milestoneList">
      <label class="check-item done"><input type="checkbox" checked onchange="updateMilestone(1, this)"><span>1. Advance 20% Paid (₹1,20,000)</span></label>
      <label class="check-item"><input type="checkbox" onchange="updateMilestone(2, this)"><span>2. Dispatched 50% (₹3,00,000)</span></label>
      <label class="check-item"><input type="checkbox" onchange="updateMilestone(3, this)"><span>3. Warehouse Quality Inspection Passed</span></label>
      <label class="check-item"><input type="checkbox" onchange="updateMilestone(4, this)"><span>4. Final Balance 30% Released (₹1,80,000)</span></label>
    </div>
  </div>

  <div class="app-card">
    <strong style="font-size:13px; color:var(--cyan); display:block; margin-bottom:8px;">🧮 Shrinkage Penalty & Settlement Calculator</strong>
    <div class="slider-box">
      <label><span>Measured Fabric Shrinkage</span><b id="shrinkageLabel" style="color:var(--text);">3.2% (Under 4% Threshold)</b></label>
      <input type="range" id="shrinkageInput" min="1.0" max="8.0" step="0.1" value="3.2" oninput="calcPenalty(this.value)">
    </div>
    <div class="grid-2">
      <div class="metric"><div class="metric-val" id="penaltyVal" style="color:var(--emerald);">₹0</div><div class="metric-lbl">Agreed Penalty (10%)</div></div>
      <div class="metric"><div class="metric-val" id="netPayable" style="color:var(--cyan);">₹6,00,000</div><div class="metric-lbl">Adjusted Deal Value</div></div>
    </div>
  </div>

  <div class="app-card">
    <strong style="font-size:13px; color:var(--cyan); display:block; margin-bottom:8px;">💳 Secure UPI Milestone Release</strong>
    <button class="btn" onclick="releasePayment()">Authorize Advance Tranche (₹1,20,000) via UPI ↗</button>
    <p style="font-size:11px; color:var(--muted); margin-top:6px; text-align:center;">PIN entry occurs exclusively in external NPCI UPI app.</p>
    <div id="paymentToast" class="toast"></div>
  </div>

  <script>
    function updateMilestone(stage, el) {{
      el.parentElement.classList.toggle('done', el.checked);
      const checks = document.querySelectorAll('#milestoneList input[type=checkbox]');
      let count = 0;
      checks.forEach(c => {{ if (c.checked) count++; }});
      const pct = Math.max(10, (count / 4) * 100);
      document.getElementById('progressBar').style.width = pct + '%';
      document.getElementById('milestoneLabel').textContent = `Stage ${{count}} / 4`;
    }}
    function calcPenalty(val) {{
      const v = parseFloat(val);
      const label = document.getElementById('shrinkageLabel');
      const penaltyEl = document.getElementById('penaltyVal');
      const netEl = document.getElementById('netPayable');
      if (v > 4.0) {{
        label.textContent = `${{v}}% (Exceeds 4.0% Clause - Penalty Applied)`;
        label.style.color = 'var(--red)';
        penaltyEl.textContent = '-₹60,000';
        penaltyEl.style.color = 'var(--red)';
        netEl.textContent = '₹5,40,000';
      }} else {{
        label.textContent = `${{v}}% (Compliant - No Penalty)`;
        label.style.color = 'var(--emerald)';
        penaltyEl.textContent = '₹0';
        penaltyEl.style.color = 'var(--emerald)';
        netEl.textContent = '₹6,00,000';
      }}
    }}
    function releasePayment() {{
      const t = document.getElementById('paymentToast');
      t.textContent = 'UPI deep-link intent triggered. Opening banking application...';
      t.style.display = 'block';
      setTimeout(() => {{ t.style.display = 'none'; }}, 3500);
    }}
  </script>
</body>
</html>"""

def generate_business_app(metadata, rules):
    owner = metadata.get("owner") or "Iron & Steel Operations"
    
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Procurement & Operations Console</title>
  <style>
    {get_base_styles()}
  </style>
</head>
<body>
  <div class="app-card" style="border-left: 4px solid var(--cyan);">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
      <span class="badge badge-cyan">Operations Active</span>
      <span style="font-size:11px; color:var(--muted);">{escape(owner)}</span>
    </div>
    <h2 style="font-size:16px;">Procurement & Inventory Rules</h2>
    <p style="font-size:12px; color:var(--muted);">Automated Scrap Yield & Forex Fluctuation Guardrails</p>
  </div>

  <div class="app-card">
    <strong style="font-size:13px; color:var(--cyan); display:block; margin-bottom:8px;">⚡ Scrap Yield Floor Guardrail</strong>
    <div class="slider-box">
      <label><span>Current Scrap Yield</span><b id="yieldLabel" style="color:var(--emerald);">74% (Safe Floor)</b></label>
      <input type="range" id="yieldInput" min="50" max="95" value="74" oninput="updateYield(this.value)">
    </div>
    <div id="yieldBanner" class="metric" style="background:rgba(52, 211, 153, 0.1); border:1px solid rgba(52, 211, 153, 0.3);">
      <div class="metric-val" id="yieldStatusText" style="color:var(--emerald);">✅ PURCHASES ACTIVE</div>
      <div class="metric-lbl">Floor rule: Stop purchasing if yield &lt; 70%</div>
    </div>
  </div>

  <div class="app-card">
    <strong style="font-size:13px; color:var(--cyan); display:block; margin-bottom:8px;">💵 Forex Spike & Grade-B Hold</strong>
    <div class="grid-2">
      <button class="btn btn-ghost" id="spikeBtn" onclick="toggleForex()">Dollar Normal</button>
      <button class="btn btn-ghost" id="gradeBtn" onclick="toggleGrade()">Grade-B Active</button>
    </div>
    <div id="holdBanner" class="metric" style="margin-top:8px; display:none; background:rgba(248, 113, 113, 0.15); border:1px solid var(--red);">
      <div class="metric-val" style="color:var(--red);">⏸️ 72-HOUR PURCHASE PAUSE</div>
      <div class="metric-lbl">Dollar spiked + Grade-B incoming without confirmed order</div>
    </div>
  </div>

  <div class="app-card">
    <strong style="font-size:13px; color:var(--cyan); display:block; margin-bottom:8px;">📦 Order Pipeline Dispatch</strong>
    <button class="btn" onclick="dispatchOrder()">Create Automated Procurement Ticket</button>
    <div id="orderToast" class="toast"></div>
  </div>

  <script>
    let isSpiked = false, isGradeB = true;
    function updateYield(val) {{
      const v = parseInt(val, 10);
      const l = document.getElementById('yieldLabel');
      const b = document.getElementById('yieldBanner');
      const s = document.getElementById('yieldStatusText');
      if (v < 70) {{
        l.textContent = `${{v}}% (BELOW 70% THRESHOLD)`;
        l.style.color = 'var(--red)';
        b.style.background = 'rgba(248, 113, 113, 0.15)';
        b.style.borderColor = 'var(--red)';
        s.textContent = '⛔ HALT PURCHASING IMMEDIATELY';
        s.style.color = 'var(--red)';
      }} else {{
        l.textContent = `${{v}}% (Safe Floor)`;
        l.style.color = 'var(--emerald)';
        b.style.background = 'rgba(52, 211, 153, 0.1)';
        b.style.borderColor = 'rgba(52, 211, 153, 0.3)';
        s.textContent = '✅ PURCHASES ACTIVE';
        s.style.color = 'var(--emerald)';
      }}
    }}
    function toggleForex() {{
      isSpiked = !isSpiked;
      const b = document.getElementById('spikeBtn');
      b.textContent = isSpiked ? '⚠️ Dollar Spiked' : 'Dollar Normal';
      b.style.borderColor = isSpiked ? 'var(--red)' : 'var(--border)';
      b.style.color = isSpiked ? 'var(--red)' : 'var(--text)';
      checkHold();
    }}
    function toggleGrade() {{
      isGradeB = !isGradeB;
      const b = document.getElementById('gradeBtn');
      b.textContent = isGradeB ? 'Grade-B Active' : 'Grade-A Active';
      checkHold();
    }}
    function checkHold() {{
      const h = document.getElementById('holdBanner');
      h.style.display = (isSpiked && isGradeB) ? 'block' : 'none';
    }}
    function dispatchOrder() {{
      const t = document.getElementById('orderToast');
      t.textContent = 'Procurement ticket #ORD-7192 created and logged.';
      t.style.display = 'block';
      setTimeout(() => {{ t.style.display = 'none'; }}, 3500);
    }}
  </script>
</body>
</html>"""

_REQUIREMENTS_APP = (Path(__file__).resolve().parents[2] / "shared" / "requirements_app.html").read_text(encoding="utf-8")


def requirements_app(title, rules, open_questions=(), labels=None, lang="en"):
    """Deterministic, rule-driven app (shared/requirements_app.html, also used by the frontend).
    Threshold rules become sliders that show when the action fires; nothing is invented."""
    items = []
    for i, r in enumerate(rules):
        r = r.model_dump() if hasattr(r, "model_dump") else dict(r)
        items.append({"req_id": r.get("req_id") or f"FR-{i + 1:02d}", "title": r.get("title", ""), "condition": r.get("condition", ""),
                      "action": r.get("action", ""), "exception": r.get("exception"), "speaker": r.get("speaker"), "acceptance": r.get("acceptance") or [],
                      **({"display": r["display"]} if r.get("display") else {})})
    data = json.dumps({"title": title or "Requirements", "rules": items, "open_questions": list(open_questions),
                       "labels": labels or {}, "lang": lang}, ensure_ascii=False)
    return _REQUIREMENTS_APP.replace("/*__VAANI_DATA__*/null", data.replace("<", r"\u003c"))  # "<" -> \u003c: data can never close the <script>


def get_bespoke_app_html(mode, metadata=None, rules=None, domain=""):
    metadata = metadata or {}
    rules = rules or []
    if mode == "awareness":
        return generate_awareness_app(metadata, rules)
    elif mode == "audit":
        return generate_audit_app(metadata, rules)
    elif mode == "deals":
        return generate_deals_app(metadata, rules)
    else:
        return requirements_app(metadata.get("title"), rules)
