"""Diagnostic: for each Babesiosis case, print the investigation's Date
Specimen Collected (ME8117) alongside the associated lab report table's
Date Collected / Date Received columns, so we can see whether the
"Specimen collection dates do not match dates on lab" finding is real."""
import os
from io import StringIO
from bs4 import BeautifulSoup
import pandas as pd
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

if __name__ == "__main__":
    launch_chrome()
    NBS = Babesia(production=False)
    NBS.set_credentials(os.getenv("BABESIA_USER", "x"), os.getenv("BABESIA_PASS", "x"))
    NBS.log_in(False)
    NBS.GoToApprovalQueue()

    for row in (1, 2):
        NBS.SortQueue(PATHS)
        NBS.CheckFirstCase(row)
        if NBS.condition != "Babesiosis":
            print(f"row {row}: not Babesiosis ({NBS.condition}); stop")
            break
        NBS.GoToNCaseInApprovalQueue(row)
        inv_id = NBS.find_element(By.XPATH, '//*[@id="bd"]/table[3]/tbody/tr[2]/td[1]/span[2]').text

        specimen = NBS.ReadText('//*[@id="ME8117"]')
        print("=" * 80)
        print(f"CASE {inv_id}")
        print(f"  Investigation 'Date Specimen Collected' (ME8117): {specimen!r}")
        try:
            html = NBS.find_element(By.XPATH, '//*[@id="eventLabReport"]').get_attribute("outerHTML")
            lab = pd.read_html(StringIO(str(BeautifulSoup(html, "html.parser"))))[0]
            cols = [c for c in ["Date Received", "Date Collected", "Test Results"] if c in lab.columns]
            print(f"  Associated lab report table ({len(lab)} row(s)):")
            print(lab[cols].to_string(index=False) if cols else lab.to_string(index=False))
        except Exception as e:
            print(f"  could not read lab table: {e}")
        NBS.ReturnApprovalQueue()
