"""
app.py — CV Upload Dashboard + Integrated Results Viewer
Run:  python app.py
Then: python crew.py
Then: python generate_dashboard.py
Visit: http://localhost:5000
"""
from __future__ import annotations

import io
import json
import logging
import re
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template_string, request

# ── PDF backend ──────────────────────────────────────────────
try:
    import pdfplumber
    PDF_BACKEND = "pdfplumber"
except ImportError:
    try:
        import pypdf
        PDF_BACKEND = "pypdf"
    except ImportError:
        PDF_BACKEND = None

# ── Project tools ────────────────────────────────────────────
try:
    from tools.member1_resume_tool import (
        extract_candidate_fields,
        normalise_skills,
        validate_candidate_profile,
    )
except ImportError:
    try:
        from tools.member1_extract_resume import (
            extract_candidate_fields,
            normalise_skills,
            validate_candidate_profile,
        )
    except ImportError:
        def extract_candidate_fields(raw):
            skills = raw.get("skills", [])
            if isinstance(skills, str):
                skills = [s.strip() for s in skills.split(",") if s.strip()]
            return {
                "name":             str(raw.get("name", "Unknown")).strip(),
                "skills":           skills,
                "experience_years": raw.get("experience_years"),
                "education":        str(raw.get("education", "Not specified")).strip(),
                "email":            str(raw.get("email", "")).strip(),
                "phone":            str(raw.get("phone", "")).strip(),
                "raw_text":         str(raw.get("raw_text", "")).strip(),
            }
        def normalise_skills(skills):
            seen, result = set(), []
            for s in skills:
                k = s.strip().lower()
                if k and k not in seen:
                    seen.add(k)
                    result.append(s.strip())
            return result
        def validate_candidate_profile(c):
            notes = []
            if not c.get("name") or c["name"].lower() == "unknown":
                notes.append("Name missing")
            if not c.get("skills"):
                notes.append("No skills listed")
            return {"valid": len(notes) == 0, "notes": notes}

# ── State helpers ────────────────────────────────────────────
STATE_PATH = Path("state/shared_state.json")

def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}

def save_state(s: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")

try:
    from state.shared_state import load_state, save_state  # type: ignore[assignment]
except ImportError:
    pass

# ── App setup ────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024

UPLOAD_DIR = Path("data/resumes")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CVUploadApp")

SKILL_PATTERNS: list[tuple[str, list[str]]] = [
    ("Python",         [r"\bPython\b"]),
    ("Java",           [r"\bJava\b(?!Script)"]),
    ("JavaScript",     [r"\bJavaScript\b", r"\bJS\b"]),
    ("TypeScript",     [r"\bTypeScript\b"]),
    ("C++",            [r"\bC\+\+"]),
    ("C#",             [r"\bC#\b"]),
    ("Go",             [r"\bGolang\b", r"\bGo\b"]),
    ("Rust",           [r"\bRust\b"]),
    ("SQL",            [r"\bSQL\b", r"\bRelational\s+Databases?\b"]),
    ("PostgreSQL",     [r"\bPostgreSQL\b", r"\bPostgres\b"]),
    ("MySQL",          [r"\bMySQL\b"]),
    ("MongoDB",        [r"\bMongoDB\b"]),
    ("Redis",          [r"\bRedis\b"]),
    ("Elasticsearch",  [r"\bElasticsearch\b"]),
    ("Docker",         [r"\bDocker\b", r"\bContaineriz"]),
    ("Kubernetes",     [r"\bKubernetes\b", r"\bK8s\b"]),
    ("AWS",            [r"\bAWS\b", r"\bAmazon\s+Web\s+Services\b"]),
    ("Azure",          [r"\bAzure\b"]),
    ("GCP",            [r"\bGCP\b", r"\bGoogle\s+Cloud\b"]),
    ("Terraform",      [r"\bTerraform\b"]),
    ("REST APIs",      [r"\bREST\s*API\b", r"\bRESTful\b"]),
    ("GraphQL",        [r"\bGraphQL\b"]),
    ("gRPC",           [r"\bgRPC\b"]),
    ("FastAPI",        [r"\bFastAPI\b"]),
    ("Django",         [r"\bDjango\b"]),
    ("Flask",          [r"\bFlask\b"]),
    ("Spring",         [r"\bSpring(?:\s+Boot)?\b"]),
    ("Node.js",        [r"\bNode\.?js\b", r"\bNodeJS\b"]),
    ("React",          [r"\bReact\b"]),
    ("Vue",            [r"\bVue\.?js\b", r"\bVue\b"]),
    ("Angular",        [r"\bAngular\b"]),
    ("Git",            [r"\bGit\b(?!Hub)"]),
    ("GitHub Actions", [r"\bGitHub\s+Actions\b"]),
    ("CI/CD",          [r"\bCI\s*/\s*CD\b"]),
    ("Jenkins",        [r"\bJenkins\b"]),
    ("Ansible",        [r"\bAnsible\b"]),
    ("Prometheus",     [r"\bPrometheus\b"]),
    ("Linux",          [r"\bLinux\b", r"\bUnix\b"]),
    ("Kafka",          [r"\bKafka\b"]),
    ("RabbitMQ",       [r"\bRabbitMQ\b"]),
    ("Spark",          [r"\bApache\s+Spark\b", r"\bSpark\b"]),
    ("Hadoop",         [r"\bHadoop\b"]),
    ("Airflow",        [r"\bAirflow\b"]),
    ("dbt",            [r"\bdbt\b"]),
    ("TensorFlow",     [r"\bTensorFlow\b"]),
    ("PyTorch",        [r"\bPyTorch\b"]),
    ("scikit-learn",   [r"\bscikit[\-\s]learn\b", r"\bsklearn\b"]),
    ("Pandas",         [r"\bPandas\b"]),
    ("NumPy",          [r"\bNumPy\b", r"\bNumpy\b"]),
]

# ── PDF helpers ──────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    if PDF_BACKEND == "pdfplumber":
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    if PDF_BACKEND == "pypdf":
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return ""


_NOT_NAME_RE = re.compile(
    r"(senior|junior|engineer|developer|analyst|manager|lead|intern|"
    r"resume|curriculum|vitae|cv|profile|summary|experience|skills|"
    r"education|contact|objective)",
    re.IGNORECASE,
)

def _extract_name_from_text(text: str, filename: str) -> str:
    m = re.search(r"(?:^|\n)\s*Name\s*[:\-]\s*([^\n]+)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines[:10]:
        if _NOT_NAME_RE.search(line):
            continue
        words = line.split()
        if 2 <= len(words) <= 4 and all(re.match(r"[A-Z][a-z]+", w) for w in words):
            return line
    stem = Path(filename).stem.replace("_", " ").replace("-", " ")
    stem = re.sub(r"\s*(cv|resume|curriculum)\s*$", "", stem, flags=re.IGNORECASE).strip()
    return stem.title() if stem else "Unknown"


def _extract_skills_from_text(text: str) -> list[str]:
    found, seen = [], set()
    for label, patterns in SKILL_PATTERNS:
        if label in seen:
            continue
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                found.append(label)
                seen.add(label)
                break
    return found


def parse_cv_text(text: str, filename: str) -> dict[str, Any]:
    name = _extract_name_from_text(text, filename)
    email_m = re.search(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}", text)
    email = email_m.group(0) if email_m else ""
    phone_m = re.search(r"[\+\d][\d\s\-\(\)]{7,15}\d", text)
    phone = phone_m.group(0).strip() if phone_m else ""
    exp_matches = re.findall(r"(\d+)\s*\+?\s*years?", text, re.IGNORECASE)
    experience_years = max(int(x) for x in exp_matches) if exp_matches else None
    edu_m = re.search(
        r"(B\.?Sc|M\.?Sc|B\.?E|M\.?E|Bachelor|Master|PhD|Diploma)[^\n]{0,100}",
        text, re.IGNORECASE,
    )
    education = edu_m.group(0).strip() if edu_m else "Not specified"
    found_skills = _extract_skills_from_text(text)
    raw = {
        "name": name, "email": email, "phone": phone,
        "experience_years": experience_years, "education": education,
        "skills": found_skills, "raw_text": text[:2000],
    }
    fields = extract_candidate_fields(raw)
    fields["skills"] = normalise_skills(fields["skills"])
    return fields


# ── Routes ───────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(UPLOAD_HTML)


@app.route("/upload", methods=["POST"])
def upload_cvs():
    files = request.files.getlist("cvs")
    if not files:
        return jsonify({"error": "No files received"}), 400
    if PDF_BACKEND is None:
        return jsonify({"error": "Install pdfplumber: pip install pdfplumber"}), 500

    state = load_state()
    if not state.get("job_requirements"):
        state["job_requirements"] = {"required_skills": [], "preferred_skills": [], "minimum_experience": None}
    if not state.get("job_description"):
        state["job_description"] = ""
    for key in ["candidates", "parsed_candidates", "fit_analyses", "fit_results",
                "scored_candidates", "scoring_results", "ranked_candidates",
                "shortlisted_candidates", "execution_trace"]:
        state.setdefault(key, [])
    state.setdefault("ranking_summary", {})
    state.setdefault("report_metadata", {})
    state.setdefault("final_report", "")

    uploaded, errors = [], []
    for f in files:
        if not f.filename:
            continue
        if not f.filename.lower().endswith(".pdf"):
            errors.append(f"{f.filename}: only PDF accepted")
            continue
        try:
            file_bytes = f.read()
            text = extract_text_from_pdf(file_bytes)
            if not text.strip():
                errors.append(f"{f.filename}: no text extracted (scanned PDF?)")
                continue
            parsed = parse_cv_text(text, f.filename)
            validation = validate_candidate_profile(parsed)
            (UPLOAD_DIR / f.filename).write_bytes(file_bytes)
            existing = {c.get("name", "").lower() for c in state["candidates"]}
            if parsed["name"].lower() in existing:
                errors.append(f"{f.filename}: '{parsed['name']}' already uploaded — skipped")
                continue
            state["candidates"].append({
                "name": parsed["name"],
                "file": f.filename,
                "path": str((UPLOAD_DIR / f.filename).resolve()),
                "skills": parsed["skills"],
                "experience_years": parsed["experience_years"],
            })
            state["parsed_candidates"].append({
                **parsed,
                "validation_passed": validation["valid"],
                "validation_notes": validation["notes"],
                "profile_summary": "Pending LLM enrichment.",
                "source_file": f.filename,
            })
            uploaded.append({
                "filename": f.filename,
                "name": parsed["name"],
                "skills": parsed["skills"],
                "experience_years": parsed["experience_years"],
                "education": parsed["education"],
                "email": parsed["email"],
                "validation_passed": validation["valid"],
                "validation_notes": validation["notes"],
            })
            logger.info("Parsed: %s → %s", f.filename, parsed["name"])
        except Exception as exc:
            errors.append(f"{f.filename}: {exc}")
            logger.error("Failed %s: %s", f.filename, exc)

    save_state(state)
    return jsonify({
        "uploaded": uploaded,
        "errors": errors,
        "total_candidates": len(state["candidates"]),
    })


@app.route("/save-job", methods=["POST"])
def save_job():
    body = request.get_json(silent=True) or {}
    state = load_state()
    state["job_requirements"] = {
        "required_skills": [s.strip() for s in body.get("required_skills", "").split(",") if s.strip()],
        "preferred_skills": [s.strip() for s in body.get("preferred_skills", "").split(",") if s.strip()],
        "minimum_experience": int(body["minimum_experience"]) if body.get("minimum_experience") else None,
    }
    state["job_description"] = body.get("job_description", "").strip()
    save_state(state)
    return jsonify({"message": "Job requirements saved."})


@app.route("/candidates", methods=["GET"])
def get_candidates():
    state = load_state()
    return jsonify({
        "candidates": state.get("parsed_candidates", []),
        "total_candidates": len(state.get("candidates", [])),
        "job_requirements": state.get("job_requirements", {}),
        "job_description": state.get("job_description", ""),
    })


@app.route("/clear", methods=["POST"])
def clear_state():
    save_state({
        "job_description": "", "job_requirements": {},
        "candidates": [], "parsed_candidates": [],
        "fit_analyses": [], "fit_results": [],
        "scored_candidates": [], "scoring_results": [],
        "ranked_candidates": [], "shortlisted_candidates": [],
        "ranking_summary": {}, "final_report": "",
        "report_metadata": {}, "execution_trace": [],
    })
    for f in UPLOAD_DIR.glob("*.pdf"):
        f.unlink(missing_ok=True)
    return jsonify({"message": "All cleared."})


@app.route("/dashboard-data", methods=["GET"])
def dashboard_data():
    state = load_state()
    results_html_path = Path("outputs/results.html")
    has_results_html = results_html_path.exists()

    return jsonify({
        "scored_candidates":    state.get("scored_candidates", []),
        "fit_results":          state.get("fit_results", []),
        "ranked_candidates":    state.get("ranked_candidates", []),
        "shortlisted_candidates": state.get("shortlisted_candidates", []),
        "ranking_summary":      state.get("ranking_summary", {}),
        "final_report":         state.get("final_report", ""),
        "report_metadata":      state.get("report_metadata", {}),
        "has_results_html":     has_results_html,
        "pipeline_ran":         bool(state.get("scored_candidates")),
    })


@app.route("/results")
def results():
    results_path = Path("outputs/results.html")
    if not results_path.exists():
        return (
            "<!DOCTYPE html><html><body style='font-family:sans-serif;padding:2rem'>"
            "<h2>No results yet</h2>"
            "<p>Run <code>crew.py</code> then <code>generate_dashboard.py</code> first.</p>"
            "<p><a href='/'>Back to Upload</a></p>"
            "</body></html>"
        ), 404
    return render_template_string(results_path.read_text(encoding="utf-8"))


# ── Main HTML ────────────────────────────────────────────────
UPLOAD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MAS Pipeline — CV Screening</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --bg:        #0C0E13;
  --surface:   #13161E;
  --surface2:  #1A1E29;
  --border:    #252A38;
  --border2:   #2E3447;
  --text:      #E8EAF0;
  --muted:     #5C6480;
  --dim:       #3A4060;
  --accent:    #4F8EF7;
  --accent2:   #2563EB;
  --green:     #34D399;
  --green-bg:  #0D2B20;
  --green-dim: #1A4535;
  --amber:     #FBBF24;
  --amber-bg:  #2A1F07;
  --amber-dim: #3D2D0A;
  --red:       #F87171;
  --red-bg:    #2A0F0F;
  --red-dim:   #3D1515;
  --blue-bg:   #0D1829;
  --blue-dim:  #162240;
  --mono: 'DM Mono', monospace;
  --sans: 'DM Sans', sans-serif;
  --display: 'Syne', sans-serif;
  --r: 6px;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  min-height: 100vh;
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 99px; }

/* ── Topbar ── */
.topbar {
  height: 52px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 200;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand-logo {
  width: 28px;
  height: 28px;
  background: var(--accent2);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--display);
  font-size: 13px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.03em;
}
.brand-name {
  font-family: var(--display);
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: 0.01em;
}
.brand-sep {
  width: 1px;
  height: 16px;
  background: var(--border2);
}
.brand-sub {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--muted);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.count-badge {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted);
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 99px;
  padding: 3px 12px;
}
.count-badge span { color: var(--accent); font-weight: 500; }

/* ── Layout ── */
.layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  height: calc(100vh - 52px);
}
.sidebar {
  background: var(--surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 20px 12px;
  overflow-y: auto;
  position: sticky;
  top: 52px;
  height: calc(100vh - 52px);
}
.main {
  overflow-y: auto;
  padding: 28px 32px;
  background: var(--bg);
}

/* ── Sidebar nav ── */
.nav-section { margin-bottom: 24px; }
.nav-section-label {
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--dim);
  padding: 0 10px;
  margin-bottom: 6px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: var(--r);
  border: none;
  background: transparent;
  color: var(--muted);
  font-family: var(--sans);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  width: 100%;
  text-align: left;
  transition: all 0.15s;
  position: relative;
}
.nav-item:hover { background: var(--surface2); color: var(--text); }
.nav-item.active { background: var(--blue-bg); color: var(--accent); }
.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 2px;
  height: 18px;
  background: var(--accent);
  border-radius: 0 2px 2px 0;
}
.nav-num {
  font-family: var(--mono);
  font-size: 10px;
  color: inherit;
  opacity: 0.6;
  min-width: 18px;
}

/* ── Pipeline status ── */
.pipeline-track {
  margin-top: auto;
  padding: 14px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--r);
}
.pipeline-track-label {
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--dim);
  margin-bottom: 12px;
}
.track-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--mono);
  font-size: 10px;
  color: var(--dim);
  margin-bottom: 8px;
}
.track-step:last-child { margin-bottom: 0; }
.track-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--dim);
  flex-shrink: 0;
  transition: all 0.2s;
}
.track-step.done { color: var(--green); }
.track-step.done .track-dot { background: var(--green); box-shadow: 0 0 6px var(--green); }
.track-step.active { color: var(--accent); }
.track-step.active .track-dot { background: var(--accent); box-shadow: 0 0 6px var(--accent); }

/* ── Candidate count ── */
.sidebar-stat {
  margin-bottom: 12px;
  padding: 12px 14px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--r);
}
.sidebar-stat-label {
  font-family: var(--mono);
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--muted);
  margin-bottom: 4px;
}
.sidebar-stat-val {
  font-family: var(--display);
  font-size: 30px;
  font-weight: 700;
  color: var(--text);
  line-height: 1;
}

/* ── Panel ── */
.panel { display: none; }
.panel.active { display: block; }

/* ── Page header ── */
.page-header { margin-bottom: 24px; }
.page-title {
  font-family: var(--display);
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.01em;
  line-height: 1.2;
}

/* ── Drop zone ── */
.dropzone {
  border: 1.5px dashed var(--border2);
  border-radius: 10px;
  padding: 52px 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--surface);
  position: relative;
}
.dropzone:hover, .dropzone.over {
  border-color: var(--accent);
  background: var(--blue-bg);
}
.dropzone input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
  width: 100%;
  height: 100%;
}
.dz-icon {
  width: 48px;
  height: 48px;
  background: var(--surface2);
  border: 1px solid var(--border2);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  margin: 0 auto 16px;
}
.dz-title {
  font-family: var(--display);
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 6px;
}
.dz-sub {
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted);
}
.dz-badge {
  display: inline-block;
  margin-top: 14px;
  font-family: var(--mono);
  font-size: 10px;
  color: var(--accent);
  background: var(--blue-bg);
  border: 1px solid var(--blue-dim);
  padding: 4px 14px;
  border-radius: 99px;
  letter-spacing: 0.06em;
}

/* ── File list ── */
.file-list { display: grid; gap: 4px; margin-top: 12px; }
.file-row {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 8px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}
.file-icon { font-size: 13px; }
.file-name {
  font-family: var(--mono);
  color: var(--accent);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-size {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--muted);
}
.file-rm {
  background: none;
  border: none;
  color: var(--dim);
  cursor: pointer;
  font-size: 13px;
  line-height: 1;
  padding: 2px;
  transition: color 0.15s;
}
.file-rm:hover { color: var(--red); }

/* ── Buttons ── */
.btn-row { display: flex; gap: 8px; margin-top: 16px; flex-wrap: wrap; }
.btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 9px 18px;
  border: none;
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.05em;
  cursor: pointer;
  border-radius: var(--r);
  transition: all 0.15s;
  text-decoration: none;
  white-space: nowrap;
}
.btn-primary { background: var(--accent2); color: #fff; }
.btn-primary:hover { background: #1d4ed8; }
.btn-primary:disabled { opacity: 0.3; cursor: not-allowed; }
.btn-ghost { background: var(--surface2); color: var(--text); border: 1px solid var(--border2); }
.btn-ghost:hover { border-color: var(--muted); }
.btn-danger { background: transparent; color: var(--red); border: 1px solid var(--red-dim); }
.btn-danger:hover { background: var(--red-bg); }
.btn-success { background: #065f46; color: var(--green); border: 1px solid #064e3b; }
.btn-success:hover { background: #047857; }

/* ── Result rows ── */
.result-item {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 10px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  margin-top: 5px;
}
.result-name { font-weight: 600; flex: 1; }
.tag {
  display: inline-flex;
  align-items: center;
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.05em;
  padding: 2px 8px;
  border-radius: 99px;
  text-transform: uppercase;
  white-space: nowrap;
}
.tag-green { background: var(--green-bg); color: var(--green); border: 1px solid var(--green-dim); }
.tag-amber { background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber-dim); }
.tag-red   { background: var(--red-bg);   color: var(--red);   border: 1px solid var(--red-dim); }
.tag-blue  { background: var(--blue-bg);  color: var(--accent); border: 1px solid var(--blue-dim); }

/* ── Config card ── */
.config-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 16px;
}
.config-title {
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}
.field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
label {
  display: block;
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 6px;
}
input[type=text], input[type=number], textarea, select {
  background: var(--surface2);
  border: 1px solid var(--border2);
  border-radius: var(--r);
  padding: 8px 12px;
  color: var(--text);
  font-family: var(--mono);
  font-size: 12px;
  width: 100%;
  outline: none;
  transition: border-color 0.15s;
}
input:focus, textarea:focus { border-color: var(--accent); }
textarea { resize: vertical; min-height: 90px; }
input::placeholder, textarea::placeholder { color: var(--dim); }

/* ── Stats grid ── */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 24px;
}
.stat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 14px 16px;
}
.stat-label {
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 8px;
}
.stat-val {
  font-family: var(--display);
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}

/* ── Candidate cards ── */
.cand-grid { display: grid; gap: 8px; }
.cand-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 16px;
  display: grid;
  grid-template-columns: 38px 1fr;
  gap: 12px;
  transition: border-color 0.15s;
}
.cand-card:hover { border-color: var(--border2); }
.avatar {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--display);
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
}
.av0 { background: #162240; color: #60a5fa; }
.av1 { background: #0d2b20; color: #34d399; }
.av2 { background: #2a1f07; color: #fbbf24; }
.av3 { background: #270d2a; color: #c084fc; }
.cand-name { font-size: 13px; font-weight: 600; margin-bottom: 2px; }
.cand-meta {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--muted);
  margin-bottom: 8px;
}
.skill-list { display: flex; flex-wrap: wrap; gap: 4px; }
.skill-chip {
  font-family: var(--mono);
  font-size: 9px;
  background: var(--surface2);
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 7px;
}

/* ── Notice banners ── */
.notice      { background: var(--blue-bg);  border: 1px solid var(--blue-dim);  border-radius: var(--r); padding: 10px 14px; font-family: var(--mono); font-size: 11px; color: var(--accent); margin-bottom: 16px; }
.warn-notice { background: var(--amber-bg); border: 1px solid var(--amber-dim); border-radius: var(--r); padding: 10px 14px; font-family: var(--mono); font-size: 11px; color: var(--amber); margin-bottom: 16px; }
.ok-notice   { background: var(--green-bg); border: 1px solid var(--green-dim); border-radius: var(--r); padding: 10px 14px; font-family: var(--mono); font-size: 11px; color: var(--green); margin-bottom: 16px; }

/* ── Dashboard ── */
.dash-tabs {
  display: flex;
  gap: 2px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 3px;
  margin-bottom: 16px;
}
.dash-tab {
  flex: 1;
  padding: 7px 10px;
  font-size: 12px;
  cursor: pointer;
  border: none;
  background: transparent;
  color: var(--muted);
  border-radius: 4px;
  font-family: var(--mono);
  font-weight: 400;
  transition: all 0.15s;
}
.dash-tab:hover:not(.active) { color: var(--text); }
.dash-tab.active { background: var(--surface2); color: var(--text); border: 1px solid var(--border2); }
.dpanel { display: none; }
.dpanel.active { display: block; }

/* ── Score cards ── */
.score-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 8px;
  display: grid;
  grid-template-columns: 40px 1fr 72px;
  gap: 12px;
  align-items: start;
  transition: border-color 0.15s;
}
.score-card:hover { border-color: var(--border2); }
.score-card.top { border-left: 2px solid var(--accent); }
.score-num {
  font-family: var(--display);
  font-size: 26px;
  font-weight: 700;
  text-align: center;
  line-height: 1;
}
.score-lbl { font-family: var(--mono); font-size: 9px; color: var(--muted); text-align: center; margin-top: 3px; }
.score-adj { font-family: var(--mono); font-size: 10px; font-weight: 600; text-align: center; margin-top: 4px; }
.score-bar { height: 3px; background: var(--border); border-radius: 99px; margin-top: 8px; overflow: hidden; }
.score-bar-fill { height: 100%; border-radius: 99px; }
.risk-badge {
  display: inline-block;
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.05em;
  padding: 2px 8px;
  border-radius: 99px;
  text-transform: uppercase;
  margin-bottom: 6px;
}
.score-name { font-size: 13px; font-weight: 600; margin-bottom: 3px; }
.score-rank { font-family: var(--mono); font-size: 10px; color: var(--muted); margin-left: 5px; }
.flag-line { font-family: var(--mono); font-size: 10px; margin-top: 3px; }
.score-reasoning { font-size: 11px; color: var(--muted); margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border); line-height: 1.6; }

/* ── Fit cards ── */
.fit-summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 14px; }
.fit-stat { border-radius: 8px; padding: 12px; text-align: center; }
.fit-stat-label { font-family: var(--mono); font-size: 9px; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }
.fit-stat-num { font-family: var(--display); font-size: 22px; font-weight: 700; }
.fit-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 8px;
}
.fit-card-grid { display: grid; grid-template-columns: 38px 1fr auto; gap: 12px; align-items: start; }

/* ── Ranked table ── */
.ranked-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--surface);
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border);
}
.ranked-table th {
  background: var(--surface2);
  padding: 9px 14px;
  text-align: left;
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 500;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  border-bottom: 1px solid var(--border);
}
.ranked-table td {
  padding: 10px 14px;
  border-top: 1px solid var(--border);
  font-size: 12px;
  vertical-align: middle;
}

/* ── Report ── */
.report-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 18px 20px;
}
.report-title {
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}
.report-content {
  max-height: 420px;
  overflow-y: auto;
  font-size: 12px;
  color: #a0a8c0;
  line-height: 1.7;
}

/* ── Empty state ── */
.empty {
  text-align: center;
  padding: 56px 20px;
  color: var(--muted);
}
.empty-icon { font-size: 28px; opacity: 0.3; margin-bottom: 10px; }
.empty-txt { font-family: var(--mono); font-size: 11px; }

/* ── Meta strip ── */
.meta-strip {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: var(--r);
  padding: 8px 14px;
  font-family: var(--mono);
  font-size: 10px;
  color: var(--muted);
  margin-top: 10px;
  line-height: 1.8;
}

/* ── Divider ── */
.divider { height: 1px; background: var(--border); margin: 20px 0; }

/* ── Toast ── */
#toast {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background: var(--surface2);
  border: 1px solid var(--border2);
  color: var(--text);
  border-radius: var(--r);
  padding: 10px 18px;
  font-family: var(--mono);
  font-size: 11px;
  z-index: 9999;
  opacity: 0;
  transform: translateY(6px);
  transition: all 0.2s;
  pointer-events: none;
  max-width: 280px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.4);
}
#toast.show { opacity: 1; transform: translateY(0); }

/* ── Loading ── */
.loading-state {
  text-align: center;
  padding: 48px;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--muted);
}

/* ── Section heading ── */
.section-heading {
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 10px;
}
</style>
</head>
<body>

<!-- ── Topbar ── -->
<header class="topbar">
  <div class="brand">
    <div class="brand-logo">M</div>
    <div class="brand-name">MAS Pipeline</div>
    <div class="brand-sep"></div>
    <div class="brand-sub">CV Screening</div>
  </div>
  <div class="topbar-right">
    <div class="count-badge" id="top-count"><span id="top-count-num">0</span> candidates</div>
    <a href="/results" target="_blank" class="btn btn-ghost" id="open-results-btn" style="font-size:10px;padding:7px 14px">
      Open Full Dashboard ↗
    </a>
  </div>
</header>

<div class="layout">

  <!-- ── Sidebar ── -->
  <nav class="sidebar">
    <div class="nav-section">
      <div class="nav-section-label">Workflow</div>
      <button class="nav-item active" onclick="show('upload',this)">
        <span class="nav-num">01</span> Upload CVs
      </button>
      <button class="nav-item" onclick="show('job',this)">
        <span class="nav-num">02</span> Job Config
      </button>
      <button class="nav-item" onclick="show('candidates',this)">
        <span class="nav-num">03</span> Candidates
      </button>
      <button class="nav-item" onclick="show('dashboard',this)">
        <span class="nav-num">04</span> Results
      </button>
    </div>

    <div class="sidebar-stat">
      <div class="sidebar-stat-label">Candidates</div>
      <div class="sidebar-stat-val" id="sb-count">0</div>
    </div>

    <div class="pipeline-track">
      <div class="pipeline-track-label">Pipeline Status</div>
      <div class="track-step" id="ps-upload"><span class="track-dot"></span> Upload CVs</div>
      <div class="track-step" id="ps-job"><span class="track-dot"></span> Configure Job</div>
      <div class="track-step" id="ps-crew"><span class="track-dot"></span> Run crew.py</div>
      <div class="track-step" id="ps-gen"><span class="track-dot"></span> Generate Dashboard</div>
    </div>
  </nav>

  <!-- ── Main ── -->
  <main class="main">

    <!-- UPLOAD -->
    <div id="panel-upload" class="panel active">
      <div class="page-header">
        <div class="page-title">Upload CVs</div>
      </div>

      <div class="dropzone" id="dz">
        <input type="file" id="fi" accept=".pdf" multiple>
        <div class="dz-icon">📄</div>
        <div class="dz-title">Drop PDF files here</div>
        <div class="dz-sub">or click to browse</div>
        <div class="dz-badge">PDF only · max 20 MB each</div>
      </div>

      <div class="file-list" id="fileList"></div>

      <div class="btn-row">
        <button class="btn btn-primary" id="upBtn" onclick="doUpload()" disabled>⬆ Upload &amp; Parse</button>
        <button class="btn btn-danger" onclick="doClear()">✕ Clear State</button>
      </div>

      <div id="uploadResults" style="margin-top:14px"></div>
    </div>

    <!-- JOB CONFIG -->
    <div id="panel-job" class="panel">
      <div class="page-header">
        <div class="page-title">Job Config</div>
      </div>

      <div class="config-card">
        <div class="config-title">Screening Requirements</div>
        <div class="field-grid">
          <div>
            <label>Required Skills</label>
            <input type="text" id="reqSkills" placeholder="Python, SQL, Docker, REST APIs">
          </div>
          <div>
            <label>Preferred Skills</label>
            <input type="text" id="prefSkills" placeholder="Kubernetes, AWS, FastAPI">
          </div>
        </div>
        <div class="field-grid" style="grid-template-columns:140px 1fr">
          <div>
            <label>Min Experience (yrs)</label>
            <input type="number" id="minYears" placeholder="3" min="0" max="30">
          </div>
          <div>
            <label>Job Description</label>
            <textarea id="jobDesc" placeholder="Paste the full job description…"></textarea>
          </div>
        </div>
      </div>

      <div class="btn-row">
        <button class="btn btn-primary" onclick="saveJob()">💾 Save to State</button>
      </div>
      <div id="jobMsg" style="font-family:var(--mono);font-size:11px;color:var(--green);margin-top:10px"></div>
    </div>

    <!-- CANDIDATES -->
    <div id="panel-candidates" class="panel">
      <div class="page-header">
        <div class="page-title">Candidates</div>
      </div>

      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-label">Total</div>
          <div class="stat-val" id="sc-total" style="color:var(--accent)">—</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Valid</div>
          <div class="stat-val" id="sc-valid" style="color:var(--green)">—</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">With Email</div>
          <div class="stat-val" id="sc-email" style="color:var(--text)">—</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Avg Exp (yrs)</div>
          <div class="stat-val" id="sc-exp" style="color:var(--amber)">—</div>
        </div>
      </div>

      <div id="candList" class="cand-grid">
        <div class="empty">
          <div class="empty-icon">👤</div>
          <div class="empty-txt">No candidates yet — upload CVs first.</div>
        </div>
      </div>
    </div>

    <!-- RESULTS DASHBOARD -->
    <div id="panel-dashboard" class="panel">
      <div class="page-header">
        <div class="page-title">Results</div>
      </div>

      <div id="dash-not-run" class="warn-notice" style="display:none">
        Pipeline hasn't run yet. Upload CVs, configure the job, then run <code>python crew.py</code> and <code>python generate_dashboard.py</code>.
      </div>
      <div id="dash-has-results" style="display:none"></div>

      <div id="dash-loading" class="loading-state">Loading…</div>

      <div id="dash-content" style="display:none">
        <div class="stat-grid" id="dash-stats"></div>

        <div class="dash-tabs">
          <button class="dash-tab active" onclick="showDTab('dt-scoring',this)">Scoring</button>
          <button class="dash-tab" onclick="showDTab('dt-fit',this)">Job Fit</button>
          <button class="dash-tab" onclick="showDTab('dt-ranked',this)">Rankings</button>
          <button class="dash-tab" onclick="showDTab('dt-report',this)">Report</button>
        </div>

        <div id="dt-scoring" class="dpanel active"></div>
        <div id="dt-fit"     class="dpanel"></div>
        <div id="dt-ranked"  class="dpanel"></div>
        <div id="dt-report"  class="dpanel"></div>
      </div>
    </div>

  </main>
</div>

<div id="toast"></div>

<script>
let files = [];

// ── Nav ────────────────────────────────────────────────────
function show(id, btn) {
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
  document.getElementById('panel-' + id).classList.add('active');
  if (btn) btn.classList.add('active');
  if (id === 'candidates') loadCandidates();
  if (id === 'job') loadJobConfig();
  if (id === 'dashboard') loadDashboard();
}
function showDTab(id, btn) {
  document.querySelectorAll('.dpanel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.dash-tab').forEach(b => b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  if (btn) btn.classList.add('active');
}

// ── Toast ──────────────────────────────────────────────────
function toast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove('show'), 2800);
}

// ── Drop zone ──────────────────────────────────────────────
const dz = document.getElementById('dz');
const fi = document.getElementById('fi');
fi.addEventListener('change', e => { addFiles(Array.from(e.target.files)); fi.value = ''; });
dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('over'); });
dz.addEventListener('dragleave', () => dz.classList.remove('over'));
dz.addEventListener('drop', e => {
  e.preventDefault(); dz.classList.remove('over');
  addFiles(Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith('.pdf')));
});

function addFiles(newFiles) {
  newFiles.forEach(f => {
    if (f.name.toLowerCase().endsWith('.pdf') && !files.find(x => x.name === f.name)) files.push(f);
  });
  renderFiles();
}
function removeFile(i) { files.splice(i, 1); renderFiles(); }
function renderFiles() {
  const el = document.getElementById('fileList');
  document.getElementById('upBtn').disabled = files.length === 0;
  if (!files.length) { el.innerHTML = ''; return; }
  el.innerHTML = files.map((f, i) => `
    <div class="file-row">
      <span class="file-icon">📄</span>
      <span class="file-name">${f.name}</span>
      <span class="file-size">${(f.size/1024).toFixed(0)} KB</span>
      <button class="file-rm" onclick="removeFile(${i})">✕</button>
    </div>`).join('');
}

// ── Upload ─────────────────────────────────────────────────
async function doUpload() {
  if (!files.length) return;
  const btn = document.getElementById('upBtn');
  btn.disabled = true; btn.textContent = '⏳ Uploading…';
  const fd = new FormData();
  files.forEach(f => fd.append('cvs', f));
  try {
    const res = await fetch('/upload', { method: 'POST', body: fd });
    const d = await res.json();
    if (!res.ok) { toast(d.error || 'Upload failed'); return; }
    const el = document.getElementById('uploadResults');
    el.innerHTML = '';
    d.uploaded.forEach(u => {
      el.innerHTML += `<div class="result-item">
        <span>✅</span>
        <span class="result-name">${u.name}</span>
        <span style="font-family:var(--mono);font-size:10px;color:var(--muted)">${u.filename}</span>
        <span class="tag ${u.validation_passed ? 'tag-green' : 'tag-amber'}">${u.validation_passed ? 'Valid' : 'Issues'}</span>
      </div>`;
    });
    d.errors.forEach(e => {
      el.innerHTML += `<div class="result-item">
        <span>❌</span>
        <span class="result-name" style="color:var(--red);font-family:var(--mono);font-size:11px">${e}</span>
      </div>`;
    });
    files = [];
    document.getElementById('fileList').innerHTML = '';
    updateCount(d.total_candidates);
    updatePipelineStatus(d.total_candidates, false, false);
    toast(`${d.uploaded.length} CV(s) parsed ✓`);
  } catch (e) { toast('Error: ' + e.message); }
  finally { btn.disabled = false; btn.textContent = '⬆ Upload & Parse'; }
}

// ── Job config ─────────────────────────────────────────────
async function loadJobConfig() {
  try {
    const d = await (await fetch('/candidates')).json();
    const r = d.job_requirements || {};
    document.getElementById('reqSkills').value  = (r.required_skills  || []).join(', ');
    document.getElementById('prefSkills').value = (r.preferred_skills || []).join(', ');
    document.getElementById('minYears').value   = r.minimum_experience || '';
    document.getElementById('jobDesc').value    = d.job_description || '';
  } catch (e) {}
}
async function saveJob() {
  const body = {
    required_skills:    document.getElementById('reqSkills').value,
    preferred_skills:   document.getElementById('prefSkills').value,
    minimum_experience: document.getElementById('minYears').value,
    job_description:    document.getElementById('jobDesc').value,
  };
  const res = await fetch('/save-job', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
  const d = await res.json();
  document.getElementById('jobMsg').textContent = '✓ ' + d.message;
  toast('Job config saved ✓');
  setTimeout(() => document.getElementById('jobMsg').textContent = '', 3000);
}

// ── Candidates ─────────────────────────────────────────────
async function loadCandidates() {
  const d = await (await fetch('/candidates')).json();
  const list = d.candidates || [];
  document.getElementById('sc-total').textContent = list.length;
  document.getElementById('sc-valid').textContent = list.filter(c => c.validation_passed).length;
  document.getElementById('sc-email').textContent = list.filter(c => c.email).length;
  const withExp = list.filter(c => c.experience_years != null);
  document.getElementById('sc-exp').textContent = withExp.length
    ? (withExp.reduce((a,c) => a+c.experience_years, 0) / withExp.length).toFixed(1) : '—';

  const cl = document.getElementById('candList');
  if (!list.length) {
    cl.innerHTML = '<div class="empty"><div class="empty-icon">👤</div><div class="empty-txt">No candidates yet — upload CVs first.</div></div>';
    return;
  }
  const avC = ['av0','av1','av2','av3'];
  cl.innerHTML = list.map((c, i) => {
    const ini = (c.name||'?').split(' ').slice(0,2).map(w=>w[0]).join('').toUpperCase();
    return `<div class="cand-card">
      <div class="avatar ${avC[i%4]}">${ini}</div>
      <div>
        <div class="cand-name">${c.name||'Unknown'}</div>
        <div class="cand-meta">${c.email||'no email'} · ${c.experience_years!=null?c.experience_years+' yrs exp':'exp unknown'} · ${c.education||'—'}</div>
        <div class="skill-list">${(c.skills||[]).slice(0,10).map(s=>`<span class="skill-chip">${s}</span>`).join('')}</div>
        ${c.validation_notes&&c.validation_notes.length?`<div style="font-family:var(--mono);font-size:10px;color:var(--amber);margin-top:6px">⚠ ${c.validation_notes.join(', ')}</div>`:''}
      </div>
    </div>`;
  }).join('');
}

// ── Pipeline status ────────────────────────────────────────
function updatePipelineStatus(candidateCount, pipelineRan, hasResultsHtml) {
  const steps = {
    'ps-upload': candidateCount > 0,
    'ps-job':    false,
    'ps-crew':   pipelineRan,
    'ps-gen':    hasResultsHtml,
  };
  for (const [id, done] of Object.entries(steps)) {
    const el = document.getElementById(id);
    if (el) el.className = 'track-step' + (done ? ' done' : '');
  }
}

// ── Dashboard helpers ──────────────────────────────────────
const rbg = r => ({'Low':'var(--blue-bg)','Medium':'var(--amber-bg)','High':'var(--red-bg)'}[r]||'var(--surface2)');
const rtx = r => ({'Low':'var(--accent)','Medium':'var(--amber)','High':'var(--red)'}[r]||'var(--muted)');
const rbd = r => ({'Low':'var(--accent)','Medium':'var(--amber)','High':'var(--red)'}[r]||'var(--muted)');
const rbc = r => ({'Low':'var(--blue-dim)','Medium':'var(--amber-dim)','High':'var(--red-dim)'}[r]||'var(--border)');
const rec = r => ({'Low':'Shortlist','Medium':'Review','High':'Reject'}[r]||'—');
const rcc = r => ({'Low':'var(--green)','Medium':'var(--amber)','High':'var(--red)'}[r]||'var(--muted)');
const fbg = f => ({'Strong':'var(--green-bg)','Moderate':'var(--amber-bg)','Weak':'var(--red-bg)'}[f]||'var(--surface2)');
const ftx = f => ({'Strong':'var(--green)','Moderate':'var(--amber)','Weak':'var(--red)'}[f]||'var(--muted)');
const fbc = f => ({'Strong':'var(--green-dim)','Moderate':'var(--amber-dim)','Weak':'var(--red-dim)'}[f]||'var(--border)');
const medal = {1:'🥇',2:'🥈',3:'🥉'};

// ── Dashboard ──────────────────────────────────────────────
async function loadDashboard() {
  document.getElementById('dash-loading').style.display = 'block';
  document.getElementById('dash-content').style.display = 'none';
  document.getElementById('dash-not-run').style.display = 'none';
  document.getElementById('dash-has-results').style.display = 'none';

  try {
    const [stateRes, candRes] = await Promise.all([fetch('/dashboard-data'), fetch('/candidates')]);
    const d    = await stateRes.json();
    const cand = await candRes.json();

    document.getElementById('dash-loading').style.display = 'none';
    updatePipelineStatus(cand.total_candidates, d.pipeline_ran, d.has_results_html);

    if (!d.pipeline_ran) {
      document.getElementById('dash-not-run').style.display = 'block';
      return;
    }

    document.getElementById('dash-has-results').style.display = 'block';
    document.getElementById('dash-content').style.display = 'block';

    // Stats
    const scored = d.scored_candidates || [];
    const low  = scored.filter(c => c.risk_level === 'Low').length;
    const med  = scored.filter(c => c.risk_level === 'Medium').length;
    const high = scored.filter(c => c.risk_level === 'High').length;
    document.getElementById('dash-stats').innerHTML = `
      <div class="stat-card"><div class="stat-label">Scored</div><div class="stat-val" style="color:var(--accent)">${scored.length}</div></div>
      <div class="stat-card" style="border-color:var(--blue-dim)"><div class="stat-label" style="color:var(--accent)">Low Risk</div><div class="stat-val" style="color:var(--accent)">${low}</div></div>
      <div class="stat-card" style="border-color:var(--amber-dim)"><div class="stat-label" style="color:var(--amber)">Medium Risk</div><div class="stat-val" style="color:var(--amber)">${med}</div></div>
      <div class="stat-card" style="border-color:var(--red-dim)"><div class="stat-label" style="color:var(--red)">High Risk</div><div class="stat-val" style="color:var(--red)">${high}</div></div>
    `;

    // Scoring tab
    const sortedScored = [...scored].sort((a,b) => b.final_score - a.final_score);
    document.getElementById('dt-scoring').innerHTML = sortedScored.length
      ? sortedScored.map((c,i) => {
          const ini = c.candidate_name.split(' ').slice(0,2).map(w=>w[0]).join('').toUpperCase();
          const flags = (c.risk_flags||[]).map(f=>`<div class="flag-line" style="color:var(--red)">⚠ ${f}</div>`).join('')
                     || `<div class="flag-line" style="color:var(--green)">✓ No risk flags</div>`;
          const adj = parseFloat(c.score_adjustment||0);
          const adjHtml = adj>0?`<span style="color:var(--green)">+${adj}</span>`:adj<0?`<span style="color:var(--red)">${adj}</span>`:`<span style="color:var(--muted)">±0</span>`;
          return `<div class="score-card ${i===0?'top':''}">
            <div class="avatar" style="background:${rbg(c.risk_level)};color:${rtx(c.risk_level)};border-radius:8px;width:40px;height:40px;font-size:12px">${ini}</div>
            <div>
              <div><span class="score-name">${c.candidate_name}</span><span class="score-rank">#${i+1}</span></div>
              <span class="risk-badge" style="background:${rbg(c.risk_level)};color:${rtx(c.risk_level)};border:1px solid ${rbc(c.risk_level)}">${c.risk_level} risk</span>
              ${flags}
              <div class="score-reasoning">${c.score_reasoning||'—'}</div>
            </div>
            <div>
              <div class="score-num" style="color:${rtx(c.risk_level)}">${Math.round(c.final_score)}</div>
              <div class="score-lbl">base ${c.base_score_used||'—'}</div>
              <div class="score-adj">${adjHtml} adj</div>
              <div class="score-bar"><div class="score-bar-fill" style="width:${Math.min(c.final_score,100)}%;background:${rbd(c.risk_level)}"></div></div>
            </div>
          </div>`;
        }).join('')
      : '<div class="empty"><div class="empty-icon">📊</div><div class="empty-txt">No scoring data yet.</div></div>';

    // Fit tab
    const fit = d.fit_results || [];
    if (!fit.length) {
      document.getElementById('dt-fit').innerHTML = '<div class="empty"><div class="empty-icon">🎯</div><div class="empty-txt">No fit analysis data yet.</div></div>';
    } else {
      const strong   = fit.filter(f => f.fit_level === 'Strong').length;
      const moderate = fit.filter(f => f.fit_level === 'Moderate').length;
      const weak     = fit.filter(f => f.fit_level === 'Weak').length;
      document.getElementById('dt-fit').innerHTML = `
        <div class="fit-summary">
          <div class="fit-stat" style="background:var(--green-bg);border:1px solid var(--green-dim)">
            <div class="fit-stat-label" style="color:var(--green)">Strong</div>
            <div class="fit-stat-num" style="color:var(--green)">${strong}</div>
          </div>
          <div class="fit-stat" style="background:var(--amber-bg);border:1px solid var(--amber-dim)">
            <div class="fit-stat-label" style="color:var(--amber)">Moderate</div>
            <div class="fit-stat-num" style="color:var(--amber)">${moderate}</div>
          </div>
          <div class="fit-stat" style="background:var(--red-bg);border:1px solid var(--red-dim)">
            <div class="fit-stat-label" style="color:var(--red)">Weak</div>
            <div class="fit-stat-num" style="color:var(--red)">${weak}</div>
          </div>
        </div>
        ${fit.map(f => {
          const ini = (f.candidate_name||'?').split(' ').slice(0,2).map(w=>w[0]).join('').toUpperCase();
          const mkTags = (arr, cls, pre) => arr&&arr.length
            ? arr.map(s=>`<span class="tag ${cls}">${pre} ${s}</span>`).join('')
            : `<span style="font-size:10px;color:var(--dim)">—</span>`;
          return `<div class="fit-card">
            <div class="fit-card-grid">
              <div class="avatar" style="background:${fbg(f.fit_level)};color:${ftx(f.fit_level)};border-radius:8px;width:38px;height:38px;font-size:12px">${ini}</div>
              <div>
                <div style="font-size:13px;font-weight:600;margin-bottom:8px">${f.candidate_name}</div>
                <div style="margin-bottom:6px"><div style="font-family:var(--mono);font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:3px">Matched</div>${mkTags(f.matched_skills,'tag-green','✓')}</div>
                <div style="margin-bottom:6px"><div style="font-family:var(--mono);font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:3px">Partial</div>${mkTags(f.partial_matches,'tag-amber','~')}</div>
                <div style="margin-bottom:8px"><div style="font-family:var(--mono);font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:3px">Missing</div>${mkTags(f.missing_critical_skills,'tag-red','✕')}</div>
                <div style="display:flex;gap:5px;margin-bottom:8px">
                  <span class="tag tag-blue">Exp: ${f.experience_fit||'—'}</span>
                  <span class="tag tag-blue">Edu: ${f.education_fit||'—'}</span>
                </div>
                <div style="font-size:11px;color:var(--muted);padding-top:8px;border-top:1px solid var(--border);line-height:1.6">${f.fit_reasoning||'—'}</div>
              </div>
              <div>
                <span class="risk-badge" style="background:${fbg(f.fit_level)};color:${ftx(f.fit_level)};border:1px solid ${fbc(f.fit_level)}">${f.fit_level}</span>
              </div>
            </div>
          </div>`;
        }).join('')}`;
    }

    // Rankings tab
    const ranked = d.ranked_candidates || [];
    const shortlisted = d.shortlisted_candidates || [];
    const shortNames = new Set(shortlisted.map(s => s.name));
    if (!ranked.length) {
      document.getElementById('dt-ranked').innerHTML = '<div class="empty"><div class="empty-icon">🏆</div><div class="empty-txt">No ranking data yet.</div></div>';
    } else {
      const shortCards = shortlisted.map(c => {
        const ini = (c.name||'?').split(' ').slice(0,2).map(w=>w[0]).join('').toUpperCase();
        return `<div style="background:var(--surface);border:1px solid var(--blue-dim);border-left:2px solid var(--accent);border-radius:0 8px 8px 0;padding:12px 14px;margin-bottom:7px;display:flex;align-items:center;gap:12px">
          <span style="font-size:18px;min-width:26px;text-align:center">${medal[c.rank]||'#'+c.rank}</span>
          <div class="avatar" style="background:${rbg(c.risk_level)};color:${rtx(c.risk_level)};border-radius:8px;width:34px;height:34px;font-size:11px;flex-shrink:0">${ini}</div>
          <div style="flex:1">
            <div style="font-size:13px;font-weight:600">${c.name}</div>
            <div style="font-family:var(--mono);font-size:10px;color:var(--muted);margin-top:1px">Rank #${c.rank} · <span style="color:${rtx(c.risk_level)}">${c.risk_level} risk</span></div>
          </div>
          <div style="font-family:var(--display);font-size:24px;font-weight:700;color:var(--accent)">${c.score}</div>
        </div>`;
      }).join('') || '<div style="color:var(--muted);font-family:var(--mono);font-size:11px;padding:8px">No shortlisted candidates.</div>';

      document.getElementById('dt-ranked').innerHTML = `
        <div class="section-heading" style="margin-bottom:10px">✅ Shortlisted</div>
        <div style="margin-bottom:20px">${shortCards}</div>
        <div class="section-heading" style="margin-bottom:10px">🏆 Full Rankings</div>
        <table class="ranked-table">
          <thead><tr>
            <th style="width:50px">Rank</th>
            <th>Candidate</th>
            <th style="text-align:center;width:80px">Score</th>
            <th style="text-align:center;width:80px">Risk</th>
            <th style="text-align:center;width:90px">Decision</th>
          </tr></thead>
          <tbody>
            ${ranked.map(c => {
              const isShort = shortNames.has(c.name);
              const badge = isShort ? `<span class="tag tag-green" style="margin-left:6px">Shortlisted</span>` : '';
              return `<tr>
                <td style="text-align:center;font-size:15px">${medal[c.rank]||'#'+c.rank}</td>
                <td style="font-weight:600">${c.name}${badge}</td>
                <td style="text-align:center;font-family:var(--display);font-size:16px;font-weight:700;color:var(--accent)">${c.score}</td>
                <td style="text-align:center"><span class="risk-badge" style="background:${rbg(c.risk_level)};color:${rtx(c.risk_level)};border:1px solid ${rbc(c.risk_level)}">${c.risk_level}</span></td>
                <td style="text-align:center;font-family:var(--mono);font-size:10px;font-weight:600;color:${rcc(c.risk_level)}">${rec(c.risk_level)}</td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      `;
    }

    // Report tab
    const report = d.final_report || '';
    const meta   = d.report_metadata || {};
    if (!report) {
      document.getElementById('dt-report').innerHTML = '<div class="empty"><div class="empty-icon">📄</div><div class="empty-txt">No report generated yet.</div></div>';
    } else {
      let display = report
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/^### (.+)$/gm, '<h4 style="font-size:12px;color:var(--accent);margin:10px 0 4px">$1</h4>')
        .replace(/^## (.+)$/gm,  '<h3 style="font-size:13px;color:var(--text);margin:12px 0 5px">$1</h3>')
        .replace(/^# (.+)$/gm,   '<h2 style="font-size:14px;color:var(--text);margin:14px 0 6px">$1</h2>')
        .replace(/^\s*[-*] (.+)$/gm, '<li style="margin:2px 0 2px 16px;font-size:11px;color:#a0a8c0">$1</li>')
        .split('\n').map(line => {
          const s = line.trim();
          if (!s) return '<div style="height:5px"></div>';
          if (s.startsWith('<')) return s;
          return `<p style="font-size:12px;color:#a0a8c0;margin:2px 0;line-height:1.7">${s}</p>`;
        }).join('\n');

      const metaHtml = Object.keys(meta).length
        ? `<div class="meta-strip">${Object.entries(meta).map(([k,v])=>
            `<span style="color:var(--accent)">${k.replace(/_/g,' ')}: </span>${v}`).join(' · ')}</div>` : '';

      document.getElementById('dt-report').innerHTML = `
        <div class="report-box">
          <div class="report-title">Final Screening Report</div>
          <div class="report-content">${display}</div>
        </div>
        ${metaHtml}
      `;
    }

  } catch (e) {
    document.getElementById('dash-loading').style.display = 'none';
    document.getElementById('dash-not-run').style.display = 'block';
    document.getElementById('dash-not-run').textContent = '⚠ Error loading dashboard: ' + e.message;
  }
}

// ── Clear ──────────────────────────────────────────────────
async function doClear() {
  if (!confirm('Clear all candidates and pipeline state?')) return;
  const d = await (await fetch('/clear', { method: 'POST' })).json();
  toast(d.message);
  files = [];
  document.getElementById('fileList').innerHTML = '';
  document.getElementById('uploadResults').innerHTML = '';
  document.getElementById('upBtn').disabled = true;
  updateCount(0);
  updatePipelineStatus(0, false, false);
}

// ── Utilities ──────────────────────────────────────────────
function updateCount(n) {
  document.getElementById('sb-count').textContent = n;
  document.getElementById('top-count-num').textContent = n;
}

// ── Init ───────────────────────────────────────────────────
(async () => {
  try {
    const d = await (await fetch('/candidates')).json();
    updateCount(d.total_candidates || 0);
    const dd = await (await fetch('/dashboard-data')).json();
    updatePipelineStatus(d.total_candidates || 0, dd.pipeline_ran, dd.has_results_html);
    if (!dd.has_results_html) {
      document.getElementById('open-results-btn').style.opacity = '0.4';
    }
  } catch (e) {}
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    print("=" * 55)
    print("  CV Screening Dashboard  →  http://localhost:5000")
    print("=" * 55)
    app.run(debug=True, port=5000)