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
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    except Exception as e:
        print(f"  WARNING: {url}: {e}", file=sys.stderr)
        return ""

def get_committee(desc):
    d = desc.lower()
    if any(k in d for k in ["police","sheriff","jail","correctional","district attorney","probation","firearm"]): return "Public Safety"
    if any(k in d for k in ["park","farmland","environment","wetland","agriculture","golf course","marina","open space"]): return "Environment, Parks & Agriculture"
    if any(k in d for k in ["road","highway","bridge","transit","bus","transportation","sewer","drainage","airport","ferry"]): return "Public Works, Transportation & Energy"
    if any(k in d for k in ["housing","affordable","workforce","economic","industrial","waterfront","development","planning"]): return "Economic Dev, Planning & Housing"
    if any(k in d for k in ["health","mental","substance","addiction","medical","nursing","hospital","clinic"]): return "Health"
    if any(k in d for k in ["senior","aging","youth","human service","nutrition"]): return "Seniors & Human Services"
    if any(k in d for k in ["veteran","military"]): return "Veterans"
    if any(k in d for k in ["education","labor","consumer","human rights","licensing board"]): return "Education, Labor, Consumer Affairs"
    if any(k in d for k in ["fire","rescue","ems","emergency service","aed"]): return "Fire, Rescue & EMS"
    if any(k in d for k in ["technology","personnel","salary","software","network","computer","information tech"]): return "Govt Operations, Info Tech"
    if any(k in d for k in ["budget","finance","appropriat","fund transfer","operating budget"]): return "Budget & Finance"
    if any(k in d for k in ["sale","conveyance","tax","mortgage","comptroller","insurance","settlement","reconveyance"]): return "Ways & Means"
    return "General"

def parse_pdf(text, session, url):
    results = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    STATUS = {"A":"Adopted","T":"Tabled","F":"Failed","W":"Withdrawn","TSC":"Tabled Subject to Call","SC":"Sent to Committee","X":"No Action","CC":"Adopted"}
    pat = re.compile(r'^(PM\d+\.?|\d{3,4})\s+([A-Z]{1,3})\s*(\d+)?\s*$')
    i = 0
    while i < len(lines):
        m = pat.match(lines[i])
        if m:
            ir = m.group(1).rstrip('.')
            status = STATUS.get(m.group(2), m.group(2))
            res_num = m.group(3)
            desc_parts = []
            j = i + 1
            while j < len(lines) and j < i + 6:
                if pat.match(lines[j]): break
                desc_parts.append(lines[j])
                j += 1
            desc = " ".join(desc_parts).strip()
            sponsor = "Co. Exec."
            sm = re.search(r'\(([^)]+)\)\s*$', desc)
            if sm:
                sponsor = sm.group(1)
                desc = desc[:sm.start()].strip()
            cp = re.findall(r'CP\s*(\d{3,4})', desc, re.I)
            rtype = "pm" if ir.startswith("PM") else "ll" if "local law" in desc.lower() else "lot"
            if ir and desc:
                results.append({
                    "ir": ir, "resNum": res_num, "type": rtype,
                    "session": session, "desc": desc, "sponsor": sponsor,
                    "committee": get_committee(desc), "status": status,
                    "cp": cp or None, "sourceUrl": url
                })
        i += 1
    return results

def build_votes(absent, status):
    if status not in ("Adopted","Tabled","Failed"): return None
    v = {l:"Y" for l in ALL_LEGS}
    for a in absent:
        v[a] = "NP"
    return v

def run():
    data_path = Path("data/resolutions.json")
    data_path.parent.mkdir(exist_ok=True)
    try:
        existing = json.loads(data_path.read_text())
    except:
        existing = {"resolutions":[], "meetings": MEETINGS_META}

    known_irs = {r["ir"] for r in existing["resolutions"]}
    all_res = list(existing["resolutions"])
    found_new = 0

    for doc in DOCS:
        print(f"\nProcessing: {doc['session']}")
        for url_key in ["agenda", "lot"]:
            url = doc.get(url_key)
            if not url:
                continue
            print(f"  Fetching {url_key}...")
            text = fetch_pdf(url)
            if not text:
                continue
            parsed = parse_pdf(text, doc["session"], url)
            print(f"  Parsed {len(parsed)} items")
            for r in parsed:
                if r["ir"] not in known_irs:
                    r["votes"] = build_votes(doc["absent"], r["status"])
                    all_res.append(r)
                    known_irs.add(r["ir"])
                    found_new += 1
                else:
                    for ex in all_res:
                        if ex["ir"] == r["ir"] and ex.get("status") != r["status"]:
                            print(f"  Updated {r['ir']}: {ex.get('status')} -> {r['status']}")
                            ex["status"] = r["status"]
                            ex["resNum"] = r["resNum"] or ex.get("resNum")
                            ex["votes"] = build_votes(doc["absent"], r["status"])

    print(f"\nTotal: {len(all_res)} resolutions ({found_new} new)")

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
