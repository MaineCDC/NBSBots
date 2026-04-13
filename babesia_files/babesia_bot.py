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
import re

from dotenv import load_dotenv
import os
from decorator import error_handle

def generator():
    while True:
        yield

is_in_production = os.getenv('ENVIRONMENT', 'production') != 'development'


@error_handle
def start_babesia(username, passcode):
    
    from .babesia import Babesia
    

    load_dotenv()
    
    reviewed_ids = []
    what_do = []
    reason = []
    epi = []

    NBS = Babesia(production=True)
    NBS.set_credentials(username, passcode)
    NBS.log_in()
    NBS.GoToApprovalQueue()
    
    patients_to_skip = set()
    error_list = []
    error = False
    n = 1
    gone_home = -1
    attempt_counter = 0
    consecutive_no_case_attempts = 0
    max_consecutive_no_case_attempts = 1
    
    with open("patients_to_skip.txt", "r") as patient_reader:
        patients_to_skip |= set(patient_reader.readlines())

    # Sort queue first to get only Anaplasma cases
    paths = {
        "clear_filter_path":'//*[@id="removeFilters"]/a/font',
        "description_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/img',
        "clear_checkbox_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[2]/input',
        "click_ok_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[1]/input[1]',
        "click_cancel_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[1]/input[2]',
        "tests":["Babesia"],
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
        NBS.SendAnaplasmaEmail("Babesia bot run completed - No cases in queue", "Status", "caleb.jones@maine.gov")
        with open("patients_to_skip.txt", "w") as patient_writer:
            patient_writer.write("\n".join(patients_to_skip) + "\n")
        return
    
    # Set limit and printAt based on actual case count
    limit = babesia_case_count
    printAt = min(16, babesia_case_count)
    
    print(f"Set limit to {limit} and printAt to {printAt}")
    
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
            
            # Save any remaining results
            if len(reviewed_ids) > 0:
                NBS.save_and_print_results("Babesia", 
                    {
                        'Inv ID': reviewed_ids,
                        'Action': what_do,
                        'Reason': reason,
                        'Epi': epi
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
            
            if NBS.condition == 'Babesia':
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
                    NBS.ReturnApprovalQueue()
                    print("going to approval queue", "current_iteration:", loop.n)
                    n += 1
                    print("Making up for skipped case with increased limit...", "current_iteration:", loop.n)
                    continue
                
                NBS.StandardChecks()
                print("running standard checks", "current_iteration:", loop.n)
                if not NBS.issues or "Out of state - should be Not a Case." in NBS.issues:
                    reviewed_ids.append(inv_id)
                    what_do.append("Approve Notification")
                    reason.append("Approved")
                    epi.append(NBS.investigator_name)

                    NBS.ApproveNotification()
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

                if len(NBS.issues) > 0:
                    NBS.SortQueue(paths)
                    print("sorting queue to check case at the top...", "current_iteration:", loop.n)
                    
                    if NBS.queue_loaded:
                        NBS.queue_loaded = None
                        print("failed to go to home, skipping to approval queue....", "current_iteration:", loop.n)
                        continue
                        
                    NBS.CheckFirstCase(n)
                    print("check for matching first case", "current_iteration:", loop.n)

                    NBS.final_name = NBS.patient_name

                    if NBS.final_name == NBS.initial_name and "Out of state - should be Not a Case." not in NBS.issues:
                        reviewed_ids.append(inv_id)
                        what_do.append("Reject Notification")
                        epi.append(NBS.investigator_name)
                        reason.append(' '.join(NBS.issues))
                        print("issues seen on append:", NBS.issues, "current_iteration:", loop.n)

                        NBS.RejectNotification(n)
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
                    elif NBS.final_name != NBS.initial_name:
                        print(f"here : {NBS.final_name} {NBS.initial_name}", "current_iteration:", loop.n)
                        print('Case at top of queue changed. No action was taken on the reviewed case.', "current_iteration:", loop.n)
                        NBS.num_fail += 1
            else:
                # Increment consecutive no-case counter since we didn't find a valid Anaplasma case
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
        NBS.save_and_print_results("Anaplasma", 
            {
                'Inv ID': reviewed_ids,
                'Action': what_do,
                'Reason': reason,
                'Epi': epi
            }, "final")
    else:
        print("No final results to save.")
    
    NBS.SendAnaplasmaEmail("Babesia bot run completed", "Status", "caleb.jones@maine.gov")

    with open("patients_to_skip.txt", "w") as patient_writer:
        patient_writer.write("\n".join(patients_to_skip) + "\n")

    if error: 
        raise Exception(error_list)

if __name__ == '__main__':
    start_babesia()