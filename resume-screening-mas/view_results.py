from __future__ import annotations
import json
from pathlib import Path

state      = json.loads(Path("state/shared_state.json").read_text(encoding="utf-8"))
candidates = sorted(state.get("scored_candidates", []), key=lambda x: x["final_score"], reverse=True)
fit_results = state.get("fit_results", [])
logs       = Path("logs/agent_trace.log").read_text(encoding="utf-8", errors="ignore") if Path("logs/agent_trace.log").exists() else ""

def rbg(r):  return {"Low":"#E6F1FB","Medium":"#fef9e7","High":"#FCEBEB"}.get(r,"#f5f5f5")
def rtx(r):  return {"Low":"#0C447C","Medium":"#854F0B","High":"#A32D2D"}.get(r,"#555")
def rbd(r):  return {"Low":"#185FA5","Medium":"#BA7517","High":"#E24B4A"}.get(r,"#999")
def rec(r):  return {"Low":"&#10003; Shortlist","Medium":"~ Review","High":"&#10005; Reject"}.get(r,"—")
def rcc(r):  return {"Low":"#3B6D11","Medium":"#854F0B","High":"#A32D2D"}.get(r,"#555")
def bar(r):  return {"Low":"#185FA5","Medium":"#BA7517","High":"#E24B4A"}.get(r,"#999")
def adj(a):
    a=float(a)
    return (f'<span style="color:#3B6D11">+{a:.0f}</span>' if a>0
            else f'<span style="color:#E24B4A">{a:.0f}</span>' if a<0
            else '<span style="color:#999">0</span>')

# ── Fit level colors ────────────────────────────────────────
def fbg(f):  return {"Strong":"#E6F4EA","Moderate":"#fef9e7","Weak":"#FCEBEB"}.get(f,"#f5f5f5")
def ftx(f):  return {"Strong":"#1E6B35","Moderate":"#854F0B","Weak":"#A32D2D"}.get(f,"#555")
def fbd(f):  return {"Strong":"#2E7D32","Moderate":"#BA7517","Weak":"#E24B4A"}.get(f,"#999")

# ── Scoring & Risk cards (Member 3) ─────────────────────────
cards=""
for i,c in enumerate(candidates,1):
    ini="".join(w[0] for w in c["candidate_name"].split()[:2]).upper()
    fl="".join(f'<div style="font-size:12px;color:#A32D2D;margin-top:3px">&#9888; {f}</div>' for f in c.get("risk_flags",[]))
    if not fl: fl='<div style="font-size:12px;color:#3B6D11;margin-top:4px">&#10003; No risk flags</div>'
    border = 'border-left:3px solid #185FA5;border-radius:0 12px 12px 0' if i==1 else 'border-radius:12px'
    cards+=f"""<div style="background:#fff;border:0.5px solid #B5D4F4;{border};padding:1rem 1.25rem;margin-bottom:10px;display:grid;grid-template-columns:42px 1fr 88px;gap:12px;align-items:start">
  <div style="width:42px;height:42px;border-radius:50%;background:{rbg(c['risk_level'])};display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:500;color:{rtx(c['risk_level'])};flex-shrink:0">{ini}</div>
  <div>
    <div style="font-size:14px;font-weight:500;color:#111;margin-bottom:3px">{c['candidate_name']} <span style="font-size:10px;background:#E6F1FB;color:#185FA5;border-radius:4px;padding:1px 6px;margin-left:4px">#{i}</span></div>
    <span style="display:inline-block;font-size:11px;padding:2px 8px;border-radius:999px;background:{rbg(c['risk_level'])};color:{rtx(c['risk_level'])};font-weight:500;margin-bottom:6px">{c['risk_level']} risk</span>
    {fl}
    <div style="font-size:12px;color:#555;margin-top:8px;padding-top:8px;border-top:0.5px solid #E6F1FB;line-height:1.5">{c.get('score_reasoning','—')}</div>
  </div>
  <div style="text-align:center">
    <div style="font-size:26px;font-weight:500;color:#185FA5;line-height:1">{c['final_score']:.0f}</div>
    <div style="font-size:11px;color:#888;margin-top:3px">base {c.get('base_score_used','—')}</div>
    <div style="font-size:12px;margin-top:3px;font-weight:500">{adj(c.get('score_adjustment',0))} adj</div>
    <div style="height:4px;background:#E6F1FB;border-radius:99px;margin-top:8px"><div style="height:100%;width:{float(c['final_score'])}%;background:{bar(c['risk_level'])};border-radius:99px"></div></div>
  </div>
</div>"""

# ── Score summary table rows (Member 3) ─────────────────────
rows=""
for i,c in enumerate(candidates,1):
    rows+=f"""<tr style="border-top:0.5px solid #E6F1FB">
  <td style="padding:10px 14px;font-size:13px;color:#378ADD;font-weight:500">{i}</td>
  <td style="padding:10px 14px;font-size:13px;font-weight:500;color:#111">{c['candidate_name']}</td>
  <td style="padding:10px 14px;text-align:center;font-size:14px;font-weight:500;color:#185FA5">{c['final_score']:.0f}</td>
  <td style="padding:10px 14px;text-align:center;font-size:13px;color:#888">{c.get('base_score_used','—')}</td>
  <td style="padding:10px 14px;text-align:center"><span style="font-size:11px;padding:2px 8px;border-radius:999px;background:{rbg(c['risk_level'])};color:{rtx(c['risk_level'])};font-weight:500">{c['risk_level']}</span></td>
  <td style="padding:10px 14px;text-align:center;font-size:13px;color:{rcc(c['risk_level'])};font-weight:500">{rec(c['risk_level'])}</td>
</tr>"""

# ── Job Fit Analysis cards (Member 2) ───────────────────────
fit_cards=""
if not fit_results:
    fit_cards='<div style="text-align:center;padding:2.5rem;color:#888;font-size:13px">No fit results found. Run crew.py first.</div>'
else:
    strong_count  = sum(1 for f in fit_results if f.get("fit_level") == "Strong")
    moderate_count= sum(1 for f in fit_results if f.get("fit_level") == "Moderate")
    weak_count    = sum(1 for f in fit_results if f.get("fit_level") == "Weak")

    # Summary stats bar
    fit_cards += f"""
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:1.25rem">
  <div style="background:#E6F4EA;border-radius:8px;padding:12px 14px;text-align:center">
    <div style="font-size:11px;color:#1E6B35;text-transform:uppercase;letter-spacing:.05em;font-weight:500;margin-bottom:5px">Strong Fit</div>
    <div style="font-size:22px;font-weight:500;color:#2E7D32">{strong_count}</div>
  </div>
  <div style="background:#fef9e7;border-radius:8px;padding:12px 14px;text-align:center">
    <div style="font-size:11px;color:#854F0B;text-transform:uppercase;letter-spacing:.05em;font-weight:500;margin-bottom:5px">Moderate Fit</div>
    <div style="font-size:22px;font-weight:500;color:#BA7517">{moderate_count}</div>
  </div>
  <div style="background:#FCEBEB;border-radius:8px;padding:12px 14px;text-align:center">
    <div style="font-size:11px;color:#A32D2D;text-transform:uppercase;letter-spacing:.05em;font-weight:500;margin-bottom:5px">Weak Fit</div>
    <div style="font-size:22px;font-weight:500;color:#E24B4A">{weak_count}</div>
  </div>
</div>"""

    # Individual candidate fit cards
    for f in fit_results:
        name        = f.get("candidate_name", "Unknown")
        fit_level   = f.get("fit_level", "Unknown")
        reasoning   = f.get("fit_reasoning", "—")
        matched     = f.get("matched_skills", [])
        missing     = f.get("missing_critical_skills", [])
        partial     = f.get("partial_matches", [])
        exp_fit     = f.get("experience_fit", "—")
        edu_fit     = f.get("education_fit", "—")
        ini         = "".join(w[0] for w in name.split()[:2]).upper()

        matched_tags = "".join(
            f'<span style="display:inline-block;font-size:11px;background:#E6F4EA;color:#1E6B35;border-radius:4px;padding:2px 8px;margin:2px 3px 2px 0">&#10003; {s}</span>'
            for s in matched
        ) or '<span style="font-size:11px;color:#999">None</span>'

        partial_tags = "".join(
            f'<span style="display:inline-block;font-size:11px;background:#fef9e7;color:#854F0B;border-radius:4px;padding:2px 8px;margin:2px 3px 2px 0">~ {s}</span>'
            for s in partial
        ) or '<span style="font-size:11px;color:#999">None</span>'

        missing_tags = "".join(
            f'<span style="display:inline-block;font-size:11px;background:#FCEBEB;color:#A32D2D;border-radius:4px;padding:2px 8px;margin:2px 3px 2px 0">&#10005; {s}</span>'
            for s in missing
        ) or '<span style="font-size:11px;color:#3B6D11">&#10003; None missing</span>'

        fit_cards += f"""
<div style="background:#fff;border:0.5px solid #c8e6c9;border-radius:12px;padding:1rem 1.25rem;margin-bottom:10px">
  <div style="display:grid;grid-template-columns:42px 1fr auto;gap:12px;align-items:start">

    <div style="width:42px;height:42px;border-radius:50%;background:{fbg(fit_level)};display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:500;color:{ftx(fit_level)};flex-shrink:0">{ini}</div>

    <div>
      <div style="font-size:14px;font-weight:500;color:#111;margin-bottom:6px">{name}</div>
      <div style="margin-bottom:6px">
        <div style="font-size:11px;color:#888;margin-bottom:3px;text-transform:uppercase;letter-spacing:.04em">Matched Skills</div>
        {matched_tags}
      </div>
      <div style="margin-bottom:6px">
        <div style="font-size:11px;color:#888;margin-bottom:3px;text-transform:uppercase;letter-spacing:.04em">Partial Matches</div>
        {partial_tags}
      </div>
      <div style="margin-bottom:8px">
        <div style="font-size:11px;color:#888;margin-bottom:3px;text-transform:uppercase;letter-spacing:.04em">Missing Critical Skills</div>
        {missing_tags}
      </div>
      <div style="display:flex;gap:8px;margin-bottom:8px">
        <span style="font-size:11px;background:#E6F1FB;color:#185FA5;border-radius:4px;padding:2px 8px">Experience: {exp_fit}</span>
        <span style="font-size:11px;background:#E6F1FB;color:#185FA5;border-radius:4px;padding:2px 8px">Education: {edu_fit}</span>
      </div>
      <div style="font-size:12px;color:#555;padding-top:8px;border-top:0.5px solid #E6F4EA;line-height:1.5">{reasoning}</div>
    </div>

    <div style="text-align:center;min-width:80px">
      <span style="display:inline-block;font-size:12px;padding:4px 12px;border-radius:999px;background:{fbg(fit_level)};color:{ftx(fit_level)};font-weight:500;border:1px solid {fbd(fit_level)}">{fit_level}</span>
    </div>

  </div>
</div>"""

# ── Log rows ─────────────────────────────────────────────────
log_rows="".join(
    f'<div style="font-size:11px;font-family:monospace;padding:7px 12px;border-bottom:0.5px solid #0C447C;color:#85B7EB;line-height:1.6">{l}</div>'
    for l in logs.strip().split("\n") if l.strip()
)

# ── Summary counts ───────────────────────────────────────────
low  = sum(1 for c in candidates if c["risk_level"]=="Low")
med  = sum(1 for c in candidates if c["risk_level"]=="Medium")
high = sum(1 for c in candidates if c["risk_level"]=="High")

# ── Full HTML ────────────────────────────────────────────────
html=f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Resume Screening Dashboard</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:Arial,sans-serif;background:#f0f4f9;padding:28px;color:#111}}
.tabs{{display:flex;gap:2px;background:#E6F1FB;border-radius:8px;padding:3px;margin-bottom:1.25rem}}
.tab{{flex:1;padding:7px 12px;font-size:13px;cursor:pointer;border:none;background:transparent;color:#378ADD;border-radius:6px;font-weight:400}}
.tab.active{{background:#fff;color:#185FA5;font-weight:500;border:0.5px solid #B5D4F4}}
.tab:hover:not(.active){{background:#B5D4F4;color:#0C447C}}
.panel{{display:none}}.panel.active{{display:block}}
table{{width:100%;border-collapse:collapse;background:#fff;border-radius:12px;overflow:hidden;border:0.5px solid #B5D4F4;table-layout:fixed}}
th{{background:#E6F1FB;padding:10px 14px;text-align:left;font-size:11px;font-weight:500;color:#185FA5;text-transform:uppercase;letter-spacing:.05em}}
</style></head>
<body>

<div style="background:#185FA5;border-radius:12px;padding:1.25rem 1.5rem;margin-bottom:1.25rem;display:flex;justify-content:space-between;align-items:center">
  <div>
    <div style="font-size:18px;font-weight:500;color:#fff">Resume Screening Dashboard</div>
    <div style="font-size:12px;color:#85B7EB;margin-top:3px">Senior Backend Engineer &mdash; MAS Pipeline Output</div>
  </div>
  <div style="background:#0C447C;color:#B5D4F4;font-size:11px;padding:4px 14px;border-radius:999px;font-weight:500">{len(candidates)} candidates scored</div>
</div>

<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:1.25rem">
  <div style="background:#E6F1FB;border-radius:8px;padding:12px 14px"><div style="font-size:11px;color:#185FA5;text-transform:uppercase;letter-spacing:.05em;font-weight:500;margin-bottom:5px">Total Scored</div><div style="font-size:22px;font-weight:500;color:#0C447C">{len(candidates)}</div></div>
  <div style="background:#E6F1FB;border-radius:8px;padding:12px 14px"><div style="font-size:11px;color:#0C447C;text-transform:uppercase;letter-spacing:.05em;font-weight:500;margin-bottom:5px">Low Risk</div><div style="font-size:22px;font-weight:500;color:#185FA5">{low}</div></div>
  <div style="background:#fef9e7;border-radius:8px;padding:12px 14px"><div style="font-size:11px;color:#854F0B;text-transform:uppercase;letter-spacing:.05em;font-weight:500;margin-bottom:5px">Medium Risk</div><div style="font-size:22px;font-weight:500;color:#BA7517">{med}</div></div>
  <div style="background:#FCEBEB;border-radius:8px;padding:12px 14px"><div style="font-size:11px;color:#A32D2D;text-transform:uppercase;letter-spacing:.05em;font-weight:500;margin-bottom:5px">High Risk</div><div style="font-size:22px;font-weight:500;color:#E24B4A">{high}</div></div>
</div>

<div class="tabs">
  <button class="tab active" onclick="showTab('scoring',this)">Scoring &amp; Risk</button>
  <button class="tab" onclick="showTab('ranking',this)">Score Summary</button>
  <button class="tab" onclick="showTab('fitanalysis',this)">Job Fit Analysis</button>
  <button class="tab" onclick="showTab('logs',this)">Agent Logs</button>
  <button class="tab" onclick="showTab('member4',this)">Member 4 Output</button>
</div>

<div id="scoring"     class="panel active">{cards}</div>
<div id="ranking"     class="panel">
  <table><thead><tr>
    <th style="width:36px">#</th>
    <th>Candidate</th>
    <th style="text-align:center;width:100px">Final Score</th>
    <th style="text-align:center;width:100px">Base Score</th>
    <th style="text-align:center;width:90px">Risk</th>
    <th style="text-align:center;width:100px">Decision</th>
  </tr></thead><tbody>{rows}</tbody></table>
</div>
<div id="fitanalysis" class="panel">{fit_cards}</div>
<div id="logs"        class="panel">
  <div style="background:#042C53;border-radius:12px;overflow:hidden;border:0.5px solid #0C447C">
    {log_rows or '<div style="padding:20px;color:#85B7EB;font-size:13px">No logs found.</div>'}
  </div>
</div>
<div id="member4" class="panel">
  <div style="text-align:center;padding:2.5rem 1rem;border:1px dashed #B5D4F4;border-radius:12px;color:#378ADD">
    <div style="font-size:28px;margin-bottom:10px;color:#185FA5">&#9998;</div>
    <div style="font-size:14px;font-weight:500;color:#111;margin-bottom:6px">Member 4 &mdash; Ranking &amp; Report Agent</div>
    <div style="font-size:13px">Not implemented yet. Will read <code>scored_candidates</code> from state and write <code>outputs/shortlist.md</code></div>
  </div>
</div>

<script>
function showTab(id,el){{
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  el.classList.add('active');
}}
</script>
</body></html>"""

Path("outputs").mkdir(exist_ok=True)
Path("outputs/results.html").write_text(html, encoding="utf-8")
print("Dashboard saved -> outputs/results.html")