"""
Suffolk County Legislature 2026 Document Tracker
Scrapes HTML index pages for all document types.
Verified against actual page HTML from scnylegislature.us
"""

import json, re, sys
from datetime import datetime, timezone
from pathlib import Path
import urllib.request

YEAR = "2026"
BASE = "https://www.scnylegislature.us"

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
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            content = r.read().decode("utf-8", errors="replace")
            print(f"  Fetched {len(content)} chars from {url}")
            return content
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}", file=sys.stderr)
        return ""

def get_all_links(html):
    """Extract all href links and their text from HTML."""
    # Match <a href="...">text</a> — handles multi-line and attributes
    pattern = re.compile(
        r'<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        re.IGNORECASE | re.DOTALL
    )
    results = []
    for m in pattern.finditer(html):
        url = m.group(1).strip()
        text = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        text = re.sub(r'\s+', ' ', text)
        if url and text:
            results.append((url, text))
    return results

def get_committee(desc):
    d = desc.lower()
    if any(k in d for k in ["police","sheriff","jail","correctional","district attorney","probation","firearm","crime","criminal"]): return "Public Safety"
    if any(k in d for k in ["park","farmland","environment","wetland","agriculture","golf course","marina","open space","drinking water","conservation","beach"]): return "Environment, Parks & Agriculture"
    if any(k in d for k in ["road","highway","bridge","transit","bus","transportation","sewer","drainage","airport","ferry","traffic"]): return "Public Works, Transportation & Energy"
    if any(k in d for k in ["housing","affordable","workforce","economic","industrial","waterfront","development","planning","jumpstart"]): return "Economic Dev, Planning & Housing"
    if any(k in d for k in ["health","mental","substance","addiction","medical","nursing","hospital","clinic","wic","oasas","behavioral"]): return "Health"
    if any(k in d for k in ["senior","aging","youth","human service","nutrition","child care","day care"]): return "Seniors & Human Services"
    if any(k in d for k in ["veteran","military"]): return "Veterans"
    if any(k in d for k in ["education","labor","consumer","human rights","licensing board","college"]): return "Education, Labor, Consumer Affairs"
    if any(k in d for k in ["fire","rescue","ems","emergency service","aed","hazmat"]): return "Fire, Rescue & EMS"
    if any(k in d for k in ["technology","personnel","salary","software","network","computer","information tech","payroll","classification"]): return "Govt Operations, Info Tech"
    if any(k in d for k in ["budget","finance","appropriat","fund transfer","operating budget","capital budget","refund","chargeback","bond","amending"]): return "Budget & Finance"
    if any(k in d for k in ["sale","conveyance","tax","mortgage","comptroller","insurance","settlement","reconveyance","clerk","deed"]): return "Ways & Means"
    return "General"

def build_votes(session, status):
    if status not in ("Adopted","Tabled","Failed"):
        return None
    absent = SESSION_ABSENT.get(session, [])
    return {l: ("NP" if l in absent else "Y") for l in ALL_LEGS}

def is_doc_link(url):
    """Check if URL is a Suffolk County DocumentCenter PDF link."""
    return "scnylegislature.us/DocumentCenter/View/" in url

def run():
    data_path = Path("data/resolutions.json")
    data_path.parent.mkdir(exist_ok=True)

    try:
        existing = json.loads(data_path.read_text())
        if not existing.get("resolutions"):
            raise ValueError("empty")
        print(f"Loaded {len(existing['resolutions'])} existing resolutions")
    except Exception:
        print("Starting fresh")
        existing = {"resolutions": [], "meetings": []}

    res_by_ir = {r["ir"]: r for r in existing.get("resolutions", [])}
    all_meetings = {m["label"]: m for m in existing.get("meetings", [])}
    found_new = 0

    # ── 1. PROCEDURAL MOTIONS ─────────────────────────────────────────────────
    print("\n=== Procedural Motions ===")
    html = fetch_html(f"{BASE}/648/Procedural-Motions")
    if html:
        links = get_all_links(html)
        count = 0
        for url, text in links:
            # Match: "Procedural Motion 01-2026 (PDF)"
            m = re.search(r'Procedural Motion (\d+)-2026', text, re.IGNORECASE)
            if m and is_doc_link(url):
                num = m.group(1).zfill(2)
                ir = f"PM{num}"
                outcome = KNOWN_OUTCOMES.get(ir)
                status = outcome[0] if outcome else "Filed"
                res_num = outcome[1] if outcome else None
                if ir not in res_by_ir:
                    res_by_ir[ir] = {
                        "ir": ir, "resNum": res_num, "type": "pm",
                        "session": "2026", "desc": f"Procedural Motion {num}-2026",
                        "sponsor": "Legislature", "committee": "Ways & Means",
                        "status": status, "cp": None, "sourceUrl": url,
                        "votes": build_votes("2026", status),
                    }
                    found_new += 1
                    count += 1
        print(f"  Added {count} procedural motions")

    # ── 2. LOT RESOLUTIONS ────────────────────────────────────────────────────
    print("\n=== LOT Resolutions ===")
    html = fetch_html(f"{BASE}/661/Laid-on-the-Table-Resolutions-LOT")
    if html:
        links = get_all_links(html)
        MONTHS = {"01":"Jan","02":"Feb","03":"Mar","04":"Apr","05":"May",
                  "06":"Jun","07":"Jul","08":"Aug","09":"Sep","10":"Oct",
                  "11":"Nov","12":"Dec"}
        count = 0
        for url, text in links:
            # Match: "03/10/2026 Laid on the Table Resolutions (PDF)"
            m = re.search(r'(\d{2})/(\d{2})/(2026)', text)
            if m and is_doc_link(url):
                month, day, year = m.group(1), m.group(2), m.group(3)
                session = f"{MONTHS[month]} {int(day)}, {year}"
                ir = f"LOT-{month}{day}{year}"
                if ir not in res_by_ir:
                    res_by_ir[ir] = {
                        "ir": ir, "resNum": None, "type": "lot",
                        "session": session,
                        "desc": f"Laid on the Table Resolutions — {session} General Meeting. Click PDF to view all resolutions introduced at this meeting.",
                        "sponsor": "Legislature", "committee": "All Committees",
                        "status": "Published", "cp": None, "sourceUrl": url,
                        "votes": None,
                    }
                    # Add to meetings
                    if session not in all_meetings:
                        all_meetings[session] = {"label": session, "type": "General Meeting", "docs": []}
                    if not any(d["url"] == url for d in all_meetings[session]["docs"]):
                        all_meetings[session]["docs"].append({"name": "LOT Resolutions", "url": url})
                    found_new += 1
                    count += 1
        print(f"  Added {count} LOT document entries")

    # ── 3. LOCAL LAWS ─────────────────────────────────────────────────────────
    print("\n=== Local Laws ===")
    html = fetch_html(f"{BASE}/665/Local-Laws")
    if html:
        links = get_all_links(html)
        count = 0
        for url, text in links:
            # Match: "2026 Local Laws (PDF)"
            if "2026" in text and "Local Laws" in text and is_doc_link(url):
                ir = "LL-2026-INDEX"
                if ir not in res_by_ir:
                    res_by_ir[ir] = {
                        "ir": ir, "resNum": None, "type": "ll",
                        "session": "2026",
                        "desc": "2026 Local Laws — Consolidated PDF index of all local laws passed in 2026.",
                        "sponsor": "Legislature", "committee": "General",
                        "status": "Published", "cp": None, "sourceUrl": url,
                        "votes": None,
                    }
                    found_new += 1
                    count += 1
        print(f"  Added {count} local law index entries")

    # ── 4. BUDGET AMENDMENTS ──────────────────────────────────────────────────
    print("\n=== Budget Amendments ===")
    html = fetch_html(f"{BASE}/684/Budget-Amendments")
    if html:
        links = get_all_links(html)
        count = 0
        seen_urls = set()
        for url, text in links:
            if not is_doc_link(url) or url in seen_urls:
                continue
            # Match 2026 budget amendment documents
            if "2026" not in text and "2026" not in url:
                continue
            if not any(k in text.lower() for k in ["budget", "amend", "capital program"]):
                continue
            seen_urls.add(url)
            # Extract number if present
            num_m = re.search(r'(\d{2})-2026', text)
            num = num_m.group(1) if num_m else "00"
            ir = f"BA-{num}-2026"
            # Make unique if duplicate number
            while ir in res_by_ir and res_by_ir[ir]["sourceUrl"] != url:
                num = str(int(num) + 1).zfill(2)
                ir = f"BA-{num}-2026"
            if ir not in res_by_ir:
                res_by_ir[ir] = {
                    "ir": ir, "resNum": None, "type": "budget",
                    "session": "2026", "desc": text,
                    "sponsor": "Co. Exec.", "committee": "Budget & Finance",
                    "status": "Published", "cp": None, "sourceUrl": url,
                    "votes": None,
                }
                found_new += 1
                count += 1
        print(f"  Added {count} budget amendment entries")

    # ── 5. HOME RULE MESSAGES ─────────────────────────────────────────────────
    print("\n=== Home Rule Messages ===")
    html = fetch_html(f"{BASE}/205/Home-Rule-Messages")
    if html:
        links = get_all_links(html)
        count = 0
        for url, text in links:
            # Match: "Home Rule 01-2026 (PDF)"
            m = re.search(r'Home Rule[^\d]*(\d+)-2026', text, re.IGNORECASE)
            if m and is_doc_link(url):
                num = m.group(1).zfill(2)
                ir = f"HR-{num}-2026"
                if ir not in res_by_ir:
                    res_by_ir[ir] = {
                        "ir": ir, "resNum": None, "type": "hrl",
                        "session": "2026", "desc": text,
                        "sponsor": "Legislature", "committee": "General",
                        "status": "Filed", "cp": None, "sourceUrl": url,
                        "votes": None,
                    }
                    found_new += 1
                    count += 1
        print(f"  Added {count} home rule messages")

    # ── 6. MEETINGS INDEX ─────────────────────────────────────────────────────
    print("\n=== Meeting Documents ===")
    for page_url in [
        f"{BASE}/765/General-Meetings-Agendas-Minutes",
        f"{BASE}/661/Laid-on-the-Table-Resolutions-LOT",
    ]:
        html = fetch_html(page_url)
        if not html:
            continue
        links = get_all_links(html)
        MONTHS = {"01":"Jan","02":"Feb","03":"Mar","04":"Apr","05":"May",
                  "06":"Jun","07":"Jul","08":"Aug","09":"Sep","10":"Oct",
                  "11":"Nov","12":"Dec"}
        DOC_NAMES = {
            "laid-on-the-table": "LOT Resolutions",
            "marked-agenda": "Marked Agenda",
            "minutes": "Minutes",
            "action-report": "Action Report",
            "resolution-packet": "Resolution Packet",
            "notice": "Notice",
        }
        for url, text in links:
            if not is_doc_link(url):
                continue
            url_lower = url.lower()
            if "2026" not in url_lower:
                continue
            # Extract date from URL
            date_m = re.search(r'(\d{2})(\d{2})(2026)', url_lower)
            if not date_m:
                continue
            month, day, year = date_m.group(1), date_m.group(2), date_m.group(3)
            if month not in MONTHS:
                continue
            session = f"{MONTHS[month]} {int(day)}, {year}"
            # Determine doc type
            doc_name = text.strip() or "Document"
            for key, name in DOC_NAMES.items():
                if key in url_lower:
                    doc_name = name
                    break
            # Add to meetings
            if session not in all_meetings:
                all_meetings[session] = {"label": session, "type": "General Meeting", "docs": []}
            if not any(d["url"] == url for d in all_meetings[session]["docs"]):
                all_meetings[session]["docs"].append({"name": doc_name, "url": url})

    # ── 7. APPLY KNOWN VOTE OUTCOMES ──────────────────────────────────────────
    print("\n=== Applying Known Vote Outcomes ===")
    updated = 0
    for ir, (status, res_num) in KNOWN_OUTCOMES.items():
        if ir in res_by_ir:
            ex = res_by_ir[ir]
            if ex.get("status","Pending") == "Pending":
                ex["status"] = status
                if res_num:
                    ex["resNum"] = res_num
                ex["votes"] = build_votes(ex.get("session","2026"), status)
                updated += 1

    # ── 8. SORT AND SAVE ──────────────────────────────────────────────────────
    type_order = {"pm":0,"lot":1,"ll":2,"budget":3,"hrl":4}
    session_order = ["Jan 5, 2026","Feb 3, 2026","Mar 10, 2026",
                     "Apr 21, 2026","May 12, 2026","2026"]

    def sort_key(r):
        try: si = session_order.index(r.get("session","2026"))
        except ValueError: si = 99
        ti = type_order.get(r.get("type","lot"), 5)
        ir = r.get("ir","")
        n = int(re.sub(r'\D','',ir) or 0)
        return (si, ti, n)

    all_res = sorted(res_by_ir.values(), key=sort_key)

    # Sort meetings newest first
    MONTH_NUM = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
                 "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
    def meet_sort(m):
        parts = m["label"].split()
        try: return (int(parts[2]), MONTH_NUM.get(parts[0],0), int(parts[1].rstrip(',')))
        except: return (0,0,0)

    meetings_list = sorted(all_meetings.values(), key=meet_sort, reverse=True)

    print(f"\nTotal: {len(all_res)} items ({found_new} new, {updated} vote outcomes applied)")
    print(f"Meetings: {len(meetings_list)}")

    output = {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "totalResolutions": len(all_res),
        "meetings": meetings_list,
        "resolutions": all_res,
    }
    data_path.write_text(json.dumps(output, indent=2))
    print(f"Saved to {data_path}")

if __name__ == "__main__":
    run()
