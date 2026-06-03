import json, re, sys, time
from datetime import datetime, timezone
from pathlib import Path

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
YEAR = "2026"
LOT_INDEX_URL = "https://www.scnylegislature.us/661/Laid-on-the-Table-Resolutions-LOT"
SEARCH_URL = "https://apps2.suffolkcountyny.gov/legislature/ressearch/Results.aspx"

ALL_LEGS = ["doroski","welker","mazzarella","caracappa","englebright","lennon","thorne",
            "piccirillo","gonzalez","bergin","flotteron","kennedy","formica","renna",
            "richberg","sanin","donnelly","bontempi"]

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

# Session date ranges for assigning session labels
SESSION_DATES = [
    ("Jan 5, 2026",  "2026-01-01", "2026-01-31"),
    ("Feb 3, 2026",  "2026-02-01", "2026-02-28"),
    ("Mar 10, 2026", "2026-03-01", "2026-03-31"),
    ("Apr 21, 2026", "2026-04-01", "2026-04-30"),
    ("May 12, 2026", "2026-05-01", "2026-05-31"),
]

def get_session(lot_date):
    """Map a LOT date to a session label."""
    if not lot_date:
        return "2026"
    for label, start, end in SESSION_DATES:
        if start <= lot_date <= end:
            return label
    return "2026"

def get_committee(desc):
    d = desc.lower()
    if any(k in d for k in ["police","sheriff","jail","correctional","district attorney","probation","firearm","crime","criminal","narcotics"]): return "Public Safety"
    if any(k in d for k in ["park","farmland","environment","wetland","agriculture","golf course","marina","open space","drinking water","conservation","beach","preserve"]): return "Environment, Parks & Agriculture"
    if any(k in d for k in ["road","highway","bridge","transit","bus","transportation","sewer","drainage","airport","ferry","traffic","signal"]): return "Public Works, Transportation & Energy"
    if any(k in d for k in ["housing","affordable","workforce","economic","industrial","waterfront","development","planning","jumpstart","ida ","industrial development"]): return "Economic Dev, Planning & Housing"
    if any(k in d for k in ["health","mental","substance","addiction","medical","nursing","hospital","clinic","wic ","oasas","medicaid","behavioral"]): return "Health"
    if any(k in d for k in ["senior","aging","youth","human service","nutrition","child care","day care","family"]): return "Seniors & Human Services"
    if any(k in d for k in ["veteran","military","armed forces"]): return "Veterans"
    if any(k in d for k in ["education","labor","consumer","human rights","licensing board","college","workforce training","apprentice"]): return "Education, Labor, Consumer Affairs"
    if any(k in d for k in ["fire","rescue"," ems ","emergency service","aed","hazmat","911","dispatch"]): return "Fire, Rescue & EMS"
    if any(k in d for k in ["technology","personnel","salary","software","network","computer","information tech","payroll","classification plan"]): return "Govt Operations, Info Tech"
    if any(k in d for k in ["budget","finance","appropriat","fund transfer","operating budget","capital budget","refund","chargeback","bond","serial bond"]): return "Budget & Finance"
    if any(k in d for k in ["sale","conveyance","tax act","mortgage","comptroller","insurance","settlement","reconveyance","county clerk","deed","property tax"]): return "Ways & Means"
    return "General"

def fetch_url(url, params=None, method="GET", data=None, headers=None):
    """Fetch a URL, return response text."""
    import urllib.request, urllib.parse
    if headers is None:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    if data:
        data = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  ERROR fetching {url}: {e}", file=sys.stderr)
        return ""

def search_resolutions_db(year, ir_start=None, ir_end=None):
    """
    Query the Suffolk County legislation search database.
    Returns list of dicts with ir, resNum, title, sponsor, lotDate.
    """
    results = []

    # The search form submits to Results.aspx
    # We search by year and iterate through IR number ranges
    base_params = {
        "txtIRYear": year,
        "txtIRNumber": "",
        "txtResNumber": "",
        "txtLOTDate": "",
        "ddlSponsor": "",
        "txtTitle": "",
    }

    print(f"  Querying legislation database for year {year}...")
    html = fetch_url(SEARCH_URL, params=base_params)

    if not html:
        print("  Could not reach legislation database", file=sys.stderr)
        return results

    # Parse the HTML table of results
    results = parse_search_results(html, year)
    print(f"  Database returned {len(results)} results")

    # If we got results and there are more pages, handle pagination
    if results:
        page = 2
        while True:
            # Check for "next page" link
            if 'Page$' not in html and f'>{page}<' not in html:
                break
            # Try to get next page via __doPostBack
            next_html = fetch_next_page(html, page)
            if not next_html or next_html == html:
                break
            new_results = parse_search_results(next_html, year)
            if not new_results:
                break
            results.extend(new_results)
            html = next_html
            page += 1
            time.sleep(0.5)
            if page > 20:  # safety limit
                break

    return results

def parse_search_results(html, year):
    """Parse the HTML search results table."""
    results = []

    # Look for table rows with resolution data
    # The table typically has columns: IR#, Res#, Date, Sponsor, Title
    row_pattern = re.compile(
        r'<tr[^>]*>.*?</tr>', re.DOTALL | re.IGNORECASE
    )
    cell_pattern = re.compile(r'<td[^>]*>(.*?)</td>', re.DOTALL | re.IGNORECASE)
    tag_pattern = re.compile(r'<[^>]+>')

    def strip_tags(html_text):
        return re.sub(r'\s+', ' ', tag_pattern.sub('', html_text)).strip()

    rows = row_pattern.findall(html)
    for row in rows:
        cells = cell_pattern.findall(row)
        if len(cells) < 3:
            continue

        cell_texts = [strip_tags(c) for c in cells]

        # Skip header rows
        if any(h in cell_texts[0].lower() for h in ['ir #', 'intro', 'title', 'sponsor', 'header']):
            continue

        # Try to identify columns
        # Common format: IR Year | IR# | Res# | Date | Sponsor | Title
        # or: IR# | Res# | Date | Sponsor | Title
        ir_num = None
        res_num = None
        lot_date = None
        sponsor = "Co. Exec."
        title = ""

        for i, text in enumerate(cell_texts):
            text = text.strip()
            if not text:
                continue
            # IR number: 3-4 digits, possibly with year prefix
            if re.match(r'^\d{3,4}$', text) and not ir_num:
                ir_num = text
            elif re.match(r'^\d{1,3}$', text) and ir_num and not res_num:
                res_num = text
            elif re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', text):
                lot_date = text
            elif len(text) > 20 and not title:
                title = text
            elif 5 < len(text) <= 30 and title:
                # Might be sponsor
                if not any(c.isdigit() for c in text):
                    sponsor = text

        if ir_num and title:
            # Parse date to YYYY-MM-DD
            parsed_date = None
            if lot_date:
                try:
                    m, d, y = lot_date.split('/')
                    parsed_date = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
                except:
                    pass

            results.append({
                "ir": ir_num,
                "resNum": res_num,
                "lotDate": parsed_date,
                "sponsor": sponsor,
                "title": title,
            })

    return results

def fetch_next_page(html, page_num):
    """Attempt to get the next page of search results via form resubmission."""
    # Extract viewstate and eventvalidation for ASP.NET postback
    vs_match = re.search(r'__VIEWSTATE[^"]*"\s+value="([^"]+)"', html)
    ev_match = re.search(r'__EVENTVALIDATION[^"]*"\s+value="([^"]+)"', html)

    if not vs_match:
        return None

    import urllib.parse
    data = {
        "__EVENTTARGET": f"ctl00$ContentPlaceHolder1$GridView1",
        "__EVENTARGUMENT": f"Page${page_num}",
        "__VIEWSTATE": vs_match.group(1),
        "__EVENTVALIDATION": ev_match.group(1) if ev_match else "",
        "ctl00$ContentPlaceHolder1$txtIRYear": YEAR,
        "ctl00$ContentPlaceHolder1$txtIRNumber": "",
        "ctl00$ContentPlaceHolder1$txtResNumber": "",
        "ctl00$ContentPlaceHolder1$txtLOTDate": "",
        "ctl00$ContentPlaceHolder1$ddlSponsor": "",
        "ctl00$ContentPlaceHolder1$txtTitle": "",
    }

    return fetch_url(SEARCH_URL, data=data, method="POST")

def check_lot_index_for_new_pdfs(existing_urls):
    """Check the LOT index page for any new PDF URLs not in our existing set."""
    html = fetch_url(LOT_INDEX_URL)
    if not html:
        return []

    # Find all PDF links for 2026
    pdf_links = re.findall(
        r'href="(https://www\.scnylegislature\.us/DocumentCenter/View/\d+/[^"]+(?:Laid-on-the-Table|Marked-Agenda|Minutes)[^"]*)"',
        html, re.IGNORECASE
    )

    new_urls = []
    for url in pdf_links:
        if url not in existing_urls and "2026" in url:
            new_urls.append(url)
            print(f"  Found new document: {url}")

    return new_urls

def build_votes(absent, status):
    if status not in ("Adopted", "Tabled", "Failed"):
        return None
    return {l: ("NP" if l in absent else "Y") for l in ALL_LEGS}

# Session → absent legislators mapping
SESSION_ABSENT = {
    "Jan 5, 2026": [],
    "Feb 3, 2026": ["richberg", "gonzalez", "kennedy"],
    "Mar 10, 2026": [],
    "Apr 21, 2026": [],
    "May 12, 2026": [],
}

# Known vote outcomes from marked agendas
# Format: ir_num -> {"status": "Adopted/Tabled/Failed", "resNum": "123"}
KNOWN_VOTES = {
    "1038": {"status":"Adopted","resNum":"102"},
    "1039": {"status":"Adopted","resNum":"133"},
    "1044": {"status":"Adopted","resNum":"187"},
    "1045": {"status":"Adopted","resNum":"94"},
    "1046": {"status":"Adopted","resNum":"95"},
    "1051": {"status":"Adopted","resNum":"96"},
    "1052": {"status":"Adopted","resNum":"205"},
    "1053": {"status":"Adopted","resNum":"97"},
    "1054": {"status":"Adopted","resNum":"114"},
    "1055": {"status":"Adopted","resNum":"178"},
    "1056": {"status":"Adopted","resNum":"122"},
    "1057": {"status":"Adopted","resNum":"103"},
    "1058": {"status":"Tabled","resNum":None},
    "1059": {"status":"Adopted","resNum":"116"},
    "1060": {"status":"Adopted","resNum":"104"},
    "1061": {"status":"Adopted","resNum":"105"},
    "1062": {"status":"Adopted","resNum":"106"},
    "1063": {"status":"Adopted","resNum":"107"},
    "1064": {"status":"Adopted","resNum":"108"},
    "1065": {"status":"Adopted","resNum":None},
    "1066": {"status":"Adopted","resNum":"138"},
    "1067": {"status":"Adopted","resNum":"139"},
    "1068": {"status":"Adopted","resNum":"140"},
    "1069": {"status":"Adopted","resNum":"141"},
    "1070": {"status":"Adopted","resNum":"109"},
    "1071": {"status":"Adopted","resNum":"98"},
    "1072": {"status":"Adopted","resNum":"110"},
    "1073": {"status":"Adopted","resNum":"143"},
    "1163": {"status":"Adopted","resNum":"209"},
    "1169": {"status":"Adopted","resNum":"247"},
    "1170": {"status":"Adopted","resNum":"248"},
    "1192": {"status":"Adopted","resNum":"303"},
    "1202": {"status":"Adopted","resNum":"315"},
    "1203": {"status":"Adopted","resNum":"317"},
    "1221": {"status":"Adopted","resNum":"292"},
    "1237": {"status":"Adopted","resNum":None},
    "1241": {"status":"Adopted","resNum":"73"},
    "1258": {"status":"Adopted","resNum":"90"},
    "1262": {"status":"Adopted","resNum":"274"},
    "1281": {"status":"Adopted","resNum":"336"},
}

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
        existing = {"resolutions": [], "meetings": MEETINGS_META}

    res_by_ir = {r["ir"]: r for r in existing.get("resolutions", [])}
    found_new = 0
    updated = 0

    # ── STEP 1: Query the legislation search database ──────────────────────────
    print("\n=== Querying Legislation Database ===")
    db_results = search_resolutions_db(YEAR)

    for r in db_results:
        ir = r["ir"]
        session = get_session(r.get("lotDate",""))
        absent = SESSION_ABSENT.get(session, [])

        # Apply known vote outcomes
        known = KNOWN_VOTES.get(ir, {})
        status = known.get("status", "Pending")
        res_num = known.get("resNum") or r.get("resNum")

        desc = r["title"]
        rtype = "pm" if ir.startswith("PM") else "ll" if "local law" in desc.lower() else "lot"
        cp = re.findall(r'CP\s*(\d{3,4})', desc, re.I)

        entry = {
            "ir": ir,
            "resNum": res_num,
            "type": rtype,
            "session": session,
            "desc": desc,
            "sponsor": r.get("sponsor", "Co. Exec."),
            "committee": get_committee(desc),
            "status": status,
            "cp": cp or None,
            "sourceUrl": f"https://apps2.suffolkcountyny.gov/legislature/ressearch/",
            "votes": build_votes(absent, status),
        }

        if ir not in res_by_ir:
            res_by_ir[ir] = entry
            found_new += 1
        else:
            ex = res_by_ir[ir]
            # Update with better data
            if len(desc) > len(ex.get("desc", "")):
                ex["desc"] = desc
                updated += 1
            if res_num and not ex.get("resNum"):
                ex["resNum"] = res_num
            if status != "Pending" and ex.get("status") == "Pending":
                ex["status"] = status
                ex["votes"] = build_votes(absent, status)

    # ── STEP 2: Check for new LOT PDFs on the index page ───────────────────────
    print("\n=== Checking LOT Index for New Documents ===")
    existing_urls = {d["url"] for m in existing.get("meetings", []) for d in m.get("docs", [])}
    new_pdf_urls = check_lot_index_for_new_pdfs(existing_urls)
    if new_pdf_urls:
        print(f"  Found {len(new_pdf_urls)} new document URLs to process next run")
    else:
        print("  No new documents found")

    # ── STEP 3: Sort and save ──────────────────────────────────────────────────
    session_order = [s[0] for s in SESSION_DATES]
    def sort_key(r):
        try: si = session_order.index(r.get("session",""))
        except ValueError: si = 99
        ir = r.get("ir","")
        n = int(re.sub(r'\D','',ir) or 0)
        return (si, 0 if 'PM' in ir else 1, n)

    all_res = sorted(res_by_ir.values(), key=sort_key)
    print(f"\nFinal: {len(all_res)} resolutions ({found_new} new, {updated} updated)")

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
