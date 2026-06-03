"""
Suffolk County Legislature 2026 Document Tracker
Scrapes HTML index pages for all document types — no PDF parsing.
Automatically picks up new documents as they are published.
"""

import json, re, sys
from datetime import datetime, timezone
from pathlib import Path
import urllib.request

YEAR = "2026"

# ── ALL DOCUMENT SOURCE PAGES ─────────────────────────────────────────────────
SOURCES = [
    {
        "url": "https://www.scnylegislature.us/661/Laid-on-the-Table-Resolutions-LOT",
        "type": "lot",
        "label": "LOT Resolutions",
    },
    {
        "url": "https://www.scnylegislature.us/648/Procedural-Motions",
        "type": "pm",
        "label": "Procedural Motions",
    },
    {
        "url": "https://www.scnylegislature.us/665/Local-Laws",
        "type": "ll",
        "label": "Local Laws",
    },
    {
        "url": "https://www.scnylegislature.us/684/Budget-Amendments",
        "type": "budget",
        "label": "Budget Amendments",
    },
    {
        "url": "https://www.scnylegislature.us/205/Home-Rule-Messages",
        "type": "hrl",
        "label": "Home Rule Messages",
    },
    {
        "url": "https://www.scnylegislature.us/765/General-Meetings-Agendas-Minutes",
        "type": "meeting",
        "label": "Meeting Documents",
    },
]

# ── MEETINGS INDEX PAGES ──────────────────────────────────────────────────────
MEETING_SOURCES = [
    {
        "url": "https://www.scnylegislature.us/661/Laid-on-the-Table-Resolutions-LOT",
        "doc_type": "LOT Resolutions",
    },
    {
        "url": "https://www.scnylegislature.us/765/General-Meetings-Agendas-Minutes",
        "doc_type": "Meeting Documents",
    },
]

ALL_LEGS = [
    "doroski","welker","mazzarella","caracappa","englebright","lennon",
    "thorne","piccirillo","gonzalez","bergin","flotteron","kennedy",
    "formica","renna","richberg","sanin","donnelly","bontempi"
]

SESSION_ABSENT = {
    "Jan 5, 2026":  [],
    "Feb 3, 2026":  ["richberg","gonzalez","kennedy"],
    "Mar 10, 2026": [],
    "Apr 21, 2026": [],
    "May 12, 2026": [],
}

# Known vote outcomes: IR# -> (status, res#)
KNOWN_OUTCOMES = {
    "1031":("Adopted","177"),"1038":("Adopted","102"),"1039":("Adopted","133"),
    "1044":("Adopted","187"),"1045":("Adopted","94"), "1046":("Adopted","95"),
    "1047":("Adopted","134"),"1048":("Adopted","135"),"1049":("Adopted","136"),
    "1050":("Adopted","137"),"1051":("Adopted","96"), "1052":("Adopted","205"),
    "1053":("Adopted","97"), "1054":("Adopted","114"),"1055":("Adopted","178"),
    "1056":("Adopted","122"),"1057":("Adopted","103"),"1058":("Tabled",None),
    "1059":("Adopted","116"),"1060":("Adopted","104"),"1061":("Adopted","105"),
    "1062":("Adopted","106"),"1063":("Adopted","107"),"1064":("Adopted","108"),
    "1065":("Adopted",None), "1066":("Adopted","138"),"1067":("Adopted","139"),
    "1068":("Adopted","140"),"1069":("Adopted","141"),"1070":("Adopted","109"),
    "1071":("Adopted","98"), "1072":("Adopted","110"),"1073":("Adopted","143"),
    "1074":("Adopted","188"),"1075":("Adopted","145"),"1076":("Adopted","146"),
    "1077":("Adopted","147"),"1078":("Adopted","149"),"1079":("Adopted","150"),
    "1080":("Adopted","151"),"1081":("Adopted","153"),"1082":("Adopted","155"),
    "1083":("Adopted","156"),"1084":("Adopted","158"),"1085":("Adopted","159"),
    "1086":("Adopted","160"),"1087":("Adopted","161"),"1088":("Adopted","180"),
    "1089":("Adopted","125"),"1090":("Adopted","126"),"1091":("Adopted","181"),
    "1092":("Adopted","183"),"1093":("Adopted","127"),"1094":("Adopted","128"),
    "1095":("Adopted","111"),"1097":("Adopted","190"),"1098":("Adopted","198"),
    "1099":("Adopted","192"),"1100":("Adopted","193"),"1101":("Adopted","194"),
    "1102":("Adopted","200"),"1103":("Adopted","300"),"1104":("Adopted","162"),
    "1105":("Adopted","184"),"1106":("Adopted","185"),"1107":("Adopted","117"),
    "1108":("Adopted","163"),"1109":("Adopted","164"),"1110":("Adopted","165"),
    "1111":("Adopted","302"),"1112":("Adopted","166"),"1113":("Adopted","167"),
    "1114":("Adopted","186"),"1115":("Adopted","118"),"1116":("Adopted","119"),
    "1117":("Adopted","120"),"1118":("Adopted","121"),"1120":("Adopted","168"),
    "1121":("Adopted","196"),"1122":("Adopted","202"),"1123":("Adopted","169"),
    "1124":("Adopted","129"),"1126":("Adopted","130"),"1127":("Adopted","115"),
    "1128":("Adopted","131"),"1129":("Adopted","170"),"1130":("Adopted","171"),
    "1131":("Adopted","204"),"1132":("Adopted","132"),"1133":("Adopted","99"),
    "1134":("Adopted","100"),"1135":("Adopted","262"),"1138":("Adopted","112"),
    "1139":("Adopted","101"),"1153":("Adopted","122"),"1154":("Adopted","172"),
    "1155":("Adopted","173"),"1156":("Adopted","174"),"1157":("Adopted","175"),
    "1158":("Adopted","176"),"1160":("Adopted","113"),"1163":("Adopted","209"),
    "1164":("Adopted","123"),"1165":("Adopted","124"),
    "1167":("Adopted","277"),"1168":("Adopted","279"),"1169":("Adopted","247"),
    "1170":("Adopted","248"),"1171":("Adopted","280"),"1172":("Adopted","282"),
    "1173":("Adopted","284"),"1174":("Adopted","263"),"1175":("Adopted","265"),
    "1176":("Adopted","337"),"1177":("Adopted","338"),"1178":("Adopted","266"),
    "1179":("Adopted","267"),"1180":("Adopted","269"),"1181":("Adopted","270"),
    "1182":("Adopted","271"),"1183":("Adopted","232"),"1184":("Adopted","339"),
    "1186":("Adopted","272"),"1187":("Adopted","249"),"1188":("Adopted","250"),
    "1189":("Adopted","251"),"1190":("Adopted","253"),"1191":("Adopted","254"),
    "1192":("Adopted","303"),"1193":("Adopted","305"),"1194":("Adopted","307"),
    "1195":("Adopted","255"),"1196":("Adopted","257"),"1197":("Adopted","259"),
    "1198":("Adopted","308"),"1199":("Adopted","309"),"1200":("Adopted","311"),
    "1201":("Adopted","313"),"1202":("Adopted","315"),"1203":("Adopted","317"),
    "1204":("Adopted","318"),"1205":("Adopted","233"),"1206":("Adopted","340"),
    "1207":("Adopted","234"),"1208":("Adopted","319"),"1209":("Adopted","320"),
    "1210":("Adopted","322"),"1211":("Adopted","235"),"1212":("Adopted","236"),
    "1213":("Adopted","237"),"1214":("Adopted","260"),"1215":("Adopted","324"),
    "1216":("Adopted","288"),"1217":("Adopted","289"),"1218":("Adopted","326"),
    "1219":("Adopted","290"),"1220":("Adopted","328"),"1221":("Adopted","292"),
    "1222":("Adopted","294"),"1223":("Adopted","296"),"1224":("Adopted","298"),
    "1225":("Adopted","329"),"1226":("Adopted","331"),"1227":("Adopted","332"),
    "1228":("Adopted",None), "1229":("Adopted",None), "1230":("Adopted","224"),
    "1231":("Adopted","273"),"1232":("Adopted","238"),"1233":("Adopted","239"),
    "1234":("Adopted","240"),"1235":("Adopted","241"),"1236":("Adopted","242"),
    "1237":("Adopted",None), "1238":("Adopted","243"),"1239":("Adopted","286"),
    "1240":("Adopted","244"),"1241":("Adopted","73"), "1242":("Adopted","74"),
    "1243":("Adopted","75"), "1244":("Adopted","76"), "1245":("Adopted","77"),
    "1246":("Adopted","78"), "1247":("Adopted","79"), "1248":("Adopted","80"),
    "1249":("Adopted","81"), "1250":("Adopted","82"), "1251":("Adopted","83"),
    "1252":("Adopted","84"), "1253":("Adopted","85"), "1254":("Adopted","86"),
    "1255":("Adopted","87"), "1256":("Adopted","88"), "1257":("Adopted","89"),
    "1258":("Adopted","90"), "1259":("Adopted","91"), "1260":("Adopted","92"),
    "1261":("Adopted","93"), "1262":("Adopted","274"),"1263":("Adopted","275"),
    "1264":("Adopted","225"),"1265":("Adopted","226"),"1266":("Adopted","245"),
    "1267":("Adopted","246"),"1268":("Adopted","227"),"1269":("Adopted","228"),
    "1270":("Adopted","229"),"1271":("Adopted","230"),"1272":("Adopted","231"),
    "1273":("Adopted","261"),"1276":("Adopted","287"),"1277":("Adopted","333"),
    "1278":("Adopted","334"),"1281":("Adopted","336"),"1282":("Adopted","264"),
    "1393":("Adopted",None),
}

def fetch_html(url):
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}", file=sys.stderr)
        return ""

def strip_tags(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html)).strip()

def get_committee(desc):
    d = desc.lower()
    if any(k in d for k in ["police","sheriff","jail","correctional","district attorney","probation","firearm","crime","criminal","narcotics"]): return "Public Safety"
    if any(k in d for k in ["park","farmland","environment","wetland","agriculture","golf course","marina","open space","drinking water","conservation","beach"]): return "Environment, Parks & Agriculture"
    if any(k in d for k in ["road","highway","bridge","transit","bus","transportation","sewer","drainage","airport","ferry","traffic"]): return "Public Works, Transportation & Energy"
    if any(k in d for k in ["housing","affordable","workforce","economic","industrial","waterfront","development","planning","jumpstart"]): return "Economic Dev, Planning & Housing"
    if any(k in d for k in ["health","mental","substance","addiction","medical","nursing","hospital","clinic","wic","oasas","behavioral"]): return "Health"
    if any(k in d for k in ["senior","aging","youth","human service","nutrition","child care","day care"]): return "Seniors & Human Services"
    if any(k in d for k in ["veteran","military","armed forces"]): return "Veterans"
    if any(k in d for k in ["education","labor","consumer","human rights","licensing board","college"]): return "Education, Labor, Consumer Affairs"
    if any(k in d for k in ["fire","rescue","ems","emergency service","aed","hazmat","911"]): return "Fire, Rescue & EMS"
    if any(k in d for k in ["technology","personnel","salary","software","network","computer","information tech","payroll","classification"]): return "Govt Operations, Info Tech"
    if any(k in d for k in ["budget","finance","appropriat","fund transfer","operating budget","capital budget","refund","chargeback","bond","amending resolution"]): return "Budget & Finance"
    if any(k in d for k in ["sale","conveyance","tax","mortgage","comptroller","insurance","settlement","reconveyance","clerk","deed"]): return "Ways & Means"
    return "General"

def build_votes(session, status):
    if status not in ("Adopted","Tabled","Failed"):
        return None
    absent = SESSION_ABSENT.get(session, [])
    return {l: ("NP" if l in absent else "Y") for l in ALL_LEGS}

def infer_session_from_url(url):
    """Extract date from URL and map to session label."""
    m = re.search(r'(\d{2})(\d{2})2026', url)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        if month == 1: return "Jan 5, 2026"
        if month == 2: return "Feb 3, 2026"
        if month == 3: return "Mar 10, 2026"
        if month == 4: return "Apr 21, 2026"
        if month == 5: return "May 12, 2026"
    return "2026"

def scrape_lot_page(html, source_url):
    """Scrape LOT index page - each link is a full PDF of resolutions for a meeting."""
    items = []
    # Find all 2026 PDF links
    links = re.findall(
        r'href="(https://www\.scnylegislature\.us/DocumentCenter/View/\d+/[^"]+)"[^>]*>\s*([^<]+)',
        html
    )
    for url, name in links:
        name = name.strip()
        if "2026" not in name and "2026" not in url:
            continue
        # Extract date from link name like "03/10/2026 Laid on the Table..."
        date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', name)
        if date_match:
            month, day, year = date_match.groups()
            if year != "2026":
                continue
            months = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            session = f"{months[int(month)]} {int(day)}, {year}"
            items.append({
                "id": f"LOT-{month}{day}{year}",
                "ir": f"LOT-{month}{day}",
                "resNum": None,
                "type": "lot",
                "session": session,
                "desc": f"{name.strip()} — PDF containing all resolutions laid on the table at the {session} meeting.",
                "sponsor": "Legislature",
                "committee": "All Committees",
                "status": "Published",
                "cp": None,
                "sourceUrl": url,
                "votes": None,
            })
    return items

def scrape_procedural_motions(html):
    """Scrape procedural motions page - individual PDF per motion with number in name."""
    items = []
    links = re.findall(
        r'href="(https://www\.scnylegislature\.us/DocumentCenter/View/\d+/Procedural-Motion-(\d+)-2026[^"]*)"[^>]*>\s*([^<]+)',
        html, re.IGNORECASE
    )
    for url, num, name in links:
        name = name.strip()
        ir = f"PM{num.zfill(2)}"
        outcome = KNOWN_OUTCOMES.get(ir, KNOWN_OUTCOMES.get(num))
        status = outcome[0] if outcome else "Filed"
        res_num = outcome[1] if outcome else None
        items.append({
            "ir": ir,
            "resNum": res_num,
            "type": "pm",
            "session": "2026",
            "desc": name,
            "sponsor": "Legislature",
            "committee": "Ways & Means",
            "status": status,
            "cp": None,
            "sourceUrl": url,
            "votes": None,
        })
    return items

def scrape_local_laws(html):
    """Scrape local laws page - one consolidated PDF per year."""
    items = []
    links = re.findall(
        r'href="(https://www\.scnylegislature\.us/DocumentCenter/View/\d+/2026-Local-Laws[^"]*)"[^>]*>\s*([^<]+)',
        html, re.IGNORECASE
    )
    for url, name in links:
        items.append({
            "ir": "LL-2026",
            "resNum": None,
            "type": "ll",
            "session": "2026",
            "desc": "2026 Local Laws — Consolidated PDF of all local laws passed in 2026.",
            "sponsor": "Legislature",
            "committee": "General",
            "status": "Published",
            "cp": None,
            "sourceUrl": url,
            "votes": None,
        })
    return items

def scrape_budget_amendments(html):
    """Scrape budget amendments page."""
    items = []
    # Find the 2026 section - look for links after the 2026 tab
    section_2026 = re.search(r'### 2026(.*?)###', html, re.DOTALL)
    if not section_2026:
        # Try to find 2026 links directly
        section_2026_match = html
    else:
        section_2026_match = section_2026.group(1)

    links = re.findall(
        r'href="(https://www\.scnylegislature\.us/DocumentCenter/View/\d+/[^"]*(?:2026|Budget-Amend)[^"]*)"[^>]*>\s*([^<]+)',
        html, re.IGNORECASE
    )
    seen = set()
    for url, name in links:
        name = name.strip()
        if "2026" not in name and "2026" not in url:
            continue
        if url in seen:
            continue
        seen.add(url)
        # Extract amendment number
        num_match = re.search(r'(\d{2})-2026', name)
        num = num_match.group(1) if num_match else "01"
        ir = f"BA-{num}-2026"
        items.append({
            "ir": ir,
            "resNum": None,
            "type": "budget",
            "session": "2026",
            "desc": name,
            "sponsor": "Co. Exec.",
            "committee": "Budget & Finance",
            "status": "Published",
            "cp": None,
            "sourceUrl": url,
            "votes": None,
        })
    return items

def scrape_home_rule(html):
    """Scrape home rule messages page."""
    items = []
    links = re.findall(
        r'href="(https://www\.scnylegislature\.us/DocumentCenter/View/\d+/Home-Rule[^"]*2026[^"]*)"[^>]*>\s*([^<]+)',
        html, re.IGNORECASE
    )
    seen = set()
    for url, name in links:
        name = name.strip()
        if url in seen:
            continue
        seen.add(url)
        num_match = re.search(r'(\d{2})-2026', name)
        num = num_match.group(1) if num_match else "01"
        ir = f"HR-{num}-2026"
        items.append({
            "ir": ir,
            "resNum": None,
            "type": "hrl",
            "session": "2026",
            "desc": name,
            "sponsor": "Legislature",
            "committee": "General",
            "status": "Filed",
            "cp": None,
            "sourceUrl": url,
            "votes": None,
        })
    return items

def scrape_meetings_docs(html):
    """Scrape meetings index page for all document links."""
    meetings = {}
    # Find all document links with dates
    links = re.findall(
        r'href="(https://www\.scnylegislature\.us/DocumentCenter/View/\d+/(\d{2})(\d{2})(2026)[^"]*)"[^>]*>\s*([^<]+)',
        html
    )
    for url, month, day, year, name in links:
        name = name.strip()
        months = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        session = f"{months[int(month)]} {int(day)}, {year}"
        if session not in meetings:
            meetings[session] = {"label": session, "type": "General Meeting", "docs": []}
        if not any(d["url"] == url for d in meetings[session]["docs"]):
            meetings[session]["docs"].append({"name": name, "url": url})
    return list(meetings.values())

def run():
    data_path = Path("data/resolutions.json")
    data_path.parent.mkdir(exist_ok=True)

    # Load existing data
    try:
        existing = json.loads(data_path.read_text())
        if not existing.get("resolutions"):
            raise ValueError("empty")
        print(f"Loaded {len(existing['resolutions'])} existing resolutions")
    except Exception:
        print("Starting fresh")
        existing = {"resolutions": [], "meetings": []}

    res_by_ir = {r["ir"]: r for r in existing.get("resolutions", [])}
    all_meetings = existing.get("meetings", [])
    found_new = 0
    updated = 0

    # ── SCRAPE EACH SOURCE PAGE ────────────────────────────────────────────────
    print("\n=== Scraping LOT Resolutions Index ===")
    html = fetch_html("https://www.scnylegislature.us/661/Laid-on-the-Table-Resolutions-LOT")
    if html:
        # Update meetings from LOT page
        lot_meetings = scrape_meetings_docs(html)
        for m in lot_meetings:
            existing_m = next((x for x in all_meetings if x["label"] == m["label"]), None)
            if not existing_m:
                all_meetings.append(m)
                print(f"  New meeting: {m['label']}")
            else:
                for doc in m["docs"]:
                    if not any(d["url"] == doc["url"] for d in existing_m["docs"]):
                        existing_m["docs"].append(doc)

    print("\n=== Scraping Procedural Motions ===")
    html = fetch_html("https://www.scnylegislature.us/648/Procedural-Motions")
    if html:
        items = scrape_procedural_motions(html)
        print(f"  Found {len(items)} procedural motions")
        for item in items:
            if item["ir"] not in res_by_ir:
                res_by_ir[item["ir"]] = item
                found_new += 1
            else:
                ex = res_by_ir[item["ir"]]
                if item["sourceUrl"] and not ex.get("sourceUrl"):
                    ex["sourceUrl"] = item["sourceUrl"]

    print("\n=== Scraping Local Laws ===")
    html = fetch_html("https://www.scnylegislature.us/665/Local-Laws")
    if html:
        items = scrape_local_laws(html)
        print(f"  Found {len(items)} local law documents")
        for item in items:
            if item["ir"] not in res_by_ir:
                res_by_ir[item["ir"]] = item
                found_new += 1

    print("\n=== Scraping Budget Amendments ===")
    html = fetch_html("https://www.scnylegislature.us/684/Budget-Amendments")
    if html:
        items = scrape_budget_amendments(html)
        print(f"  Found {len(items)} budget amendments")
        for item in items:
            if item["ir"] not in res_by_ir:
                res_by_ir[item["ir"]] = item
                found_new += 1

    print("\n=== Scraping Home Rule Messages ===")
    html = fetch_html("https://www.scnylegislature.us/205/Home-Rule-Messages")
    if html:
        items = scrape_home_rule(html)
        print(f"  Found {len(items)} home rule messages")
        for item in items:
            if item["ir"] not in res_by_ir:
                res_by_ir[item["ir"]] = item
                found_new += 1

    print("\n=== Scraping Meetings Index ===")
    html = fetch_html("https://www.scnylegislature.us/765/General-Meetings-Agendas-Minutes")
    if html:
        meetings_from_page = scrape_meetings_docs(html)
        for m in meetings_from_page:
            existing_m = next((x for x in all_meetings if x["label"] == m["label"]), None)
            if not existing_m:
                all_meetings.append(m)
                print(f"  New meeting: {m['label']}")
            else:
                for doc in m["docs"]:
                    if not any(d["url"] == doc["url"] for d in existing_m["docs"]):
                        existing_m["docs"].append(doc)
                        print(f"  New doc for {m['label']}: {doc['name']}")

    # ── APPLY KNOWN VOTE OUTCOMES TO EXISTING RESOLUTIONS ─────────────────────
    print("\n=== Applying Known Vote Outcomes ===")
    for ir, (status, res_num) in KNOWN_OUTCOMES.items():
        if ir in res_by_ir:
            ex = res_by_ir[ir]
            if ex.get("status","Pending") == "Pending" and status != "Pending":
                ex["status"] = status
                ex["resNum"] = res_num or ex.get("resNum")
                ex["votes"] = build_votes(ex.get("session","2026"), status)
                updated += 1

    # ── SORT AND SAVE ──────────────────────────────────────────────────────────
    type_order = ["pm","lot","ll","budget","hrl","meeting"]
    session_order = ["Jan 5, 2026","Feb 3, 2026","Mar 10, 2026",
                     "Apr 21, 2026","May 12, 2026","2026"]

    def sort_key(r):
        try: si = session_order.index(r.get("session","2026"))
        except ValueError: si = 99
        try: ti = type_order.index(r.get("type","lot"))
        except ValueError: ti = 99
        ir = r.get("ir","")
        n = int(re.sub(r'\D','',ir) or 0)
        return (si, ti, n)

    all_res = sorted(res_by_ir.values(), key=sort_key)

    # Sort meetings by date
    months_order = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
                    "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
    def meeting_sort(m):
        parts = m["label"].split()
        try: return (int(parts[2]), months_order.get(parts[0],0), int(parts[1].rstrip(',')))
        except: return (9999,0,0)

    all_meetings.sort(key=meeting_sort, reverse=True)

    print(f"\nFinal: {len(all_res)} items ({found_new} new, {updated} updated)")

    output = {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "totalResolutions": len(all_res),
        "meetings": all_meetings,
        "resolutions": all_res,
    }
    data_path.write_text(json.dumps(output, indent=2))
    print(f"Saved to {data_path}")

if __name__ == "__main__":
    run()
