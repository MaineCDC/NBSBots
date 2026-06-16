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
from threading import Event
import pandas as pd
from datetime import datetime
import smtplib, ssl
from email.message import EmailMessage
import re

from dotenv import load_dotenv
import os
from decorator import error_handle

def generator():
    while True:
        yield

is_in_production = os.getenv('ENVIRONMENT', 'production') != 'development'


def log_skip(inv_id, reason):
    """Append a per-case record line to case_skipping.txt for later review.

    Written to the repo root (same working dir as patients_to_skip.txt) so each
    run leaves a human-readable record of exactly what the bot saw and what it
    would have done -- without ever actioning a case.
    """
    try:
        with open("case_skipping.txt", "a", encoding="utf-8") as f:
            f.write(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {inv_id} - {reason}\n"
            )
    except Exception as e:
        print(f"log_skip failed for {inv_id}: {e}")


def would_be_note(NBS):
    """Reproduce the email body the live bot WOULD submit for a reject case.

    Mirrors the body logic in the live reject path so the dry-run record
    captures the exact note that would have been sent to disease.reporting.
    Returns '' when no specific note would be sent.
    """
    if all(case in NBS.issues for case in ['City is blank.', 'County is blank.', 'Zip code is blank.']):
        return 'Hey, please only update City, Zip Code and County, then Click CN'
    if getattr(NBS, "CorrectCaseStatus", None):
        return f'Hey, please only update the case status to {NBS.CorrectCaseStatus}, then click CN for this case.'
    return ''


@error_handle
def start_babesia(username, passcode, login_complete: Event = None, is_logged_in=False):

    from .babesia import Babesia

    load_dotenv()

    # Babesia is still in testing. By default the bot runs in RECORD-ONLY mode:
    # it walks the real queue and reviews every Babesia case, recording the
    # action it WOULD take and the note it WOULD submit, but performs NO
    # mutations -- no ApproveNotification, no RejectNotification, no emails. This
    # leaves the queue untouched so the same cases can be reviewed again on the
    # next run. Set DRY_RUN=0 (or false/no) to promote to live actioning.
    dry_run = os.getenv("DRY_RUN", "true").strip().lower() not in ("0", "false", "no")

    reviewed_ids = []
    what_do = []
    reason = []
    note = []
    epi = []
    check_errors = []

    # Babesia is still in testing -> run against the NBS test site (InductiveHealth
    # / Maine DHHS SSO). Flip to production=True when promoting to production.
    NBS = Babesia(production=False)
    NBS.set_credentials(username, passcode)
    NBS.log_in(is_logged_in)
    if login_complete is not None:
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
    # NoSuchElementException and sets condition=None) shouldn't end the whole
    # run. Require several consecutive empties before concluding the queue is
    # truly exhausted.
    max_consecutive_no_case_attempts = 3

    with open("patients_to_skip.txt", "r") as patient_reader:
        patients_to_skip |= set(patient_reader.readlines())

    # Sort queue first to get only Babesia cases
    paths = {
        "clear_filter_path":'//*[@id="removeFilters"]/a/font',
        "description_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/img',
        "clear_checkbox_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[2]/input',
        "click_ok_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[1]/input[1]',
        "click_cancel_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[1]/input[2]',
        "tests":["Babesiosis"],
        "submit_date_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[3]/a'
    }

    print("Sorting queue to filter for Babesia cases...")
    NBS.SortQueue(paths)

    # Count the number of Babesia cases in the queue
    print("Counting Babesia cases in queue...")

    babesia_case_count = NBS.disease_case_count("Babesia", 16)
    # Check if there are any cases to process
    if babesia_case_count == 0:
        print("No Babesia cases found in queue. Exiting.")
        if not dry_run:
            NBS.SendAnaplasmaEmail("Babesia bot run completed - No cases in queue", "Status", "caleb.jones@maine.gov")
        with open("patients_to_skip.txt", "w") as patient_writer:
            patient_writer.write("\n".join(patients_to_skip) + "\n")
        return

    # Set limit and printAt based on actual case count
    limit = babesia_case_count
    printAt = min(16, babesia_case_count)

    print(f"Set limit to {limit} and printAt to {printAt}")
    log_skip("=== RUN START ===", f"mode={'RECORD-ONLY' if dry_run else 'LIVE'}; {babesia_case_count} Babesia case(s) in queue")

    printNo = 1
    page = 1
    loop = tqdm(generator())

    for _ in loop:
        print(f"current limit: {limit}", "starting_iteration:", loop.n)

        #check if the bot has gone through the set limit of reviews
        if loop.n != 0 and loop.n % printAt == 0:
            print(f"printing set {printNo}", reviewed_ids, reason)
            NBS.save_and_print_results("Babesia",
                {
                    'Inv ID': reviewed_ids,
                    'Action': what_do,
                    'Reason': reason,
                    'Note': note,
                    'Epi': epi,
                    'Check Errors': check_errors
                }, f"{printNo}r")
            printNo += 1
            reviewed_ids = []
            what_do = []
            reason = []
            note = []
            epi = []
            check_errors = []
            print(f"sleeping for 2s after run {printNo - 1}")
            time.sleep(2)

        # Check if we've reached the limit OR if we've had too many consecutive attempts with no valid cases
        if (limit and loop.n == limit) or consecutive_no_case_attempts >= max_consecutive_no_case_attempts:
            if consecutive_no_case_attempts >= max_consecutive_no_case_attempts:
                print(f"No more valid cases found after {max_consecutive_no_case_attempts} consecutive attempts. Ending run.")

            # Save any remaining results
            if len(reviewed_ids) > 0:
                NBS.save_and_print_results("Babesia",
                    {
                        'Inv ID': reviewed_ids,
                        'Action': what_do,
                        'Reason': reason,
                        'Note': note,
                        'Epi': epi,
                        'Check Errors': check_errors
                    }, "final")
            else:
                print("No cases processed in final batch.")
            break

        try:
            #Sort review queue so that only Babesia investigations are listed
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

            if NBS.condition == 'Babesiosis':
                # Reset consecutive no-case counter since we found a valid case
                consecutive_no_case_attempts = 0

                NBS.GoToNCaseInApprovalQueue(n)
                print(f"navigated to {n or 'first'} case in queue", "current_iteration:", loop.n)
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

                # Decide the action the live bot WOULD take. StandardChecks is
                # read-only, so this analysis never mutates the case.
                if not NBS.issues or "Out of state - should be Not a Case." in NBS.issues:
                    action = "Approve Notification"
                    case_reason = "Approved"
                    # The approve path's note depends on whether the case is the
                    # out-of-state special case or a clean approval.
                    if "Out of state - should be Not a Case." in NBS.issues:
                        case_note = "Out of state - should be Not a Case."
                    else:
                        case_note = "Hey, please don't change anything at all and just click CN"
                else:
                    action = "Reject Notification"
                    case_reason = ' '.join(NBS.issues)
                    case_note = would_be_note(NBS)

                if dry_run:
                    # RECORD-ONLY: log what we WOULD do, record it for the
                    # spreadsheet, then walk to the next row WITHOUT actioning
                    # the case. Nothing leaves the queue, so advance n so we
                    # don't re-read the same row forever.
                    decision = f"WOULD {action.split()[0].upper()}"
                    if action.startswith("Reject"):
                        decision += f". Issues: {case_reason}"
                        if case_note:
                            decision += f" || Note: {case_note}"
                    print(f"[RECORD-ONLY] {inv_id}: {decision}", "current_iteration:", loop.n)
                    log_skip(inv_id, f"[RECORD-ONLY] {decision}")

                    reviewed_ids.append(inv_id)
                    what_do.append(action)
                    reason.append(case_reason)
                    note.append(case_note)
                    epi.append(NBS.investigator_name)
                    check_errors.append(' | '.join(getattr(NBS, "check_errors", [])))

                    NBS.ReturnApprovalQueue()
                    n += 1  # advance: nothing left the queue, so move to next row
                    continue

                # ---- LIVE path (DRY_RUN disabled): actually action the case ----
                actioned = False
                if action == "Approve Notification":
                    reviewed_ids.append(inv_id)
                    what_do.append(action)
                    reason.append(case_reason)
                    note.append(case_note)
                    epi.append(NBS.investigator_name)
                    check_errors.append(' | '.join(getattr(NBS, "check_errors", [])))

                    NBS.ApproveNotification()
                    actioned = True
                    NBS.SendAnaplasmaEmail(case_note, inv_id)
                    print("current run approved", "current_iteration:", loop.n)

                NBS.ReturnApprovalQueue()
                print("returning to approval queue..", "ending_iteration:", loop.n)
                if NBS.queue_loaded:
                    NBS.queue_loaded = None
                    continue

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
                        reviewed_ids.append(inv_id)
                        what_do.append("Reject Notification")
                        epi.append(NBS.investigator_name)
                        reason.append(case_reason)
                        note.append(case_note)
                        check_errors.append(' | '.join(getattr(NBS, "check_errors", [])))
                        print("issues seen on append:", NBS.issues, "current_iteration:", loop.n)

                        NBS.RejectNotification(n)
                        if case_note:
                            print('mail', case_note, "current_iteration:", loop.n)
                            NBS.SendAnaplasmaEmail(case_note, inv_id)
                        print("current iteration was rejected", "current_iteration:", loop.n)

                        NBS.GoToApprovalQueue()
                        print(f"returning approval queue....: {NBS.queue_loaded}", "ending_iteration:", loop.n)
                    elif NBS.final_name != NBS.initial_name:
                        print(f"here : {NBS.final_name} {NBS.initial_name}", "current_iteration:", loop.n)
                        print('Case at top of queue changed. No action was taken on the reviewed case.', "current_iteration:", loop.n)
                        NBS.num_fail += 1
            else:
                # Increment consecutive no-case counter since we didn't find a valid Babesia case
                consecutive_no_case_attempts += 1
                print(f"No Babesia case found. Consecutive attempts: {consecutive_no_case_attempts}/{max_consecutive_no_case_attempts}", "current_iteration:", loop.n)

                if attempt_counter < NBS.num_attempts:
                    attempt_counter += 1
                else:
                    attempt_counter = 0
                    print("No Babesia cases in notification queue.", "current_iteration:", loop.n)
                    if consecutive_no_case_attempts >= max_consecutive_no_case_attempts:
                        print("Maximum consecutive no-case attempts reached. Ending run.")
                        break

        except Exception as e:
            error_list.append(str(e))
            error = True
            print(f"Exception occurred: {str(e)}", "current_iteration:", loop.n)

    print("ending, printing, saving", "current_iteration:", loop.n)

    # Final save of any remaining results
    if len(reviewed_ids) > 0:
        NBS.save_and_print_results("Babesia",
            {
                'Inv ID': reviewed_ids,
                'Action': what_do,
                'Reason': reason,
                'Note': note,
                'Epi': epi,
                'Check Errors': check_errors
            }, "final")
    else:
        print("No final results to save.")

    if not dry_run:
        NBS.SendAnaplasmaEmail("Babesia bot run completed", "Status", "caleb.jones@maine.gov")

    with open("patients_to_skip.txt", "w") as patient_writer:
        patient_writer.write("\n".join(patients_to_skip) + "\n")

    if error:
        raise Exception(error_list)

if __name__ == '__main__':
    start_babesia()
