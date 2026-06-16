# -*- coding: utf-8 -*-
"""
Created on Wed Apr 17 10:35:46 2024

@author: Jared.Strauch
"""
from tqdm import tqdm
import time
import traceback
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException
import pandas as pd
from datetime import datetime
import smtplib, ssl
from email.message import EmailMessage
from threading import Event
import re

from dotenv import load_dotenv
import os
from decorator import error_handle

def generator():
    while True:
        yield

is_in_production = os.getenv('ENVIRONMENT', 'production') != 'development'


def log_skip(inv_id, reason):
    """Append a per-case skip/stuck reason to case_skipping.txt for later review.

    Written to the repo root (same working dir as patients_to_skip.txt) so each
    run leaves a human-readable record of exactly which cases were not actioned
    and why.
    """
    try:
        with open("case_skipping.txt", "a", encoding="utf-8") as f:
            f.write(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {inv_id} - {reason}\n"
            )
    except Exception as e:
        print(f"log_skip failed for {inv_id}: {e}")


@error_handle
def start_anaplasma(username, passcode, login_complete: Event = None, is_logged_in=False):
    
    from .anaplasma import Anaplasma
    

    load_dotenv()

    # DRY_RUN walks the real queue and writes case_skipping.txt/logs but performs
    # NO production mutations: no ApproveNotification, no RejectNotification, no
    # emails. Used to validate the forward-progress fix safely. Enable with the
    # env var DRY_RUN=1 (or true/yes).
    dry_run = os.getenv("DRY_RUN", "").strip().lower() in ("1", "true", "yes")

    # NO_CASE_LIMIT removes the per-run iteration cap so the bot keeps reviewing
    # until the queue genuinely runs out of Anaplasma cases (detected via
    # consecutive no-case reads) instead of stopping after `limit` reviews.
    no_case_limit = os.getenv("NO_CASE_LIMIT", "").strip().lower() in ("1", "true", "yes")

    reviewed_ids = []
    what_do = []
    reason = []
    epi = []

    # Cumulative copies that are NEVER cleared by the periodic batch save, so a
    # complete results spreadsheet can always be written when the run ends --
    # including when it stops because the queue ran out of cases.
    all_reviewed_ids = []
    all_what_do = []
    all_reason = []
    all_epi = []

    # Environment is driven by .env (ENVIRONMENT=development -> test site).
    # Computed here, after load_dotenv() above, so it reflects .env rather than
    # only a shell variable. Defaults to production when ENVIRONMENT is unset.
    is_in_production = os.getenv('ENVIRONMENT', 'production') != 'development'
    print("entered?")
    NBS = Anaplasma(production=is_in_production)
    NBS.set_credentials(username, passcode)
    NBS.log_in(is_logged_in)
    login_complete.set()
    NBS.GoToApprovalQueue()
    
    patients_to_skip = set()
    error_list = []
    error = False
    n = 1
    gone_home = -1
    attempt_counter = 0
    consecutive_no_case_attempts = 0
    # A single flaky read of the condition cell (CheckFirstCase swallows
    # NoSuchElementException and sets condition=None) used to end the whole run
    # when this was 1. Require several consecutive empties before concluding the
    # queue is truly exhausted.
    max_consecutive_no_case_attempts = 3
    
    with open("patients_to_skip.txt", "r") as patient_reader:
        patients_to_skip |= set(patient_reader.readlines())

    # Sort queue first to get only Anaplasma cases
    paths = {
        "clear_filter_path":'//*[@id="removeFilters"]/a/font',
        "description_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/img',
        "clear_checkbox_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[2]/input',
        "click_ok_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[1]/input[1]',
        "click_cancel_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[1]/input[2]',
        "tests":["Anapla"],
        "submit_date_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[3]/a'
    }
    
    print("Sorting queue to filter for Anaplasma cases...")
    NBS.SortQueue(paths)
    
    # Count the number of Anaplasma cases in the queue
    print("Counting Anaplasma cases in queue...")
    try:
        # Get the case count element using the provided XPath
        case_count_element = NBS.find_element(By.XPATH, '//*[@id="bd"]/table[2]/tbody/tr/td/span[1]/b')
        case_count_text = case_count_element.text.strip()
        print(f"Case count text found: '{case_count_text}'")
        
        # Parse the count - Format: "Results 1 to 1 of 1" or "Results 1 to 16 of 45"
        match = re.search(r'Results\s+\d+\s+to\s+\d+\s+of\s+(\d+)', case_count_text)
        if match:
            anaplasma_case_count = int(match.group(1))
            print(f"Total Anaplasma cases in queue: {anaplasma_case_count}")
        else:
            raise ValueError(f"Could not parse count from: '{case_count_text}'")
    except Exception as e:
        print(f"Error getting case count: {e}")
        # Fallback: count table rows
        try:
            case_rows = NBS.find_elements(By.XPATH, '/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/tbody/tr')
            anaplasma_case_count = len(case_rows)
            print(f"Fallback: Found {anaplasma_case_count} case rows in table")
        except:
            # Ultimate fallback
            anaplasma_case_count = 16
            print("Could not determine case count, using default value of 16")
    
    # If SortQueue matched no Anaplasma condition option, the queue could not be
    # filtered to Anaplasma (the filter lists only conditions present), so NBS is
    # showing every case. The true Anaplasma count is 0 -- don't treat the
    # unfiltered total above as Anaplasma cases.
    if getattr(NBS, "condition_filter_matches", None) == 0:
        print("No 'Anaplasma' condition option in the queue filter; 0 cases.")
        anaplasma_case_count = 0

    # Check if there are any cases to process
    if anaplasma_case_count == 0:
        print("No Anaplasma cases found in queue. Exiting.")
        if not dry_run:
            NBS.SendAnaplasmaEmail("Anaplasma bot run completed - No cases in queue", "Status", "caleb.jones@maine.gov")
        with open("patients_to_skip.txt", "w") as patient_writer:
            patient_writer.write("\n".join(patients_to_skip) + "\n")
        return
    
    # Set limit and printAt based on actual case count
    limit = anaplasma_case_count
    printAt = min(16, anaplasma_case_count)
    if no_case_limit:
        # No cap: run until the queue is empty (the no-case detector ends it).
        limit = None
        print("NO_CASE_LIMIT set: ignoring iteration cap; will process the whole queue.")

    print(f"Set limit to {limit} and printAt to {printAt}")
    log_skip("=== RUN START ===", f"mode={'DRY-RUN' if dry_run else 'LIVE'}; cap={'NONE' if no_case_limit else limit}; {anaplasma_case_count} Anaplasma case(s) in queue")

    printNo = 1
    page = 1
    loop = tqdm(generator())
    
    for _ in loop:
        print(f"current limit: {limit}", "starting_iteration:", loop.n)
        
        #check if the bot has gone through the set limit of reviews
        if loop.n !=0 and loop.n % printAt == 0: 
            print(f"printing set {printNo}", reviewed_ids, reason)
            NBS.save_and_print_results("Anaplasma",
                {
                    'Inv ID': reviewed_ids,
                    'Action': what_do,
                    'Reason': reason,
                    'Epi': epi
                }, f"{printNo}r")
            printNo += 1
            reviewed_ids = []
            what_do = []
            reason = []
            epi = []
            print(f"sleeping for 2s after run {printNo - 1}")
            time.sleep(2)

        # Check if we've reached the limit OR if we've had too many consecutive attempts with no valid cases
        if (limit and loop.n == limit) or consecutive_no_case_attempts >= max_consecutive_no_case_attempts:
            if consecutive_no_case_attempts >= max_consecutive_no_case_attempts:
                print(f"No more valid cases found after {max_consecutive_no_case_attempts} consecutive attempts. Ending run.")
            # The complete results are written from the cumulative lists after
            # the loop (covers the no-case end and the limit end alike).
            break
            
        try:
            #Sort review queue so that only Anaplasma investigations are listed
            NBS.SortQueue(paths)
            print(f"sorting queue...: {NBS.queue_loaded}", "current_iteration:", loop.n)

            if NBS.queue_loaded:
                NBS.queue_loaded = None
                continue
            elif NBS.queue_loaded == False:
                NBS.queue_loaded = None
                print("failed to go to home, approval queue didn't load, breaking....", "current_iteration:", loop.n)
                break
            
            NBS.CheckFirstCase(n)
            print("checked first case", "current_iteration:", loop.n)
            
            if NBS.condition == 'Anaplasma phagocytophilum':
                # Reset consecutive no-case counter since we found a valid case
                consecutive_no_case_attempts = 0
                
                NBS.GoToNCaseInApprovalQueue(n)
                print(f"navigated to {n or "first"} case in queue", "current_iteration:", loop.n)
                if NBS.queue_loaded:
                    NBS.queue_loaded = None
                    continue
                    
                inv_id = NBS.find_element(By.XPATH,'//*[@id="bd"]/table[3]/tbody/tr[2]/td[1]/span[2]').text 
                print(f"present, {inv_id}", "current_iteration:", loop.n)
                
                if inv_id in patients_to_skip:
                    print(f"skipping, {inv_id}", "current_iteration:", loop.n)
                    log_skip(inv_id, "Present in patients_to_skip list")
                    NBS.ReturnApprovalQueue()
                    print("going to approval queue", "current_iteration:", loop.n)
                    n += 1
                    print("Making up for skipped case with increased limit...", "current_iteration:", loop.n)
                    continue
                
                NBS.StandardChecks()
                print("running standard checks", "current_iteration:", loop.n)

                if dry_run:
                    # Validation mode: determine the action that WOULD be taken,
                    # record it, and walk to the next row without mutating NBS or
                    # sending email. StandardChecks is read-only, so this is safe.
                    if not NBS.issues:
                        decision = "WOULD APPROVE (no issues)"
                    elif "Out of state - should be Not a Case." in NBS.issues:
                        decision = "WOULD APPROVE (out of state)"
                    else:
                        decision = f"WOULD REJECT. Issues: {' | '.join(NBS.issues)}"
                    print(f"[DRY-RUN] {inv_id}: {decision}", "current_iteration:", loop.n)
                    log_skip(inv_id, f"[DRY-RUN] {decision}")
                    reviewed_ids.append(inv_id)
                    what_do.append("DRY-RUN " + ("Approve" if "APPROVE" in decision else "Reject"))
                    reason.append(decision)
                    epi.append(NBS.investigator_name)
                    all_reviewed_ids.append(reviewed_ids[-1])
                    all_what_do.append(what_do[-1])
                    all_reason.append(reason[-1])
                    all_epi.append(epi[-1])
                    NBS.ReturnApprovalQueue()
                    n += 1  # advance: nothing left the queue, so move to next row
                    continue

                # Track whether this case was actually approved or rejected. If
                # it was not, the case stays in the queue at row `n`, so we must
                # advance past it instead of re-reading the same row forever.
                actioned = False
                if not NBS.issues or "Out of state - should be Not a Case." in NBS.issues:
                    reviewed_ids.append(inv_id)
                    what_do.append("Approve Notification")
                    reason.append("Approved")
                    epi.append(NBS.investigator_name)
                    all_reviewed_ids.append(reviewed_ids[-1])
                    all_what_do.append(what_do[-1])
                    all_reason.append(reason[-1])
                    all_epi.append(epi[-1])

                    NBS.ApproveNotification()
                    actioned = True
                    if "Out of state - should be Not a Case." not in NBS.issues:
                        NBS.SendAnaplasmaEmail("Out of state - should be Not a Case.", inv_id)
                    else:
                        NBS.SendAnaplasmaEmail("Hey, please don't change anything at all and just click CN", inv_id)
                    print("current run approved", "current_iteration:", loop.n)

                NBS.ReturnApprovalQueue()
                print("returning to approval queue..", "ending_iteration:", loop.n)
                if NBS.queue_loaded:
                    NBS.queue_loaded = None
                    continue

                # Only attempt a rejection for a case we did NOT already approve.
                if not actioned and len(NBS.issues) > 0:
                    NBS.SortQueue(paths)
                    print("sorting queue to check case at the top...", "current_iteration:", loop.n)

                    if NBS.queue_loaded:
                        NBS.queue_loaded = None
                        print("failed to go to home, skipping to approval queue....", "current_iteration:", loop.n)
                        continue

                    NBS.CheckFirstCase(n)
                    print("check for matching first case", "current_iteration:", loop.n)

                    NBS.final_name = NBS.patient_name

                    if NBS.final_name == NBS.initial_name:
                        print("issues seen on append:", NBS.issues, "current_iteration:", loop.n)

                        # Reject by the row we just verified. If the rejection
                        # itself fails, advance past the case rather than spin on
                        # it; record why in case_skipping.txt.
                        try:
                            NBS.RejectNotification(n)
                            actioned = True
                        except Exception as reject_error:
                            print(f"RejectNotification failed for {inv_id}: {reject_error}", "current_iteration:", loop.n)
                            log_skip(inv_id, f"RejectNotification failed: {reject_error}; advanced past case to avoid a re-review loop. Issues: {' | '.join(NBS.issues)}")
                            n += 1
                            NBS.GoToApprovalQueue()
                            continue

                        reviewed_ids.append(inv_id)
                        what_do.append("Reject Notification")
                        epi.append(NBS.investigator_name)
                        reason.append(' '.join(NBS.issues))
                        all_reviewed_ids.append(reviewed_ids[-1])
                        all_what_do.append(what_do[-1])
                        all_reason.append(reason[-1])
                        all_epi.append(epi[-1])

                        body = ''
                        if  all(case in NBS.issues  for case in ['City is blank.', 'County is blank.', 'Zip code is blank.']):
                            body = 'Hey, please only update City, Zip Code and County, then Click CN'
                        elif NBS.CorrectCaseStatus:
                            body = f'Hey, please only update the case status to {NBS.CorrectCaseStatus}, then click CN for this case.'
                        if body:
                            print('mail', body, "current_iteration:", loop.n)
                            NBS.SendAnaplasmaEmail(body, inv_id)
                        print("current iteration was rejected", "current_iteration:", loop.n)

                        NBS.GoToApprovalQueue()
                        print(f"returning approval queue....: {NBS.queue_loaded}", "ending_iteration:", loop.n)
                    else:
                        # The case at row n is no longer the one we reviewed, so
                        # rejecting row n would act on the WRONG case. Do not act;
                        # advance past it and record why it was left for a human.
                        print(f"here : {NBS.final_name} {NBS.initial_name}", "current_iteration:", loop.n)
                        print('Case at top of queue changed. No action was taken on the reviewed case.', "current_iteration:", loop.n)
                        NBS.num_fail += 1
                        log_skip(inv_id, f"Queue top changed after re-sort (expected '{NBS.initial_name}', saw '{NBS.final_name}'); advanced past case without acting to avoid acting on the wrong case. Issues: {' | '.join(NBS.issues) if NBS.issues else 'none'}")
                        n += 1
                        NBS.GoToApprovalQueue()
            else:
                # Increment consecutive no-case counter since we didn't find a valid Anaplasma case
                consecutive_no_case_attempts += 1
                print(f"No Anaplasma case found. Consecutive attempts: {consecutive_no_case_attempts}/{max_consecutive_no_case_attempts}", "current_iteration:", loop.n)
                
                if attempt_counter < NBS.num_attempts:
                    attempt_counter += 1
                else:
                    attempt_counter = 0
                    print("No Anaplasma cases in notification queue.", "current_iteration:", loop.n)
                    if consecutive_no_case_attempts >= max_consecutive_no_case_attempts:
                        print("Maximum consecutive no-case attempts reached. Ending run.")
                        log_skip(
                            "=== RUN END (no more cases) ===",
                            f"Row {n} read condition '{NBS.condition}' (not Anaplasma) for "
                            f"{max_consecutive_no_case_attempts} consecutive checks; ending run. "
                            f"Any cases past row {n} were not reviewed this run.",
                        )
                        break
                        
        except Exception as e:
            error_list.append(str(e))
            error = True
            print(f"Exception occurred: {str(e)}", "current_iteration:", loop.n)
            
    print("ending, printing, saving", "current_iteration:", loop.n)

    # Final save of ALL results reviewed this run (cumulative lists are never
    # cleared by the periodic batch save), so the spreadsheet is complete
    # whenever the bot ends -- including when it stops because the queue ran out
    # of cases.
    if len(all_reviewed_ids) > 0:
        NBS.save_and_print_results("Anaplasma",
            {
                'Inv ID': all_reviewed_ids,
                'Action': all_what_do,
                'Reason': all_reason,
                'Epi': all_epi
            }, "final")
        log_skip(
            "=== RUN END ===",
            f"reviewed {len(all_reviewed_ids)} case(s); results written to "
            f"saved/Anaplasma/Anaplasma_bot_activity_final_<date>.xlsx",
        )
    else:
        print("No results to save.")
        log_skip("=== RUN END ===", "no cases reviewed this run")
    
    if not dry_run:
        NBS.SendAnaplasmaEmail("Anaplasma bot run completed", "Status", "caleb.jones@maine.gov")

    with open("patients_to_skip.txt", "w") as patient_writer:
        patient_writer.write("\n".join(patients_to_skip) + "\n")

    if error: 
        raise Exception(error_list)

if __name__ == '__main__':
    start_anaplasma()