"""
Suffolk County Legislature Resolution Scraper
Uses Playwright to drive a real browser and scrape the legislation search database.
Runs automatically via GitHub Actions every Sunday.
"""

import json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path

YEAR = "2026"
SEARCH_URL = "https://apps2.suffolkcountyny.gov/legislature/ressearch/"
LOT_INDEX_URL = "https://www.scnylegislature.us/661/Laid-on-the-Table-Resolutions-LOT"
MEETINGS_INDEX_URL = "https://www.scnylegislature.us/765/General-Meetings-Agendas-Minutes"

ALL_LEGS = [
    "doroski","welker","mazzarella","caracappa","englebright","lennon",
    "thorne","piccirillo","gonzalez","bergin","flotteron","kennedy",
    "formica","renna","richberg","sanin","donnelly","bontempi"
]

# Map session label -> absent legislators (from meeting minutes)
SESSION_ABSENT = {
    "Jan 5, 2026":  [],
    "Feb 3, 2026":  ["richberg","gonzalez","kennedy"],
    "Mar 10, 2026": [],
    "Apr 21, 2026": [],
    "May 12, 2026": [],
}

# Known vote outcomes from marked agendas (IR# -> status, res#)
KNOWN_OUTCOMES = {
    "1031": ("Adopted","177"), "1038": ("Adopted","102"), "1039": ("Adopted","133"),
    "1044": ("Adopted","187"), "1045": ("Adopted","94"),  "1046": ("Adopted","95"),
    "1047": ("Adopted","134"), "1048": ("Adopted","135"), "1049": ("Adopted","136"),
    "1050": ("Adopted","137"), "1051": ("Adopted","96"),  "1052": ("Adopted","205"),
    "1053": ("Adopted","97"),  "1054": ("Adopted","114"), "1055": ("Adopted","178"),
    "1056": ("Adopted","122"), "1057": ("Adopted","103"), "1058": ("Tabled", None),
    "1059": ("Adopted","116"), "1060": ("Adopted","104"), "1061": ("Adopted","105"),
    "1062": ("Adopted","106"), "1063": ("Adopted","107"), "1064": ("Adopted","108"),
    "1065": ("Adopted",None),  "1066": ("Adopted","138"), "1067": ("Adopted","139"),
    "1068": ("Adopted","140"), "1069": ("Adopted","141"), "1070": ("Adopted","109"),
    "1071": ("Adopted","98"),  "1072": ("Adopted","110"), "1073": ("Adopted","143"),
    "1074": ("Adopted","188"), "1075": ("Adopted","145"), "1076": ("Adopted","146"),
    "1077": ("Adopted","147"), "1078": ("Adopted","149"), "1079": ("Adopted","150"),
    "1080": ("Adopted","151"), "1081": ("Adopted","153"), "1082": ("Adopted","155"),
    "1083": ("Adopted","156"), "1084": ("Adopted","158"), "1085": ("Adopted","159"),
    "1086": ("Adopted","160"), "1087": ("Adopted","161"), "1088": ("Adopted","180"),
    "1089": ("Adopted","125"), "1090": ("Adopted","126"), "1091": ("Adopted","181"),
    "1092": ("Adopted","183"), "1093": ("Adopted","127"), "1094": ("Adopted","128"),
    "1095": ("Adopted","111"), "1097": ("Adopted","190"), "1098": ("Adopted","198"),
    "1099": ("Adopted","192"), "1100": ("Adopted","193"), "1101": ("Adopted","194"),
    "1102": ("Adopted","200"), "1103": ("Adopted","300"), "1104": ("Adopted","162"),
    "1105": ("Adopted","184"), "1106": ("Adopted","185"), "1107": ("Adopted","117"),
    "1108": ("Adopted","163"), "1109": ("Adopted","164"), "1110": ("Adopted","165"),
    "1111": ("Adopted","302"), "1112": ("Adopted","166"), "1113": ("Adopted","167"),
    "1114": ("Adopted","186"), "1115": ("Adopted","118"), "1116": ("Adopted","119"),
    "1117": ("Adopted","120"), "1118": ("Adopted","121"), "1120": ("Adopted","168"),
    "1121": ("Adopted","196"), "1122": ("Adopted","202"), "1123": ("Adopted","169"),
    "1124": ("Adopted","129"), "1126": ("Adopted","130"), "1127": ("Adopted","115"),
    "1128": ("Adopted","131"), "1129": ("Adopted","170"), "1130": ("Adopted","171"),
    "1131": ("Adopted","204"), "1132": ("Adopted","132"), "1133": ("Adopted","99"),
    "1134": ("Adopted","100"), "1135": ("Adopted","262"), "1136": ("Adopted",None),
    "1137": ("Adopted",None),  "1138": ("Adopted","112"), "1139": ("Adopted","101"),
    "1153": ("Adopted","122"), "1154": ("Adopted","172"), "1155": ("Adopted","173"),
    "1156": ("Adopted","174"), "1157": ("Adopted","175"), "1158": ("Adopted","176"),
    "1160": ("Adopted","113"), "1162": ("Adopted",None),  "1163": ("Adopted","209"),
    "1164": ("Adopted","123"), "1165": ("Adopted","124"),
    # Mar 10
    "1167": ("Adopted","277"), "1168": ("Adopted","279"), "1169": ("Adopted","247"),
    "1170": ("Adopted","248"), "1171": ("Adopted","280"), "1172": ("Adopted","282"),
    "1173": ("Adopted","284"), "1174": ("Adopted","263"), "1175": ("Adopted","265"),
    "1176": ("Adopted","337"), "1177": ("Adopted","338"), "1178": ("Adopted","266"),
    "1179": ("Adopted","267"), "1180": ("Adopted","269"), "1181": ("Adopted","270"),
    "1182": ("Adopted","271"), "1183": ("Adopted","232"), "1184": ("Adopted","339"),
    "1186": ("Adopted","272"), "1187": ("Adopted","249"), "1188": ("Adopted","250"),
    "1189": ("Adopted","251"), "1190": ("Adopted","253"), "1191": ("Adopted","254"),
    "1192": ("Adopted","303"), "1193": ("Adopted","305"), "1194": ("Adopted","307"),
    "1195": ("Adopted","255"), "1196": ("Adopted","257"), "1197": ("Adopted","259"),
    "1198": ("Adopted","308"), "1199": ("Adopted","309"), "1200": ("Adopted","311"),
    "1201": ("Adopted","313"), "1202": ("Adopted","315"), "1203": ("Adopted","317"),
    "1204": ("Adopted","318"), "1205": ("Adopted","233"), "1206": ("Adopted","340"),
    "1207": ("Adopted","234"), "1208": ("Adopted","319"), "1209": ("Adopted","320"),
    "1210": ("Adopted","322"), "1211": ("Adopted","235"), "1212": ("Adopted","236"),
    "1213": ("Adopted","237"), "1214": ("Adopted","260"), "1215": ("Adopted","324"),
    "1216": ("Adopted","288"), "1217": ("Adopted","289"), "1218": ("Adopted","326"),
    "1219": ("Adopted","290"), "1220": ("Adopted","328"), "1221": ("Adopted","292"),
    "1222": ("Adopted","294"), "1223": ("Adopted","296"), "1224": ("Adopted","298"),
    "1225": ("Adopted","329"), "1226": ("Adopted","331"), "1227": ("Adopted","332"),
    "1228": ("Adopted",None),  "1229": ("Adopted",None),  "1230": ("Adopted","224"),
    "1231": ("Adopted","273"), "1232": ("Adopted","238"), "1233": ("Adopted","239"),
    "1234": ("Adopted","240"), "1235": ("Adopted","241"), "1236": ("Adopted","242"),
    "1237": ("Adopted",None),  "1238": ("Adopted","243"), "1239": ("Adopted","286"),
    "1240": ("Adopted","244"), "1241": ("Adopted","73"),  "1242": ("Adopted","74"),
    "1243": ("Adopted","75"),  "1244": ("Adopted","76"),  "1245": ("Adopted","77"),
    "1246": ("Adopted","78"),  "1247": ("Adopted","79"),  "1248": ("Adopted","80"),
    "1249": ("Adopted","81"),  "1250": ("Adopted","82"),  "1251": ("Adopted","83"),
    "1252": ("Adopted","84"),  "1253": ("Adopted","85"),  "1254": ("Adopted","86"),
    "1255": ("Adopted","87"),  "1256": ("Adopted","88"),  "1257": ("Adopted","89"),
    "1258": ("Adopted","90"),  "1259": ("Adopted","91"),  "1260": ("Adopted","92"),
    "1261": ("Adopted","93"),  "1262": ("Adopted","274"), "1263": ("Adopted","275"),
    "1264": ("Adopted","225"), "1265": ("Adopted","226"), "1266": ("Adopted","245"),
    "1267": ("Adopted","246"), "1268": ("Adopted","227"), "1269": ("Adopted","228"),
    "1270": ("Adopted","229"), "1271": ("Adopted","230"), "1272": ("Adopted","231"),
    "1273": ("Adopted","261"), "1276": ("Adopted","287"), "1277": ("Adopted","333"),
    "1278": ("Adopted","334"), "1281": ("Adopted","336"), "1282": ("Adopted","264"),
    "1283": ("Adopted",None),
    # Apr 21
    "1058": ("Tabled", None),  # confirmed tabled at Apr 21
    "1393": ("Adopted",None),
}

MEETINGS_META = [
    {"label":"Jan 5, 2026","type":"Organizational Meeting","docs":[
        {"name":"LOT Resolutions","url":"https://www.scnylegislature.us/DocumentCenter/View/126663/01052026-Laid-on-the-Table-Resolutions-PDF"},
        {"name":"Minutes","url":"https://www.scnylegislature.us/DocumentCenter/View/127567/01052026-Organizational-Meeting-Minutes-PDF"}]},
    {"label":"Feb 3, 2026","type":"General Meeting","docs":[
        {"name":"Minutes","url":"https://www.scnylegislature.us/DocumentCenter/View/127979/02032026-General-Meeting-Minutes-PDF"},
        {"name":"Marked Agenda","url":"https://www.scnylegislature.us/DocumentCenter/View/127636/02032026-General-Meeting-Marked-Agenda-PDF"},
        {"name":"LOT Resolutions","url":"https://www.scnylegislature.us/DocumentCenter/View/127573/02032026-Laid-on-the-Table-Resolutions-PDF"},
        {"name":"Action Report","url":"https://www.scnylegislature.us/DocumentCenter/View/127659/02032026-Action-Report-PDF"}]},
    {"label":"Mar 10, 2026","type":"General Meeting","docs":[
        {"name":"Minutes","url":"https://www.scnylegislature.us/DocumentCenter/View/128621/03102026-General-Meeting-Minutes-PDF"},
        {"name":"Marked Agenda","url":"https://www.scnylegislature.us/DocumentCenter/View/128172/03102026-General-Meeting-Marked-Agenda-PDF"},
        {"name":"LOT Resolutions","url":"https://www.scnylegislature.us/DocumentCenter/View/127984/03102026-Laid-on-the-Table-Resolutions-PDF"},
        {"name":"Action Report","url":"https://www.scnylegislature.us/DocumentCenter/View/128168/03102026-Action-Report-PDF"}]},
    {"label":"Apr 21, 2026","type":"General Meeting","docs":[
        {"name":"Marked Agenda","url":"https://www.scnylegislature.us/DocumentCenter/View/128778/04212026-General-Meeting-Marked-Agenda-PDF"},
        {"name":"Resolution Packet","url":"https://www.scnylegislature.us/DocumentCenter/View/128633/04212026-General-Meeting-Resolution-Packet-PDF"},
        {"name":"Action Report","url":"https://www.scnylegislature.us/DocumentCenter/View/128789/04212026-Action-Report-PDF"}]},
    {"label":"May 12, 2026","type":"General Meeting","docs":[
        {"name":"Action Report","url":"https://www.scnylegislature.us/DocumentCenter/View/129295/05122026-Action-Report-PDF"}]},
]

SESSION_DATES = [
    ("Jan 5, 2026",  "2026-01-01", "2026-01-31"),
    ("Feb 3, 2026",  "2026-02-01", "2026-02-28"),
    ("Mar 10, 2026", "2026-03-01", "2026-03-31"),
    ("Apr 21, 2026", "2026-04-01", "2026-04-30"),
    ("May 12, 2026", "2026-05-01", "2026-05-31"),
]

def get_session(lot_date):
    if not lot_date:
        return "2026"
    for label, start, end in SESSION_DATES:
        if start <= lot_date <= end:
            return label
    return "2026"

def get_committee(desc):
    d = desc.lower()
    if any(k in d for k in ["police","sheriff","jail","correctional","district attorney","probation","firearm","crime","criminal"]): return "Public Safety"
    if any(k in d for k in ["park","farmland","environment","wetland","agriculture","golf course","marina","open space","drinking water","conservation","beach"]): return "Environment, Parks & Agriculture"
    if any(k in d for k in ["road","highway","bridge","transit","bus","transportation","sewer","drainage","airport","ferry","traffic"]): return "Public Works, Transportation & Energy"
    if any(k in d for k in ["housing","affordable","workforce","economic","industrial","waterfront","development","planning","jumpstart"]): return "Economic Dev, Planning & Housing"
    if any(k in d for k in ["health","mental","substance","addiction","medical","nursing","hospital","clinic","wic ","oasas","behavioral"]): return "Health"
    if any(k in d for k in ["senior","aging","youth","human service","nutrition","child care","day care","family"]): return "Seniors & Human Services"
    if any(k in d for k in ["veteran","military","armed forces"]): return "Veterans"
    if any(k in d for k in ["education","labor","consumer","human rights","licensing board","college"]): return "Education, Labor, Consumer Affairs"
    if any(k in d for k in ["fire","rescue"," ems ","emergency service","aed","hazmat","911"]): return "Fire, Rescue & EMS"
    if any(k in d for k in ["technology","personnel","salary","software","network","computer","information tech","payroll","classification plan"]): return "Govt Operations, Info Tech"
    if any(k in d for k in ["budget","finance","appropriat","fund transfer","operating budget","capital budget","refund","chargeback","bond"]): return "Budget & Finance"
    if any(k in d for k in ["sale","conveyance","tax act","mortgage","comptroller","insurance","settlement","reconveyance","county clerk","deed"]): return "Ways & Means"
    return "General"

def build_votes(session, status):
    if status not in ("Adopted","Tabled","Failed"):
        return None
    absent = SESSION_ABSENT.get(session, [])
    return {l: ("NP" if l in absent else "Y") for l in ALL_LEGS}

def scrape_with_playwright():
    """Use Playwright to scrape all 2026 resolutions from the legislation database."""
    from playwright.sync_api import sync_playwright

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("  Opening legislation search database...")
        page.goto(SEARCH_URL, wait_until="networkidle", timeout=30000)

        # Fill in the year field and submit
        print("  Submitting search for year 2026...")
        try:
            # Try different possible field selectors
            for selector in ["#txtIRYear", "input[name*='IRYear']", "input[id*='IRYear']"]:
                if page.locator(selector).count() > 0:
                    page.fill(selector, YEAR)
                    break

            # Submit the form
            for selector in ["input[type='submit']", "input[value='Submit']", "button[type='submit']", "#btnSubmit"]:
                if page.locator(selector).count() > 0:
                    page.click(selector)
                    break
            else:
                page.keyboard.press("Enter")

            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception as e:
            print(f"  Search submission error: {e}", file=sys.stderr)
            browser.close()
            return results

        # Scrape all pages of results
        page_num = 1
        while True:
            print(f"  Scraping page {page_num}...")
            page_results = extract_table_data(page)
            if not page_results:
                print(f"  No results on page {page_num}, stopping")
                break

            results.extend(page_results)
            print(f"  Found {len(page_results)} resolutions on page {page_num} (total: {len(results)})")

            # Try to go to next page
            try:
                next_links = page.locator("a").filter(has_text=re.compile(r'^\d+$'))
                # Find the link for the next page number
                found_next = False
                for i in range(next_links.count()):
                    link_text = next_links.nth(i).inner_text().strip()
                    if link_text == str(page_num + 1):
                        next_links.nth(i).click()
                        page.wait_for_load_state("networkidle", timeout=10000)
                        page_num += 1
                        found_next = True
                        time.sleep(0.5)
                        break

                if not found_next:
                    # Also check for "Next" link
                    next_btn = page.locator("a:has-text('Next'), a:has-text('>')")
                    if next_btn.count() > 0:
                        next_btn.first.click()
                        page.wait_for_load_state("networkidle", timeout=10000)
                        page_num += 1
                        time.sleep(0.5)
                    else:
                        break
            except Exception as e:
                print(f"  Pagination ended: {e}")
                break

            if page_num > 30:  # safety limit
                break

        browser.close()

    print(f"  Total scraped from database: {len(results)}")
    return results

def extract_table_data(page):
    """Extract resolution data from the current page's table."""
    results = []

    # Get all table rows
    rows = page.locator("table tr").all()

    for row in rows:
        cells = row.locator("td").all()
        if len(cells) < 3:
            continue

        texts = []
        links = []
        for cell in cells:
            texts.append(cell.inner_text().strip())
            # Check for links (PDF links)
            cell_links = cell.locator("a").all()
            links.extend([l.get_attribute("href") or "" for l in cell_links])

        if not texts:
            continue

        # Skip header rows
        if any(h in texts[0].lower() for h in ["ir", "res", "title", "sponsor", "date", "year"]):
            continue

        # Parse columns: typically [Year, IR#, Res#, LOT Date, Sponsor, Title, PDF Link]
        # or [IR#, Res#, LOT Date, Sponsor, Title]
        ir_num = None
        res_num = None
        lot_date_str = None
        sponsor = "Co. Exec."
        title = ""
        pdf_url = ""

        for t in texts:
            t = t.strip()
            if not t:
                continue
            if re.match(r'^\d{3,4}$', t) and not ir_num:
                ir_num = t
            elif re.match(r'^\d{1,3}$', t) and ir_num and not res_num:
                res_num = t
            elif re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', t):
                lot_date_str = t
            elif len(t) > 25 and not title:
                title = t
            elif 3 < len(t) <= 35 and title and not any(c.isdigit() for c in t) and t not in ["View", "PDF"]:
                sponsor = t

        # Get PDF link if any
        for link in links:
            if link and ("pdf" in link.lower() or "document" in link.lower()):
                pdf_url = link if link.startswith("http") else "https://apps2.suffolkcountyny.gov" + link
                break

        if ir_num and title and len(title) > 10:
            # Parse date
            parsed_date = None
            if lot_date_str:
                try:
                    m, d, y = lot_date_str.split('/')
                    parsed_date = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
                except:
                    pass

            results.append({
                "ir": ir_num,
                "resNum": res_num,
                "lotDate": parsed_date,
                "sponsor": sponsor,
                "title": title,
                "pdfUrl": pdf_url,
            })

    return results

def check_for_new_meetings(existing_meetings):
    """Check the meetings index page for new documents."""
    import urllib.request
    try:
        req = urllib.request.Request(
            MEETINGS_INDEX_URL,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  Could not check meetings index: {e}", file=sys.stderr)
        return existing_meetings

    # Find all document links
    existing_urls = {d["url"] for m in existing_meetings for d in m.get("docs", [])}
    found_new = False

    pdf_links = re.findall(
        r'href="(https://www\.scnylegislature\.us/DocumentCenter/View/\d+/[^"]+)"',
        html
    )

    for url in pdf_links:
        if url not in existing_urls:
            # Extract date from URL filename
            date_match = re.search(r'(\d{2})(\d{2})(\d{4})', url)
            if date_match and date_match.group(3) == "2026":
                month, day, year = date_match.groups()
                months = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
                label = f"{months[int(month)]} {int(day)}, {year}"

                # Determine doc type from filename
                url_lower = url.lower()
                if "laid-on-the-table" in url_lower:
                    doc_name = "LOT Resolutions"
                elif "marked-agenda" in url_lower:
                    doc_name = "Marked Agenda"
                elif "minutes" in url_lower:
                    doc_name = "Minutes"
                elif "action-report" in url_lower:
                    doc_name = "Action Report"
                elif "resolution-packet" in url_lower:
                    doc_name = "Resolution Packet"
                else:
                    doc_name = "Document"

                # Find or create meeting entry
                meeting = next((m for m in existing_meetings if m["label"] == label), None)
                if not meeting:
                    meeting = {"label": label, "type": "General Meeting", "docs": []}
                    existing_meetings.append(meeting)
                    print(f"  New meeting found: {label}")
                    found_new = True

                if not any(d["url"] == url for d in meeting["docs"]):
                    meeting["docs"].append({"name": doc_name, "url": url})
                    print(f"  Added document: {doc_name} for {label}")
                    found_new = True

    if not found_new:
        print("  No new meetings or documents found")

    return existing_meetings

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
        existing = {"resolutions": [], "meetings": list(MEETINGS_META)}

    res_by_ir = {r["ir"]: r for r in existing.get("resolutions", [])}
    found_new = 0
    updated = 0

    # ── STEP 1: Check for new meetings ────────────────────────────────────────
    print("\n=== Checking for New Meetings ===")
    meetings = check_for_new_meetings(existing.get("meetings", list(MEETINGS_META)))

    # ── STEP 2: Scrape legislation database with Playwright ───────────────────
    print("\n=== Scraping Legislation Database ===")
    try:
        db_results = scrape_with_playwright()
    except Exception as e:
        print(f"Playwright scraping failed: {e}", file=sys.stderr)
        db_results = []

    for r in db_results:
        ir = r["ir"]
        session = get_session(r.get("lotDate",""))
        desc = r["title"]

        # Apply known vote outcomes
        outcome = KNOWN_OUTCOMES.get(ir)
        status = outcome[0] if outcome else "Pending"
        res_num = outcome[1] if outcome else r.get("resNum")

        rtype = "pm" if ir.startswith("PM") else "ll" if "local law" in desc.lower() else "lot"
        cp = re.findall(r'CP\s*(\d{3,4})', desc, re.I)

        entry = {
            "ir": ir,
            "resNum": res_num,
            "type": rtype,
            "session": session,
            "desc": desc,
            "sponsor": r.get("sponsor","Co. Exec."),
            "committee": get_committee(desc),
            "status": status,
            "cp": cp or None,
            "sourceUrl": r.get("pdfUrl") or SEARCH_URL,
            "votes": build_votes(session, status),
        }

        if ir not in res_by_ir:
            res_by_ir[ir] = entry
            found_new += 1
        else:
            ex = res_by_ir[ir]
            # Update with better data from database
            if len(desc) > len(ex.get("desc","")):
                ex["desc"] = desc
                updated += 1
            if res_num and not ex.get("resNum"):
                ex["resNum"] = res_num
            if status != "Pending" and ex.get("status","Pending") == "Pending":
                ex["status"] = status
                ex["votes"] = build_votes(session, status)

    # ── STEP 3: Sort and save ─────────────────────────────────────────────────
    session_order = [s[0] for s in SESSION_DATES]

    def sort_key(r):
        try:
            si = session_order.index(r.get("session",""))
        except ValueError:
            si = 99
        ir = r.get("ir","")
        n = int(re.sub(r'\D','',ir) or 0)
        return (si, 0 if "PM" in ir else 1, n)

    all_res = sorted(res_by_ir.values(), key=sort_key)
    print(f"\nFinal count: {len(all_res)} resolutions ({found_new} new, {updated} updated)")

    output = {
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "totalResolutions": len(all_res),
        "meetings": meetings,
        "resolutions": all_res,
    }
    data_path.write_text(json.dumps(output, indent=2))
    print(f"Saved to {data_path}")

if __name__ == "__main__":
    run()
