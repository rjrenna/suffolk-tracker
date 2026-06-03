#!/usr/bin/env python3
"""
Suffolk County Legislature Resolution Scraper
Fetches marked agenda PDFs, parses IR#, Res#, status, sponsor, description.
Runs via GitHub Actions every Sunday. Outputs data/resolutions.json
"""

import json
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# ── KNOWN DOCUMENTS ──────────────────────────────────────────────────────────
# Add new meetings here as they are published on scnylegislature.us
DOCUMENTS = [
    {
        "session": "Jan 5, 2026",
        "type": "Organizational Meeting",
        "lot_url": "https://www.scnylegislature.us/DocumentCenter/View/126663/01052026-Laid-on-the-Table-Resolutions-PDF",
        "agenda_url": None,
        "minutes_url": "https://www.scnylegislature.us/DocumentCenter/View/127567/01052026-Organizational-Meeting-Minutes-PDF",
        "packet_url": "https://www.scnylegislature.us/DocumentCenter/View/126662/01052026-Organizational-Meeting-Resolution-Packet-PDF",
        "action_url": None,
        "absent": [],
    },
    {
        "session": "Feb 3, 2026",
        "type": "General Meeting",
        "lot_url": "https://www.scnylegislature.us/DocumentCenter/View/127573/02032026-Laid-on-the-Table-Resolutions-PDF",
        "agenda_url": "https://www.scnylegislature.us/DocumentCenter/View/127636/02032026-General-Meeting-Marked-Agenda-PDF",
        "minutes_url": "https://www.scnylegislature.us/DocumentCenter/View/127979/02032026-General-Meeting-Minutes-PDF",
        "packet_url": "https://www.scnylegislature.us/DocumentCenter/View/127574/02032026-General-Meeting-Resolution-Packet-PDF",
        "action_url": "https://www.scnylegislature.us/DocumentCenter/View/127659/02032026-Action-Report-PDF",
        "absent": ["richberg", "gonzalez", "kennedy"],
    },
    {
        "session": "Mar 10, 2026",
        "type": "General Meeting",
        "lot_url": "https://www.scnylegislature.us/DocumentCenter/View/127984/03102026-Laid-on-the-Table-Resolutions-PDF",
        "agenda_url": "https://www.scnylegislature.us/DocumentCenter/View/128172/03102026-General-Meeting-Marked-Agenda-PDF",
        "minutes_url": "https://www.scnylegislature.us/DocumentCenter/View/128621/03102026-General-Meeting-Minutes-PDF",
        "packet_url": "https://www.scnylegislature.us/DocumentCenter/View/127983/03102026-General-Meeting-Resolution-Packet-PDF",
        "action_url": "https://www.scnylegislature.us/DocumentCenter/View/128168/03102026-Action-Report-PDF",
        "absent": [],
    },
    {
        "session": "Apr 21, 2026",
        "type": "General Meeting",
        "lot_url": None,
        "agenda_url": "https://www.scnylegislature.us/DocumentCenter/View/128778/04212026-General-Meeting-Marked-Agenda-PDF",
        "minutes_url": None,
        "packet_url": "https://www.scnylegislature.us/DocumentCenter/View/128633/04212026-General-Meeting-Resolution-Packet-PDF",
        "action_url": "https://www.scnylegislature.us/DocumentCenter/View/128789/04212026-Action-Report-PDF",
        "absent": [],
    },
    {
        "session": "May 12, 2026",
        "type": "General Meeting",
        "lot_url": None,
        "agenda_url": None,
        "minutes_url": None,
        "packet_url": None,
        "action_url": "https://www.scnylegislature.us/DocumentCenter/View/129295/05122026-Action-Report-PDF",
        "absent": [],
    },
]

# ── MEETINGS INDEX PAGE — checked for new documents ──────────────────────────
MEETINGS_INDEX_URL = "https://www.scnylegislature.us/765/General-Meetings-Agendas-Minutes"

# ── LEGISLATOR IDs ───────────────────────────────────────────────────────────
ALL_LEG_IDS = [
    "doroski","welker","mazzarella","caracappa","englebright","lennon",
    "thorne","piccirillo","gonzalez","bergin","flotteron","kennedy",
    "formica","renna","richberg","sanin","donnelly","bontempi",
]

# ── STATUS MAPPING from marked agenda codes ──────────────────────────────────
STATUS_MAP = {
    "A": "Adopted",
    "T": "Tabled",
    "F": "Failed",
    "W": "Withdrawn",
    "TSC": "Tabled Subject to Call",
    "SC": "Sent to Committee",
    "X": "No Action",
    "S": "Status",
    "CC": "Consent Calendar",
}

# ── KNOWN SPONSOR KEYWORDS → legislator IDs ──────────────────────────────────
SPONSOR_ALIASES = {
    "doroski": ["doroski"],
    "welker": ["welker"],
    "mazzarella": ["mazzarella"],
    "caracappa": ["caracappa"],
    "englebright": ["englebright"],
    "lennon": ["lennon"],
    "thorne": ["thorne"],
    "piccirillo": ["piccirillo", "pres. off", "presiding off"],
    "gonzalez": ["gonzalez"],
    "bergin": ["bergin"],
    "flotteron": ["flotteron"],
    "kennedy": ["kennedy"],
    "formica": ["formica"],
    "renna": ["renna"],
    "richberg": ["richberg"],
    "sanin": ["sanin"],
    "donnelly": ["donnelly"],
    "bontempi": ["bontempi"],
}

def fetch_pdf_text(url):
    """Download a PDF and extract its text using pdfplumber."""
    try:
        import pdfplumber
        import io
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            pdf_bytes = resp.read()
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        return text
    except Exception as e:
        print(f"  WARNING: Could not fetch/parse {url}: {e}", file=sys.stderr)
        return ""

def fetch_page_html(url):
    """Fetch HTML page text."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  WARNING: Could not fetch {url}: {e}", file=sys.stderr)
        return ""

def detect_new_meetings(existing_sessions):
    """Check the meetings index page for document URLs not yet in our list."""
    print("Checking meetings index for new documents...")
    html = fetch_page_html(MEETINGS_INDEX_URL)
    new_urls = []
    # Look for marked agenda and LOT PDF links
    pattern = r'href="(https://www\.scnylegislature\.us/DocumentCenter/View/\d+/[^"]+(?:Marked-Agenda|Laid-on-the-Table)[^"]*)"'
    found = re.findall(pattern, html, re.IGNORECASE)
    for url in found:
        # Extract date from filename like 05122026-General-Meeting-Marked-Agenda-PDF
        date_match = re.search(r'(\d{2})(\d{2})(\d{4})', url)
        if date_match:
            month, day, year = date_match.groups()
            label = f"{['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][int(month)]} {int(day)}, {year}"
            if label not in existing_sessions:
                new_urls.append({"label": label, "url": url})
                print(f"  Found new document: {label} — {url}")
    return new_urls

def parse_marked_agenda(text, session_label, lot_url, agenda_url):
    """
    Parse a marked agenda PDF text to extract:
    IR#, Status (A/T/F/etc), Res#, Description, Sponsor, Committee
    
    The marked agenda format is:
    IR#  S  RES#
    1045 A  94   Description text... (Sponsor)
    """
    resolutions = []
    
    # Pattern: IR number, status code, optional res number, then description
    # Matches lines like: "1045 A 94" or "1058 T" or "PM04. C"
    ir_pattern = re.compile(
        r'^((?:PM\d+\.?|\d{3,4}))\s+'   # IR number (e.g. 1045, PM04)
        r'([A-Z]{1,3})\s*'               # Status code (A, T, F, TSC, SC, etc)
        r'(\d+)?\s*$',                   # Optional Res# 
        re.MULTILINE
    )
    
    # Also look for lines with descriptions following IR# lines
    lines = text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Match IR# status [res#] pattern
        m = ir_pattern.match(line)
        if m:
            ir_num = m.group(1).rstrip('.')
            status_code = m.group(2)
            res_num = m.group(3)
            
            # Collect description from following lines until next IR# or section header
            desc_lines = []
            j = i + 1
            while j < len(lines) and j < i + 8:
                next_line = lines[j].strip()
                if not next_line:
                    j += 1
                    continue
                if ir_pattern.match(next_line):
                    break
                if re.match(r'^[•\*]|^TITLE$|^IR#|^\d{4}\s+[A-Z]', next_line):
                    break
                desc_lines.append(next_line)
                j += 1
            
            desc = " ".join(desc_lines).strip()
            
            # Extract sponsor from parentheses at end: "(Co. Exec.)" or "(Lennon)"
            sponsor = "Co. Exec."
            sponsor_match = re.search(r'\(([^)]+)\)\s*$', desc)
            if sponsor_match:
                sponsor = sponsor_match.group(1).strip()
                desc = desc[:sponsor_match.start()].strip()
            
            # Extract committee (often appears after sponsor in caps)
            committee = extract_committee(desc + " " + (sponsor_match.group(0) if sponsor_match else ""))
            
            # Map status
            status = STATUS_MAP.get(status_code, status_code)
            
            # Extract CP numbers
            cp_nums = re.findall(r'CP\s*(\d{3,4}(?:\.\d+)*)', desc, re.IGNORECASE)
            
            # Determine type
            res_type = "lot"
            if ir_num.startswith("PM"):
                res_type = "pm"
            elif "local law" in desc.lower() or "adopt local law" in desc.lower():
                res_type = "ll"
            
            if desc and ir_num:
                resolutions.append({
                    "ir": ir_num,
                    "resNum": res_num,
                    "type": res_type,
                    "session": session_label,
                    "desc": desc,
                    "sponsor": sponsor,
                    "committee": committee,
                    "status": status,
                    "cp": cp_nums if cp_nums else None,
                    "sourceUrl": agenda_url or lot_url,
                })
        i += 1
    
    return resolutions

def extract_committee(text):
    """Infer committee from description keywords."""
    text_lower = text.lower()
    if any(k in text_lower for k in ["budget", "finance", "appropriat", "fund transfer", "operating budget"]):
        return "Budget & Finance"
    if any(k in text_lower for k in ["public safety", "police", "sheriff", "jail", "correctional", "district attorney", "fire arm"]):
        return "Public Safety"
    if any(k in text_lower for k in ["park", "farmland", "environment", "ecology", "wetland", "agriculture", "golf course", "marina"]):
        return "Environment, Parks & Agriculture"
    if any(k in text_lower for k in ["road", "highway", "bridge", "transit", "bus", "transportation", "sewer", "drainage", "airport"]):
        return "Public Works, Transportation & Energy"
    if any(k in text_lower for k in ["economic", "housing", "affordable", "workforce", "industrial", "waterfront", "development"]):
        return "Economic Dev, Planning & Housing"
    if any(k in text_lower for k in ["health", "mental", "substance", "addiction", "medical", "nursing", "hospital"]):
        return "Health"
    if any(k in text_lower for k in ["senior", "aging", "youth", "human service", "nutrition"]):
        return "Seniors & Human Services"
    if any(k in text_lower for k in ["veteran", "military"]):
        return "Veterans"
    if any(k in text_lower for k in ["education", "labor", "consumer", "diversity", "human rights", "licensing board"]):
        return "Education, Labor, Consumer Affairs"
    if any(k in text_lower for k in ["fire", "rescue", "ems", "emergency service", "hazmat", "aed"]):
        return "Fire, Rescue & EMS"
    if any(k in text_lower for k in ["technology", "personnel", "classification", "salary", "information tech", "software", "network", "computer"]):
        return "Govt Operations, Info Tech"
    if any(k in text_lower for k in ["sale", "conveyance", "tax act", "mortgage", "county clerk", "comptroller", "insurance", "settlement", "reconveyance"]):
        return "Ways & Means"
    return "General"

def build_votes(session_doc, status):
    """Build vote object based on attendance and status."""
    if status not in ("Adopted", "Tabled", "Failed"):
        return None
    votes = {leg: "Y" for leg in ALL_LEG_IDS}
    for absent_id in session_doc.get("absent", []):
        if absent_id in votes:
            votes[absent_id] = "NP"
    # If tabled, votes still show who was present (they voted to table)
    return votes

def load_existing_data(output_path):
    """Load existing resolutions.json to merge with new data."""
    try:
        with open(output_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"resolutions": [], "meetings": [], "lastUpdated": None}

def scrape_all():
    output_path = Path(__file__).parent.parent / "data" / "resolutions.json"
    output_path.parent.mkdir(exist_ok=True)
    
    existing = load_existing_data(output_path)
    existing_irs = {r["ir"] for r in existing.get("resolutions", [])}
    existing_sessions = {m["label"] for m in existing.get("meetings", [])}
    
    all_resolutions = list(existing.get("resolutions", []))
    meetings_meta = []
    
    # Check for new meetings on the index page
    new_docs = detect_new_meetings(existing_sessions)
    
    for doc in DOCUMENTS:
        session = doc["session"]
        print(f"\nProcessing: {session}")
        
        # Build meeting metadata
        meeting_entry = {
            "label": session,
            "type": doc["type"],
            "docs": []
        }
        for key, label in [("lot_url","LOT Resolutions"),("agenda_url","Marked Agenda"),
                            ("minutes_url","Minutes"),("packet_url","Resolution Packet"),
                            ("action_url","Action Report")]:
            if doc.get(key):
                meeting_entry["docs"].append({"name": label, "url": doc[key]})
        meetings_meta.append(meeting_entry)
        
        # Parse marked agenda for vote/status data
        if doc.get("agenda_url"):
            print(f"  Parsing marked agenda...")
            text = fetch_pdf_text(doc["agenda_url"])
            if text:
                parsed = parse_marked_agenda(text, session, doc.get("lot_url"), doc["agenda_url"])
                print(f"  Found {len(parsed)} resolutions in agenda")
                for r in parsed:
                    if r["ir"] not in existing_irs:
                        r["votes"] = build_votes(doc, r["status"])
                        all_resolutions.append(r)
                        existing_irs.add(r["ir"])
                    else:
                        # Update status if it changed (e.g. went from Pending to Adopted)
                        for existing_r in all_resolutions:
                            if existing_r["ir"] == r["ir"] and existing_r["status"] != r["status"]:
                                existing_r["status"] = r["status"]
                                existing_r["resNum"] = r["resNum"] or existing_r.get("resNum")
                                existing_r["votes"] = build_votes(doc, r["status"])
                                print(f"  Updated {r['ir']}: {r['status']}")
        
        # Parse LOT PDF for newly introduced resolutions
        if doc.get("lot_url"):
            print(f"  Parsing LOT resolutions...")
            text = fetch_pdf_text(doc["lot_url"])
            if text:
                parsed = parse_marked_agenda(text, session, doc["lot_url"], doc.get("agenda_url"))
                new_count = 0
                for r in parsed:
                    if r["ir"] not in existing_irs:
                        r["status"] = r.get("status", "Pending")
                        r["votes"] = None
                        all_resolutions.append(r)
                        existing_irs.add(r["ir"])
                        new_count += 1
                print(f"  Added {new_count} new LOT resolutions")
    
    # Sort resolutions by session order then IR number
    session_order = [d["session"] for d in DOCUMENTS]
    def sort_key(r):
        try:
            session_idx = session_order.index(r.get("session", ""))
        except ValueError:
            session_idx = 99
        ir = r.get("ir", "")
        ir_num = int(re.sub(r'\D', '', ir) or 0)
        return (session_idx, ir_num)
    
    all_resolutions.sort(key=sort_key)
    
    # Build output
    output = {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "totalResolutions": len(all_resolutions),
        "meetings": meetings_meta,
        "resolutions": all_resolutions,
    }
    
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✓ Saved {len(all_resolutions)} resolutions to {output_path}")
    return output

if __name__ == "__main__":
    scrape_all()
