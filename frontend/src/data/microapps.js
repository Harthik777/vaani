import { requirementsApp } from "./requirementsApp.js";
// Bespoke interactive micro-apps synthesized for each domain (client-side / offline synthesis)

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function getBaseStyles() {
  return `
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
    .slider-box input[type="range"] {
      width: 100%;
      accent-color: var(--cyan);
      height: 6px;
      background: var(--border);
      border-radius: 3px;
    }
    
    .status-msg {
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 12px;
      margin-top: 8px;
      display: none;
    }
    .status-msg.show { display: block; animation: fadeIn 0.2s ease; }
    .status-msg.success { background: rgba(52, 211, 153, 0.15); border: 1px solid rgba(52, 211, 153, 0.3); color: var(--emerald); }
    .status-msg.info { background: rgba(103, 232, 249, 0.15); border: 1px solid rgba(103, 232, 249, 0.3); color: var(--cyan); }
    
    @keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
  `;
}

function synthesizeAwarenessApp(meta, rules) {
  const title = meta.title || "Public Health Advisory";
  const speaker = meta.speaker || "Chief Medical Officer";
  const area = meta.area || "District Health Authority";
  const actionsList = rules.map(r => r.action || r.title);
  const checklistHtml = actionsList.map((a, i) => `
    <label class="check-item" id="check-${i}">
      <input type="checkbox" onchange="toggleCheck(${i})">
      <span>${escapeHtml(a)}</span>
    </label>
  `).join("");

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)}</title>
  <style>
    ${getBaseStyles()}
    .banner {
      background: linear-gradient(135deg, rgba(248, 113, 113, 0.25), rgba(220, 38, 38, 0.1));
      border: 1px solid rgba(248, 113, 113, 0.4);
      border-radius: 12px;
      padding: 16px;
      margin-bottom: 12px;
    }
    .timer-display {
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 38px;
      font-weight: 800;
      letter-spacing: 2px;
      color: var(--amber);
      text-shadow: 0 0 16px rgba(252, 211, 77, 0.4);
      text-align: center;
      margin: 8px 0;
    }
    .timer-controls { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  </style>
</head>
<body>
  <div class="banner">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
      <span class="badge badge-red">Active Advisory</span>
      <span style="font-size: 11px; color: var(--muted);">${escapeHtml(area)}</span>
    </div>
    <h2 style="font-size: 16px; font-weight: 700; margin-bottom: 4px;">${escapeHtml(title)}</h2>
    <p style="font-size: 12px; color: var(--muted);">Issued by ${escapeHtml(speaker)}</p>
  </div>

  <div class="app-card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
      <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; color: var(--cyan);">Rolling Boil Sterilization Timer</h3>
      <span class="badge badge-amber" id="timer-status">Idle</span>
    </div>
    <p style="font-size: 12px; color: var(--muted); margin-bottom: 8px;">Maintain vigorous rolling boil for minimum 10 minutes to eliminate pathogen load.</p>
    <div class="timer-display" id="timer">10:00</div>
    <div class="timer-controls">
      <button class="btn" id="start-btn" onclick="startTimer()">Start Timer</button>
      <button class="btn btn-ghost" onclick="resetTimer()">Reset</button>
    </div>
    <div id="boil-alert" class="status-msg success">Sterilization duration reached! Water is safely purified.</div>
  </div>

  <div class="app-card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
      <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; color: var(--cyan);">Chlorine Dilution Dosage</h3>
      <span class="badge badge-cyan" id="dosage-badge">0.5% Solution</span>
    </div>
    <div class="slider-box">
      <label><span>Water Volume</span><strong id="vol-lbl">20 Liters</strong></label>
      <input type="range" id="vol-slider" min="5" max="100" value="20" step="5" oninput="updateDilution(this.value)">
    </div>
    <div class="grid-2">
      <div class="metric">
        <div class="metric-val" id="chlorine-tabs">4</div>
        <div class="metric-lbl">Halazone Tabs</div>
      </div>
      <div class="metric">
        <div class="metric-val" id="standing-time">30m</div>
        <div class="metric-lbl">Contact Time</div>
      </div>
    </div>
  </div>

  <div class="app-card">
    <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; color: var(--cyan); margin-bottom: 8px;">Citizen Action Checklist</h3>
    ${checklistHtml}
    <div style="margin-top: 10px; font-size: 12px; color: var(--muted); text-align: right;" id="progress-lbl">0 of ${actionsList.length} completed</div>
  </div>

  <div class="app-card" style="margin-bottom: 0;">
    <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; color: var(--red); margin-bottom: 10px;">Emergency Hotlines & Care</h3>
    <div class="grid-2" style="margin-bottom: 8px;">
      <a href="tel:104" class="btn" style="text-decoration: none;">Call 104 (Health)</a>
      <a href="tel:108" class="btn btn-red" style="text-decoration: none;">Call 108 (Ambulance)</a>
    </div>
    <a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent("primary health center " + area)}" target="_blank" rel="noreferrer" class="btn btn-ghost" style="text-decoration: none;">Locate Nearest PHC Facility ↗</a>
  </div>

  <script>
    let timeLeft = 600;
    let timerId = null;
    function updateDisplay() {
      const m = Math.floor(timeLeft / 60);
      const s = timeLeft % 60;
      document.getElementById('timer').innerText = (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
    }
    function startTimer() {
      if (timerId) {
        clearInterval(timerId);
        timerId = null;
        document.getElementById('start-btn').innerText = 'Resume';
        document.getElementById('timer-status').innerText = 'Paused';
        document.getElementById('timer-status').className = 'badge badge-amber';
        return;
      }
      document.getElementById('start-btn').innerText = 'Pause';
      document.getElementById('timer-status').innerText = 'Active';
      document.getElementById('timer-status').className = 'badge badge-green';
      timerId = setInterval(() => {
        if (timeLeft > 0) {
          timeLeft--;
          updateDisplay();
        } else {
          clearInterval(timerId);
          timerId = null;
          document.getElementById('start-btn').innerText = 'Completed';
          document.getElementById('timer-status').innerText = 'Done';
          document.getElementById('boil-alert').classList.add('show');
        }
      }, 1000);
    }
    function resetTimer() {
      clearInterval(timerId);
      timerId = null;
      timeLeft = 600;
      updateDisplay();
      document.getElementById('start-btn').innerText = 'Start Timer';
      document.getElementById('timer-status').innerText = 'Idle';
      document.getElementById('timer-status').className = 'badge badge-amber';
      document.getElementById('boil-alert').classList.remove('show');
    }
    function updateDilution(val) {
      document.getElementById('vol-lbl').innerText = val + ' Liters';
      const tabs = Math.round(val / 5);
      document.getElementById('chlorine-tabs').innerText = tabs;
    }
    const total = ${actionsList.length};
    function toggleCheck(i) {
      const item = document.getElementById('check-' + i);
      const checked = item.querySelector('input').checked;
      if (checked) item.classList.add('done'); else item.classList.remove('done');
      const count = document.querySelectorAll('.check-item input:checked').length;
      document.getElementById('progress-lbl').innerText = count + ' of ' + total + ' completed';
    }
  </script>
</body>
</html>`;
}

function synthesizeAuditApp(meta, rules) {
  const asset = meta.asset || "Infrastructure Asset";
  const gps = meta.gps || "19.0760 N, 72.8777 E";
  const inspector = meta.inspector || "Field Engineering Team";

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Engineering Inspection Twin: ${escapeHtml(asset)}</title>
  <style>
    ${getBaseStyles()}
    .schematic-box {
      background: #080d1a;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 12px;
      text-align: center;
      position: relative;
      margin: 10px 0;
    }
    .hotspot {
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .hotspot:hover {
      filter: drop-shadow(0 0 8px rgba(103, 232, 249, 0.8));
    }
    .detail-overlay {
      background: rgba(20, 32, 51, 0.95);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      margin-top: 10px;
      text-align: left;
    }
    .radar-pulse {
      animation: pulse 2s infinite;
    }
    @keyframes pulse {
      0% { opacity: 0.4; }
      50% { opacity: 1; }
      100% { opacity: 0.4; }
    }
  </style>
</head>
<body>
  <div class="app-card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
      <span class="badge badge-amber">Structural Audit</span>
      <span style="font-size: 11px; font-family: monospace; color: var(--muted);">${escapeHtml(gps)}</span>
    </div>
    <h2 style="font-size: 16px; font-weight: 700;">${escapeHtml(asset)}</h2>
    <p style="font-size: 12px; color: var(--muted);">Inspector: ${escapeHtml(inspector)}</p>
  </div>

  <div class="app-card">
    <div style="display: flex; justify-content: space-between; align-items: center;">
      <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; color: var(--cyan);">Pier 4 Structural Twin</h3>
      <span class="badge badge-red" id="defect-badge">2 Defects Detected</span>
    </div>
    <p style="font-size: 12px; color: var(--muted); margin-top: 4px;">Tap hotspots on the pier elevation model to inspect crack depth and rebar corrosion:</p>

    <div class="schematic-box">
      <svg viewBox="0 0 340 220" style="width: 100%; height: auto; max-height: 220px;">
        <!-- Bridge Deck -->
        <rect x="20" y="20" width="300" height="24" rx="3" fill="#1e293b" stroke="#334155" stroke-width="2"/>
        <text x="170" y="36" fill="#94a3b8" font-size="10" font-weight="bold" text-anchor="middle">SUPERSTRUCTURE BEAM</text>
        
        <!-- Pier Column -->
        <rect x="110" y="44" width="120" height="130" fill="#0f172a" stroke="#334155" stroke-width="2"/>
        
        <!-- Water / Ground line -->
        <path d="M10,185 Q90,175 170,185 T330,185 L330,210 L10,210 Z" fill="rgba(8, 123, 137, 0.3)"/>
        <text x="170" y="202" fill="#67e8f9" font-size="9" text-anchor="middle">WATERLINE ELEVATION -2.4M</text>

        <!-- Hotspot 1: Shear Crack (Defect) -->
        <g class="hotspot" onclick="showDefect('crack')">
          <circle cx="140" cy="90" r="14" fill="rgba(248, 113, 113, 0.3)" class="radar-pulse"/>
          <circle cx="140" cy="90" r="6" fill="#f87171"/>
          <!-- Crack line -->
          <path d="M140,82 L138,92 L144,98 L142,104" stroke="#f87171" stroke-width="2" fill="none"/>
          <text x="140" y="74" fill="#f87171" font-size="9" font-weight="bold" text-anchor="middle">4mm CRACK</text>
        </g>

        <!-- Hotspot 2: Spalling & Rebar Exposure -->
        <g class="hotspot" onclick="showDefect('rebar')">
          <circle cx="190" cy="130" r="14" fill="rgba(252, 211, 77, 0.3)" class="radar-pulse"/>
          <circle cx="190" cy="130" r="6" fill="#fcd34d"/>
          <rect x="186" y="125" width="8" height="10" fill="none" stroke="#fcd34d" stroke-dasharray="2,2"/>
          <text x="190" y="154" fill="#fcd34d" font-size="9" font-weight="bold" text-anchor="middle">REBAR EXPOSURE</text>
        </g>

        <!-- Hotspot 3: Sound Core -->
        <g class="hotspot" onclick="showDefect('core')">
          <circle cx="170" cy="100" r="6" fill="#34d399"/>
          <text x="170" y="112" fill="#34d399" font-size="8" text-anchor="middle">CORE SOUND</text>
        </g>
      </svg>
    </div>

    <div class="detail-overlay" id="detail-panel">
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <strong id="det-title" style="color: var(--red);">Critical Shear Defect #1</strong>
        <span class="badge badge-red" id="det-badge">Immediate Remediation</span>
      </div>
      <p id="det-desc" style="font-size: 12px; margin: 6px 0; color: var(--text);">Vertical tension crack measuring 4.2mm width extending 1.1m along eastern face. Exceeds standard 0.3mm tolerance.</p>
      <div class="grid-2">
        <div class="metric">
          <div class="metric-val" id="det-m1">4.2 mm</div>
          <div class="metric-lbl">Aperture</div>
        </div>
        <div class="metric">
          <div class="metric-val" id="det-m2">CRITICAL</div>
          <div class="metric-lbl">Risk Tier</div>
        </div>
      </div>
    </div>
  </div>

  <div class="app-card" style="margin-bottom: 0;">
    <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; color: var(--cyan); margin-bottom: 8px;">Action Dispatch</h3>
    <button class="btn btn-red" id="dispatch-btn" onclick="dispatchTicket()">Dispatch Epoxy Injection Repair Order</button>
    <div id="dispatch-msg" class="status-msg success">Work-order #TKT-PIER4-892 generated & dispatched to PWD Central Division.</div>
  </div>

  <script>
    const defects = {
      crack: {
        title: 'Critical Shear Defect #1',
        badge: 'Immediate Remediation',
        badgeClass: 'badge badge-red',
        desc: 'Vertical crack 4.2mm width extending 1.1m along eastern face. Requires high-pressure epoxy resin injection within 7 days.',
        m1: '4.2 mm',
        m2: 'CRITICAL'
      },
      rebar: {
        title: 'Concrete Spalling & Rebar Corrosion',
        badge: 'Moderate Action',
        badgeClass: 'badge badge-amber',
        desc: 'Surface cover spalled over 450mm x 300mm area with exposed T25 steel reinforcement showing oxidation.',
        m1: '12% Loss',
        m2: 'MODERATE'
      },
      core: {
        title: 'Sound Structural Substrate',
        badge: 'Compliant',
        badgeClass: 'badge badge-green',
        desc: 'Ultrasonic pulse velocity test indicates sound concrete density in central load-bearing core.',
        m1: '4.1 km/s',
        m2: 'OPTIMAL'
      }
    };

    function showDefect(key) {
      const d = defects[key];
      document.getElementById('det-title').innerText = d.title;
      document.getElementById('det-badge').className = d.badgeClass;
      document.getElementById('det-badge').innerText = d.badge;
      document.getElementById('det-desc').innerText = d.desc;
      document.getElementById('det-m1').innerText = d.m1;
      document.getElementById('det-m2').innerText = d.m2;
    }

    function dispatchTicket() {
      const btn = document.getElementById('dispatch-btn');
      btn.disabled = true;
      btn.innerText = 'Dispatched';
      document.getElementById('dispatch-msg').classList.add('show');
    }
  </script>
</body>
</html>`;
}

function synthesizeDealsApp(meta, rules) {
  const buyer = meta.buyer || "Commercial Purchaser";
  const seller = meta.seller || "Authorized Merchant";
  const goods = meta.goods || "High-Grade Cotton Textiles (Lot 200)";
  const value = meta.value || "₹4,50,000";
  const numValue = parseInt(value.replace(/[^0-9]/g, "")) || 450000;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>B2B Deal Execution: ${escapeHtml(goods)}</title>
  <style>
    ${getBaseStyles()}
    .parties-box {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: rgba(11, 18, 32, 0.5);
      border-radius: 8px;
      padding: 10px;
      margin: 8px 0;
    }
    .party-col { flex: 1; }
    .arrow { color: var(--cyan); font-size: 18px; padding: 0 10px; }
    .stepper {
      display: flex;
      justify-content: space-between;
      margin: 14px 0 8px 0;
      position: relative;
    }
    .stepper::before {
      content: '';
      position: absolute;
      top: 14px;
      left: 20px;
      right: 20px;
      height: 2px;
      background: var(--border);
      z-index: 1;
    }
    .step-node {
      position: relative;
      z-index: 2;
      text-align: center;
    }
    .node-circle {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: var(--surface);
      border: 2px solid var(--border);
      color: var(--muted);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: bold;
      margin: 0 auto 4px auto;
      transition: all 0.2s;
    }
    .step-node.active .node-circle {
      border-color: var(--cyan);
      background: #087b89;
      color: #fff;
      box-shadow: 0 0 10px var(--cyan-glow);
    }
    .step-node.done .node-circle {
      border-color: var(--emerald);
      background: rgba(52, 211, 153, 0.2);
      color: var(--emerald);
    }
    .node-label { font-size: 10px; color: var(--muted); max-width: 60px; }
  </style>
</head>
<body>
  <div class="app-card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
      <span class="badge badge-cyan">Commercial MoU Contract</span>
      <span style="font-size: 12px; font-weight: bold; color: var(--emerald);">${escapeHtml(value)}</span>
    </div>
    <h2 style="font-size: 15px; font-weight: 700;">${escapeHtml(goods)}</h2>
    
    <div class="parties-box">
      <div class="party-col">
        <span style="font-size: 10px; color: var(--muted); text-transform: uppercase;">Seller</span>
        <div style="font-weight: 600;">${escapeHtml(seller)}</div>
      </div>
      <div class="arrow">⇄</div>
      <div class="party-col" style="text-align: right;">
        <span style="font-size: 10px; color: var(--muted); text-transform: uppercase;">Buyer</span>
        <div style="font-weight: 600;">${escapeHtml(buyer)}</div>
      </div>
    </div>
  </div>

  <div class="app-card">
    <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; color: var(--cyan);">Milestone Fulfillment Flow</h3>
    <div class="stepper">
      <div class="step-node done" id="sn-0">
        <div class="node-circle">✓</div>
        <div class="node-label">Signed</div>
      </div>
      <div class="step-node active" id="sn-1">
        <div class="node-circle">2</div>
        <div class="node-label">Dispatch</div>
      </div>
      <div class="step-node" id="sn-2">
        <div class="node-circle">3</div>
        <div class="node-label">Lab QA</div>
      </div>
      <div class="step-node" id="sn-3">
        <div class="node-circle">4</div>
        <div class="node-label">Final UPI</div>
      </div>
    </div>
    <button class="btn btn-ghost" id="next-step-btn" onclick="advanceStep()" style="margin-top: 6px;">Advance to Lab Quality Check →</button>
  </div>

  <div class="app-card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
      <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; color: var(--cyan);">Quality & Penalty Calculator</h3>
      <span class="badge badge-amber" id="penalty-badge">Agreed 3% Spec</span>
    </div>
    <p style="font-size: 12px; color: var(--muted); margin-bottom: 8px;">Adjust measured fabric shrinkage to calculate contract deduction:</p>
    
    <div class="slider-box">
      <label><span>Tested Shrinkage</span><strong id="shrink-val">3.0% (Allowed)</strong></label>
      <input type="range" id="shrink-range" min="1.0" max="8.0" value="3.0" step="0.1" oninput="calcPenalty(this.value)">
    </div>

    <div class="grid-2">
      <div class="metric">
        <div class="metric-val" id="penalty-amt" style="color: var(--amber);">₹0</div>
        <div class="metric-lbl">Deduction</div>
      </div>
      <div class="metric">
        <div class="metric-val" id="net-payable" style="color: var(--emerald);">${escapeHtml(value)}</div>
        <div class="metric-lbl">Payable Release</div>
      </div>
    </div>
  </div>

  <div class="app-card" style="margin-bottom: 0;">
    <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; color: var(--emerald); margin-bottom: 8px;">Settlement Intent</h3>
    <button class="btn" style="background: #059669;" onclick="triggerUPI()">Initiate Verified Milestone UPI Payment</button>
    <div id="upi-msg" class="status-msg info">UPI payment intent payload ready. Authorize in external NPCI banking app.</div>
  </div>

  <script>
    const baseVal = ${numValue};
    let curStep = 1;

    function advanceStep() {
      if (curStep < 3) {
        document.getElementById('sn-' + curStep).className = 'step-node done';
        document.getElementById('sn-' + curStep).querySelector('.node-circle').innerText = '✓';
        curStep++;
        document.getElementById('sn-' + curStep).className = 'step-node active';
        if (curStep === 3) {
          document.getElementById('next-step-btn').innerText = 'All Milestones Satisfied';
          document.getElementById('next-step-btn').disabled = true;
        }
      }
    }

    function calcPenalty(val) {
      const v = parseFloat(val);
      document.getElementById('shrink-val').innerText = v.toFixed(1) + '% ' + (v <= 3.0 ? '(Within Tolerance)' : '(Exceeds Spec)');
      let deduction = 0;
      if (v > 3.0) {
        const excess = v - 3.0;
        deduction = Math.round(baseVal * (excess * 0.05));
      }
      const net = baseVal - deduction;
      document.getElementById('penalty-amt').innerText = '₹' + deduction.toLocaleString('en-IN');
      document.getElementById('net-payable').innerText = '₹' + net.toLocaleString('en-IN');
      
      const b = document.getElementById('penalty-badge');
      if (deduction > 0) {
        b.className = 'badge badge-red';
        b.innerText = '₹' + deduction.toLocaleString('en-IN') + ' Penalty';
      } else {
        b.className = 'badge badge-green';
        b.innerText = 'Pass Standard';
      }
    }

    function triggerUPI() {
      document.getElementById('upi-msg').classList.add('show');
    }
  </script>
</body>
</html>`;
}

function synthesizeBusinessApp(meta, rules) {
  const site = meta.site || "Industrial Foundry #4";
  const owner = meta.owner || "Factory Operations Lead";
  const title = meta.title || "Foundry Rules & Procurement Twin";

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dhandha Twin: ${escapeHtml(title)}</title>
  <style>
    ${getBaseStyles()}
    .gauge-container {
      position: relative;
      width: 160px;
      height: 90px;
      margin: 10px auto 0 auto;
    }
    .status-banner {
      padding: 10px;
      border-radius: 8px;
      text-align: center;
      font-weight: bold;
      margin-top: 10px;
    }
  </style>
</head>
<body>
  <div class="app-card">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
      <span class="badge badge-cyan">Dhandha Twin Simulation</span>
      <span style="font-size: 11px; color: var(--muted);">${escapeHtml(site)}</span>
    </div>
    <h2 style="font-size: 15px; font-weight: 700;">${escapeHtml(title)}</h2>
    <p style="font-size: 12px; color: var(--muted);">Supervised by ${escapeHtml(owner)}</p>
  </div>

  <div class="app-card">
    <div style="display: flex; justify-content: space-between; align-items: center;">
      <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; color: var(--cyan);">Yield Floor Decision Engine</h3>
      <span class="badge badge-green" id="yield-badge">Status: Buying</span>
    </div>
    <p style="font-size: 12px; color: var(--muted); margin-top: 4px;">Rule: If metal recovery yield drops below 84%, automatically freeze supplier purchase orders.</p>

    <div class="slider-box" style="margin-top: 14px;">
      <label><span>Simulated Scrap Yield</span><strong id="yield-val">87.5%</strong></label>
      <input type="range" id="yield-slider" min="70" max="98" value="87.5" step="0.5" oninput="testYield(this.value)">
    </div>

    <div id="yield-banner" class="status-banner" style="background: rgba(52, 211, 153, 0.15); border: 1px solid rgba(52, 211, 153, 0.4); color: var(--emerald);">
      ✓ Yield Healthy: Purchasing Active
    </div>
  </div>

  <div class="app-card">
    <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; color: var(--cyan); margin-bottom: 8px;">Forex & Cost Stress Tester</h3>
    <div class="grid-2">
      <div class="metric">
        <div class="metric-val" id="margin-disp">+18.4%</div>
        <div class="metric-lbl">Operating Margin</div>
      </div>
      <div class="metric">
        <div class="metric-val" id="scrap-cost">₹41.20</div>
        <div class="metric-lbl">Scrap / Kg</div>
      </div>
    </div>
    <button class="btn btn-ghost" onclick="toggleForexSpike()" id="forex-btn" style="margin-top: 10px;">Simulate +5% Dollar Index Spike</button>
  </div>

  <div class="app-card" style="margin-bottom: 0;">
    <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; color: var(--cyan); margin-bottom: 8px;">Automated Procurement Action</h3>
    <button class="btn" id="procure-btn" onclick="createProcurementTicket()">Generate Supplier Consignment Ticket</button>
    <div id="procure-msg" class="status-msg success">Purchase Requisition #PR-MET-441 issued to Approved Foundry Vendor.</div>
  </div>

  <script>
    let forexSpiked = false;
    function testYield(val) {
      const v = parseFloat(val);
      document.getElementById('yield-val').innerText = v.toFixed(1) + '%';
      const badge = document.getElementById('yield-badge');
      const banner = document.getElementById('yield-banner');
      const procureBtn = document.getElementById('procure-btn');
      
      if (v < 84.0) {
        badge.className = 'badge badge-red';
        badge.innerText = 'PO Freeze';
        banner.style.background = 'rgba(248, 113, 113, 0.15)';
        banner.style.borderColor = 'rgba(248, 113, 113, 0.4)';
        banner.style.color = 'var(--red)';
        banner.innerText = '⚠️ Yield Below 84% Threshold: PO Freeze Activated';
        procureBtn.disabled = true;
        procureBtn.innerText = 'Purchasing Frozen by Rule';
      } else {
        badge.className = 'badge badge-green';
        badge.innerText = 'Status: Buying';
        banner.style.background = 'rgba(52, 211, 153, 0.15)';
        banner.style.borderColor = 'rgba(52, 211, 153, 0.4)';
        banner.style.color = 'var(--emerald)';
        banner.innerText = '✓ Yield Healthy: Purchasing Active';
        procureBtn.disabled = false;
        procureBtn.innerText = 'Generate Supplier Consignment Ticket';
      }
    }

    function toggleForexSpike() {
      forexSpiked = !forexSpiked;
      const btn = document.getElementById('forex-btn');
      if (forexSpiked) {
        btn.innerText = 'Reset Forex Baseline';
        document.getElementById('margin-disp').innerText = '+12.1%';
        document.getElementById('margin-disp').style.color = 'var(--amber)';
        document.getElementById('scrap-cost').innerText = '₹44.80';
      } else {
        btn.innerText = 'Simulate +5% Dollar Index Spike';
        document.getElementById('margin-disp').innerText = '+18.4%';
        document.getElementById('margin-disp').style.color = 'var(--cyan)';
        document.getElementById('scrap-cost').innerText = '₹41.20';
      }
    }

    function createProcurementTicket() {
      document.getElementById('procure-msg').classList.add('show');
    }
  </script>
</body>
</html>`;
}

export function getBespokeAppHtml(mode, metadata = {}, rules = [], domain = "") {
  if (mode === "awareness") return synthesizeAwarenessApp(metadata, rules);
  if (mode === "audit") return synthesizeAuditApp(metadata, rules);
  if (mode === "deals") return synthesizeDealsApp(metadata, rules);
  return requirementsApp(metadata.title, rules);
}
