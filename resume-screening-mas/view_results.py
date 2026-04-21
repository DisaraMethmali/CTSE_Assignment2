"""view_results.py — Generate a visual HTML report from shared state."""
from __future__ import annotations
import json
from pathlib import Path

state = json.loads(Path("state/shared_state.json").read_text())
candidates = state.get("scored_candidates", [])

rows = ""
for c in sorted(candidates, key=lambda x: x["final_score"], reverse=True):
    risk_color = {"Low": "#2ecc71", "Medium": "#f39c12", "High": "#e74c3c"}.get(c["risk_level"], "#999")
    flags_html = "".join(f"<li>⚠ {f}</li>" for f in c.get("risk_flags", []))
    flags_html = f"<ul>{flags_html}</ul>" if flags_html else "<span style='color:#2ecc71'>✔ No flags</span>"
    rows += f"""
    <tr>
        <td><strong>{c['candidate_name']}</strong></td>
        <td style='font-size:1.4em; font-weight:bold'>{c['final_score']}</td>
        <td>{c.get('base_score_used', '—')}</td>
        <td style='color:{"#2ecc71" if float(c.get("score_adjustment",0)) >= 0 else "#e74c3c"}'>
            {'+' if float(c.get('score_adjustment',0)) >= 0 else ''}{c.get('score_adjustment', 0)}
        </td>
        <td><span style='background:{risk_color};color:white;padding:3px 10px;border-radius:12px'>
            {c['risk_level']}</span></td>
        <td style='font-size:0.85em'>{flags_html}</td>
        <td style='font-size:0.85em;color:#555'>{c.get('score_reasoning','—')}</td>
    </tr>"""

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset='utf-8'>
<title>Resume Screening Results</title>
<style>
  body {{ font-family: Arial, sans-serif; padding: 30px; background: #f5f5f5; }}
  h1   {{ color: #2c3e50; }}
  table {{ width: 100%; border-collapse: collapse; background: white;
           box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }}
  th   {{ background: #2c3e50; color: white; padding: 12px 15px; text-align: left; }}
  td   {{ padding: 12px 15px; border-bottom: 1px solid #eee; vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #f9f9f9; }}
  ul   {{ margin: 0; padding-left: 16px; }}
</style>
</head>
<body>
<h1>📋 Resume Screening Results</h1>
<p>Total candidates scored: <strong>{len(candidates)}</strong></p>
<table>
  <thead>
    <tr>
      <th>Candidate</th>
      <th>Final Score</th>
      <th>Base Score</th>
      <th>Adjustment</th>
      <th>Risk Level</th>
      <th>Risk Flags</th>
      <th>Reasoning</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
</body>
</html>"""

Path("outputs").mkdir(exist_ok=True)
Path("outputs/results.html").write_text(html, encoding="utf-8")
print("Report saved → outputs/results.html")