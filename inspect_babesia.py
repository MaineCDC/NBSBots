"""Diagnostic: open the first Babesiosis case on the NBS test site and dump the
real form field ids + their question labels, so we can see which xpaths in
babesia.py are pointed at the wrong (or nonexistent) element ids.

Test-site login is Maine DHHS SSO over VPN (no RSA passcode used), so creds here
are placeholders. Writes a full field map to babesia_form_dump.txt and prints the
rows that matter for the currently-broken checks.
"""
import os
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By

from start_bots import launch_chrome
from babesia_files.babesia import Babesia

PATHS = {
    "clear_filter_path": '//*[@id="removeFilters"]/a/font',
    "description_path": '/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/img',
    "clear_checkbox_path": '/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[2]/input',
    "click_ok_path": '/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[1]/input[1]',
    "click_cancel_path": '/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[1]/input[2]',
    "tests": ["Babesiosis"],
    "submit_date_path": '/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[3]/a',
}

# Labels we care about for the currently-failing / suspect checks.
KEYWORDS = [
    "organ", "blood", "donat", "transfus", "transplant", "splenect", "asplen",
    "immuno", "co-infection", "coinfection", "fatigue", "malaise",
    "investigator", "leukopenia", "transaminase", "crp",
]


def row_label(tag):
    """Best-effort question label for a tagged value element: walk up to the
    enclosing table row and return its collapsed text."""
    tr = tag.find_parent("tr")
    if tr is None:
        return ""
    return " ".join(tr.get_text(" ", strip=True).split())


def dump(NBS, tab_name):
    soup = BeautifulSoup(NBS.page_source, "html.parser")
    rows = []
    seen = set()
    for tag in soup.find_all(attrs={"id": True}):
        _id = tag.get("id")
        if _id in seen:
            continue
        seen.add(_id)
        label = row_label(tag)
        if not label:
            continue
        rows.append((_id, tag.name, label))
    return rows


if __name__ == "__main__":
    print("launching chrome...")
    launch_chrome()

    NBS = Babesia(production=False)
    NBS.set_credentials(os.getenv("BABESIA_USER", "x"), os.getenv("BABESIA_PASS", "x"))
    print("logging in (SSO)...")
    NBS.log_in(False)
    NBS.GoToApprovalQueue()

    print("sorting for Babesiosis...")
    NBS.SortQueue(PATHS)
    NBS.CheckFirstCase(1)
    print("condition at row 1:", NBS.condition)
    NBS.GoToNCaseInApprovalQueue(1)

    inv_id = NBS.find_element(By.XPATH, '//*[@id="bd"]/table[3]/tbody/tr[2]/td[1]/span[2]').text
    print("inspecting case:", inv_id)

    all_rows = []
    # Demographics / main tab as loaded
    all_rows += [("MAIN",) + r for r in dump(NBS, "MAIN")]
    # Tickborne / Babesiosis tab
    try:
        NBS.GoToBabesiosis()
        all_rows += [("TICKBORNE",) + r for r in dump(NBS, "TICKBORNE")]
    except Exception as e:
        print("could not open Babesiosis tab:", e)
    # Supplemental tab
    try:
        NBS.GoToSupplemental()
        all_rows += [("SUPPLEMENTAL",) + r for r in dump(NBS, "SUPPLEMENTAL")]
    except Exception as e:
        print("could not open Supplemental tab:", e)

    with open("babesia_form_dump.txt", "w", encoding="utf-8") as f:
        f.write(f"Field map for {inv_id}\n")
        f.write("TAB | ID | tag | row label\n")
        f.write("=" * 80 + "\n")
        for tab, _id, name, label in all_rows:
            f.write(f"{tab} | {_id} | {name} | {label[:160]}\n")

    print(f"\nWrote {len(all_rows)} fields to babesia_form_dump.txt\n")
    print("==== ROWS MATCHING BROKEN/SUSPECT CHECKS ====")
    for tab, _id, name, label in all_rows:
        low = label.lower()
        if any(k in low for k in KEYWORDS):
            print(f"[{tab}] id={_id:<12} {label[:120]}")
