import json, re, sys
from datetime import datetime, timezone
from pathlib import Path

DOCS = [
    {"session":"Jan 5, 2026","lot":"https://www.scnylegislature.us/DocumentCenter/View/126663/01052026-Laid-on-the-Table-Resolutions-PDF","agenda":None,"absent":[]},
    {"session":"Feb 3, 2026","lot":"https://www.scnylegislature.us/DocumentCenter/View/127573/02032026-Laid-on-the-Table-Resolutions-PDF","agenda":"https://www.scnylegislature.us/DocumentCenter/View/127636/02032026-General-Meeting-Marked-Agenda-PDF","absent":["richberg","gonzalez","kennedy"]},
    {"session":"Mar 10, 2026","lot":"https://www.scnylegislature.us/DocumentCenter/View/127984/03102026-Laid-on-the-Table-Resolutions-PDF","agenda":"https://www.scnylegislature.us/DocumentCenter/View/128172/03102026-General-Meeting-Marked-Agenda-PDF","absent":[]},
    {"session":"Apr 21, 2026","lot":None,"agenda":"https://www.scnylegislature.us/DocumentCenter/View/128778/04212026-General-Meeting-Marked-Agenda-PDF","absent":[]},
    {"session":"May 12, 2026","lot":None,"agenda":None,"absent":[]},
]

ALL_LEGS = ["doroski","welker","mazzarella","caracappa","englebright","lennon","thorne","piccirillo","gonzalez","bergin","flotteron","kennedy","formica","renna","richberg","sanin","donnelly","bontempi"]

MEETINGS_META = [
    {"label":"Jan 5, 2026","type":"Organizational Meeting","docs":[{"name":"LOT Resolutions","url":"https://www.scnylegislature.us/DocumentCenter/View/126663/01052026-Laid-on-the-Table-Resolutions-PDF"},{"name":"Minutes","url":"https://www.scnylegislature.us/DocumentCenter/View/127567/01052026-Organizational-Meeting-Minutes-PDF"}]},
    {"label":"Feb 3, 2026","type":"General Meeting","docs":[{"name":"Minutes","url":"https://www.scnylegislature.us/DocumentCenter/View/127979/02032026-General-Meeting-Minutes-PDF"},{"name":"Marked Agenda","url":"https://www.scnylegislature.us/DocumentCenter/View/127636/02032026-General-Meeting-Marked-Agenda-PDF"},{"name":"LOT Resolutions","url":"https://www.scnylegislature.us/DocumentCenter/View/127573/02032026-Laid-on-the-Table-Resolutions-PDF"},{"name":"Action Report","url":"https://www.scnylegislature.us/DocumentCenter/View/127659/02032026-Action-Report-PDF"}]},
    {"label":"Mar 10, 2026","type":"General Meeting","docs":[{"name":"Minutes","url":"https://www.scnylegislature.us/DocumentCenter/View/128621/03102026-General-Meeting-Minutes-PDF"},{"name":"Marked Agenda","url":"https://www.scnylegislature.us/DocumentCenter/View/128172/03102026-General-Meeting-Marked-Agenda-PDF"},{"name":"LOT Resolutions","url":"https://www.scnylegislature.us/DocumentCenter/View/127984/03102026-Laid-on-the-Table-Resolutions-PDF"},{"name":"Action Report","url":"https://www.scnylegislature.us/DocumentCenter/View/128168/03102026-Action-Report-PDF"}]},
    {"label":"Apr 21, 2026","type":"General Meeting","docs":[{"name":"Marked Agenda","url":"https://www.scnylegislature.us/DocumentCenter/View/128778/04212026-General-Meeting-Marked-Agenda-PDF"},{"name":"Resolution Packet","url":"https://www.scnylegislature.us/DocumentCenter/View/128633/04212026-General-Meeting-Resolution-Packet-PDF"},{"name":"Action Report","url":"https://www.scnylegislature.us/DocumentCenter/View/128789/04212026-Action-Report-PDF"}]},
    {"label":"May 12, 2026","type":"General Meeting","docs":[{"name":"Action Report","url":"https://www.scnylegislature.us/DocumentCenter/View/129295/05122026-Action-Report-PDF"}]},
]

def fetch_pdf(url):
    try:
        import pdfplumber, io, urllib.request
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text(layout=True)
                if text:
                    pages.append(text)
            return "\n".join(pages)
    except Exception as e:
        print(f"  WARNING: {url}: {e}", file=sys.stderr)
        return ""

def get_committee(desc):
    d = desc.lower()
    if any(k in d for k in ["police","sheriff","jail","correctional","district attorney","probation","firearm"]): return "Public Safety"
    if any(k in d for k in ["park","farmland","environment","wetland","agriculture","golf course","marina","open space","drinking water"]): return "Environment, Parks & Agriculture"
    if any(k in d for k in ["road","highway","bridge","transit","bus","transportation","sewer","drainage","airport","ferry"]): return "Public Works, Transportation & Energy"
    if any(k in d for k in ["housing","affordable","workforce","economic","industrial","waterfront","development","planning","jumpstart"]): return "Economic Dev, Planning & Housing"
    if any(k in d for k in ["health","mental","substance","addiction","medical","nursing","hospital","clinic","wic","oasas"]): return "Health"
    if any(k in d for k in ["senior","aging","youth","human service","nutrition"]): return "Seniors & Human Services"
    if any(k in d for k in ["veteran","military"]): return "Veterans"
    if any(k in d for k in ["education","labor","consumer","human rights","licensing board","college"]): return "Education, Labor, Consumer Affairs"
    if any(k in d for k in ["fire","rescue","ems","emergency service","aed","hazmat"]): return "Fire, Rescue & EMS"
    if any(k in d for k in ["technology","personnel","salary","software","network","computer","information tech","payroll"]): return "Govt Operations, Info Tech"
    if any(k in d for k in ["budget","finance","appropriat","fund transfer","operating budget","capital budget","refund","chargeback"]): return "Budget & Finance"
    if any(k in d for k in ["sale","conveyance","tax","mortgage","comptroller","insurance","settlement","reconveyance","clerk"]): return "Ways & Means"
    return "General"

def is_junk_line(line):
    """Return True if line is a page header, footer, or other non-description content."""
    line = line.strip()
    if not line:
        return True
    # Pure numbers (resolution numbers listed separately)
    if re.match(r'^\d+$', line):
        return True
    # Page numbers like "Page 1 of 12"
    if re.match(r'^Page \d+', line, re.I):
        return True
    # Date headers
    if re.match(r'^\d{1,2}/\d{1,2}/\d{4}', line):
        return True
    # Short lines that are just labels
    if len(line) < 8:
        return True
    # Lines that are just "TITLE" or "SPONSOR" labels
    if line.upper() in ["TITLE","SPONSOR","COMMITTEE","STATUS","IR#","RES#","RESOLUTION","MOTION"]:
        return True
    # Agenda header lines
    if any(x in line for x in ["Suffolk County Legislature","General Meeting","Organizational Meeting","Laid on the Table","LAID ON THE TABLE","GENERAL MEETING"]):
        return True
    return False

def parse_lot_pdf(text, session, url):
    """
    Parse a Laid-on-Table PDF. Format is typically:
    IR 1045
    Title: Amend the 2026 Operating Budget...
    Sponsor: Formica
    Committee: Budget & Finance
    """
    results = []
    # Join all text and split into blocks by IR number
    # Look for patterns like "IR 1045" or just "1045" at start of line
    blocks = re.split(r'\n(?=(?:IR\s+)?(?:PM\s*)?\d{3,4}\b)', text)

    ir_header = re.compile(r'^(?:IR\s+)?(PM\s*\d+|\d{3,4})\b', re.IGNORECASE)

    for block in blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        if not lines:
            continue

        # First line should have the IR number
        m = ir_header.match(lines[0])
        if not m:
            continue

        ir = m.group(1).replace(' ', '').upper()
        if ir.startswith('PM'):
            ir = 'PM' + ir[2:].lstrip('0') if ir[2:].lstrip('0') else 'PM0'
            rtype = 'pm'
        else:
            ir = ir.lstrip('0') or '0'
            rtype = 'lot'

        # Collect description lines - skip junk
        desc_lines = []
        sponsor = "Co. Exec."
        committee = ""

        for line in lines[1:]:
            if is_junk_line(line):
                continue
            # Check for labeled fields
            if re.match(r'^(?:Sponsor|Introduced by|By):\s*', line, re.I):
                sponsor = re.sub(r'^(?:Sponsor|Introduced by|By):\s*', '', line, flags=re.I).strip()
                continue
            if re.match(r'^Committee:\s*', line, re.I):
                committee = re.sub(r'^Committee:\s*', '', line, flags=re.I).strip()
                continue
            if re.match(r'^(?:Title|Description|Subject):\s*', line, re.I):
                line = re.sub(r'^(?:Title|Description|Subject):\s*', '', line, flags=re.I).strip()
            # Stop if we hit another IR number
            if ir_header.match(line):
                break
            if len(desc_lines) < 8:
                desc_lines.append(line)

        desc = ' '.join(desc_lines).strip()

        # Extract sponsor from end of description if in parens
        if not sponsor or sponsor == "Co. Exec.":
            sm = re.search(r'\(([^)]{3,40})\)\s*$', desc)
            if sm:
                potential_sponsor = sm.group(1).strip()
                # Only use if it looks like a name/office not a legal reference
                if not any(c.isdigit() for c in potential_sponsor) and len(potential_sponsor) < 40:
                    sponsor = potential_sponsor
                    desc = desc[:sm.start()].strip()

        # Detect local law
        if 'local law' in desc.lower():
            rtype = 'll'

        # Extract CP numbers
        cp = re.findall(r'CP\s*(\d{3,4}(?:\.\d+)*)', desc, re.I)

        if ir and len(desc) > 15:
            results.append({
                "ir": ir,
                "resNum": None,
                "type": rtype,
                "session": session,
                "desc": desc,
                "sponsor": sponsor,
                "committee": committee if committee else get_committee(desc),
                "status": "Pending",
                "cp": cp if cp else None,
                "sourceUrl": url,
                "votes": None
            })

    print(f"    LOT parser found {len(results)} resolutions")
    return results

def parse_agenda_pdf(text, session, url):
    """
    Parse a Marked Agenda PDF. Format is typically:
    IR#   Status  Res#
    1045  A       94    Description text... (Sponsor)

    Or sometimes all on separate lines.
    """
    results = []

    # Try to find lines with IR# + status code pattern
    # Handles: "1045 A 94" or "1045 A" or "PM04 A"
    # Also handles multiline where description follows on next lines

    STATUS_MAP = {
        "A":"Adopted", "T":"Tabled", "F":"Failed", "W":"Withdrawn",
        "TSC":"Tabled Subject to Call", "SC":"Sent to Committee",
        "X":"No Action", "CC":"Adopted", "S":"Status", "PH":"Public Hearing Set"
    }

    lines = text.split('\n')
    i = 0

    # Pattern: IR# followed by status code, optional res#
    # Matches lines like: "1045 A 94" "PM04 A" "1058 T" "1279 PH"
    pat = re.compile(
        r'^(PM\s*\d+\.?|\d{3,4})\s+'   # IR number
        r'([A-Z]{1,3})\s*'              # Status code
        r'(\d{1,3})?\s*$'              # Optional res number
    )

    # Also match inline format: "1045 A 94 Amend the 2026..."
    pat_inline = re.compile(
        r'^(PM\s*\d+\.?|\d{3,4})\s+'
        r'([A-Z]{1,3})\s+'
        r'(\d{1,3})?\s*'
        r'(.+)$'
    )

    while i < len(lines):
        line = lines[i].strip()

        # Try standalone IR# + status line
        m = pat.match(line)
        m2 = pat_inline.match(line) if not m else None

        if m or m2:
            if m:
                ir_raw = m.group(1)
                status_code = m.group(2)
                res_num = m.group(3)
                inline_desc = ""
            else:
                ir_raw = m2.group(1)
                status_code = m2.group(2)
                res_num = m2.group(3)
                inline_desc = m2.group(4).strip()

            ir = re.sub(r'\s+', '', ir_raw).rstrip('.').upper()
            status = STATUS_MAP.get(status_code, status_code)

            # Collect description from following lines
            desc_lines = [inline_desc] if inline_desc else []
            j = i + 1
            while j < len(lines) and len(desc_lines) < 12:
                next_line = lines[j].strip()
                # Stop at next IR entry
                if pat.match(next_line) or pat_inline.match(next_line):
                    break
                if is_junk_line(next_line):
                    j += 1
                    continue
                # Stop at lines that look like pure numbers (res numbers listed)
                if re.match(r'^\d{1,3}$', next_line):
                    j += 1
                    continue
                desc_lines.append(next_line)
                j += 1

            desc = ' '.join(d for d in desc_lines if d).strip()

            # Extract sponsor from parens
            sponsor = "Co. Exec."
            sm = re.search(r'\(([^)]{3,40})\)\s*$', desc)
            if sm:
                potential = sm.group(1).strip()
                if not any(c.isdigit() for c in potential):
                    sponsor = potential
                    desc = desc[:sm.start()].strip()

            rtype = 'pm' if 'PM' in ir else 'll' if 'local law' in desc.lower() else 'lot'
            cp = re.findall(r'CP\s*(\d{3,4}(?:\.\d+)*)', desc, re.I)

            if ir and (desc or status in ("Adopted","Tabled","Failed")):
                results.append({
                    "ir": ir,
                    "resNum": res_num,
                    "type": rtype,
                    "session": session,
                    "desc": desc if desc else f"Resolution {ir} — {status}",
                    "sponsor": sponsor,
                    "committee": get_committee(desc),
                    "status": status,
                    "cp": cp if cp else None,
                    "sourceUrl": url,
                })
            i = j
        else:
            i += 1

    print(f"    Agenda parser found {len(results)} resolutions")
    return results

def build_votes(absent, status):
    if status not in ("Adopted", "Tabled", "Failed"):
        return None
    v = {l: "Y" for l in ALL_LEGS}
    for a in absent:
        v[a] = "NP"
    return v

def run():
    data_path = Path("data/resolutions.json")
    data_path.parent.mkdir(exist_ok=True)

    try:
        existing = json.loads(data_path.read_text())
        print(f"Loaded existing data: {len(existing.get('resolutions',[]))} resolutions")
    except Exception as e:
        print(f"Starting fresh: {e}")
        existing = {"resolutions": [], "meetings": MEETINGS_META}

    # Build lookup by IR number
    res_by_ir = {r["ir"]: r for r in existing.get("resolutions", [])}
    found_new = 0
    updated = 0

    for doc in DOCS:
        print(f"\nProcessing: {doc['session']}")

        # Parse LOT PDF first (gets full descriptions)
        if doc.get("lot"):
            print(f"  Fetching LOT PDF...")
            text = fetch_pdf(doc["lot"])
            if text:
                parsed = parse_lot_pdf(text, doc["session"], doc["lot"])
                for r in parsed:
                    if r["ir"] not in res_by_ir:
                        res_by_ir[r["ir"]] = r
                        found_new += 1
                    else:
                        # Update description if existing one is short
                        ex = res_by_ir[r["ir"]]
                        if len(r["desc"]) > len(ex.get("desc", "")):
                            ex["desc"] = r["desc"]

        # Parse marked agenda (gets status and res numbers)
        if doc.get("agenda"):
            print(f"  Fetching marked agenda PDF...")
            text = fetch_pdf(doc["agenda"])
            if text:
                parsed = parse_agenda_pdf(text, doc["session"], doc["agenda"])
                for r in parsed:
                    if r["ir"] not in res_by_ir:
                        r["votes"] = build_votes(doc["absent"], r["status"])
                        res_by_ir[r["ir"]] = r
                        found_new += 1
                    else:
                        ex = res_by_ir[r["ir"]]
                        old_status = ex.get("status")
                        # Update status and res number from agenda
                        if r["status"] and r["status"] != old_status:
                            print(f"    Updated {r['ir']}: {old_status} -> {r['status']}")
                            ex["status"] = r["status"]
                            updated += 1
                        if r["resNum"] and not ex.get("resNum"):
                            ex["resNum"] = r["resNum"]
                        # Add votes if newly resolved
                        if r["status"] in ("Adopted","Tabled","Failed") and not ex.get("votes"):
                            ex["votes"] = build_votes(doc["absent"], r["status"])
                        # Update description if we have a better one
                        if len(r.get("desc","")) > len(ex.get("desc","")) and r.get("desc","") != f"Resolution {r['ir']} — {r['status']}":
                            ex["desc"] = r["desc"]

    # Sort by session then IR number
    session_order = [d["session"] for d in DOCS]
    def sort_key(r):
        try:
            si = session_order.index(r.get("session",""))
        except ValueError:
            si = 99
        ir = r.get("ir","")
        n = int(re.sub(r'\D','',ir) or 0)
        return (si, 0 if 'PM' in ir else 1, n)

    all_res = sorted(res_by_ir.values(), key=sort_key)

    print(f"\nResults: {len(all_res)} total ({found_new} new, {updated} updated)")

    output = {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "totalResolutions": len(all_res),
        "meetings": existing.get("meetings", MEETINGS_META),
        "resolutions": all_res
    }

    data_path.write_text(json.dumps(output, indent=2))
    print(f"Saved to {data_path}")

if __name__ == "__main__":
    run()
