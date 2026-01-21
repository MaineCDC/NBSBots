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

reviewed_ids = []
what_do = []
reason = []

is_in_production = os.getenv('ENVIRONMENT', 'production') != 'development'


@error_handle
def start_giardia(username, passcode):
    
    from .giardia import Giardia
    

    load_dotenv()
    
    
    NBS = Giardia(production=True)
    NBS.set_credentials(username, passcode)
    NBS.log_in()
    NBS.GoToApprovalQueue()

    patients_to_skip = set()
    error_list = []
    error = False
    n = 1
    gone_home = -1
    attempt_counter = 0

    def save_and_print_results(file_suffix=""):
        """Helper function to save results to Excel - appends if file exists"""
        if len(reviewed_ids) > 0:
            print(f"Saving results: {reviewed_ids}, {what_do}, {reason}")
            new_data = pd.DataFrame(
                {
                'Inv ID': reviewed_ids,
                'Action': what_do,
                'Reason': reason
                })
            
            filename = f"saved/giardia/Giardia_bot_activity_{file_suffix}_{datetime.now().date().strftime('%m_%d_%Y')}.xlsx"
            
            # Check if file already exists
            if os.path.exists(filename):
                try:
                    # Read existing data
                    existing_data = pd.read_excel(filename, index_col=0)
                    # Append new data to existing data
                    combined_data = pd.concat([existing_data, new_data], ignore_index=True)
                    
                    # Remove duplicates based on 'Inv ID' to avoid processing same case multiple times
                    # Keep the last occurrence (most recent) in case of duplicates
                    combined_data = combined_data.drop_duplicates(subset=['Inv ID'], keep='last')
                    
                    print(f"Appending {len(new_data)} new records to existing file with {len(existing_data)} records")
                    print(f"After removing duplicates: {len(combined_data)} total records")
                except Exception as e:
                    print(f"Error reading existing file, creating new one: {str(e)}")
                    combined_data = new_data
            else:
                combined_data = new_data
                print(f"Creating new file with {len(new_data)} records")
            
            # Save the combined data
            combined_data.to_excel(filename)
            print(f"Results saved to {filename} (Total records: {len(combined_data)})")
            return True
        return False

    
    with open("patients_to_skip.txt", "r") as patient_reader:
        patients_to_skip |= set(patient_reader.readlines())

    # Sort queue first to get only Giardia cases
    paths = {
        "clear_filter_path":'//*[@id="removeFilters"]/a/font',
        "description_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/img',
        "clear_checkbox_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[2]/input',
        "click_ok_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[1]/input[1]',
        "click_cancel_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[1]/input[2]',
        "tests":["Giardiasis"],
        "submit_date_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[3]/a'
    }
    
    print("Sorting queue to filter for Giardia cases...")
    NBS.SortQueue(paths)
    
    # Count the number of Giardia cases in the queue
    print("Counting Giardia cases in queue...")
    try:
        # Get the case count element using the provided XPath
        case_count_element = NBS.find_element(By.XPATH, '//*[@id="bd"]/table[2]/tbody/tr/td/span[2]/b')
        case_count_text = case_count_element.text.strip()
        print(f"Case count text found: '{case_count_text}'")
        
        # Parse the count - Format: "Results 1 to 1 of 1" or "Results 1 to 16 of 45"
        match = re.search(r'Results\s+\d+\s+to\s+\d+\s+of\s+(\d+)', case_count_text)
        if match:
            giardia_case_count = int(match.group(1))
            print(f"Total Giardia cases in queue: {giardia_case_count}")
        else:
            raise ValueError(f"Could not parse count from: '{case_count_text}'")
        
    except Exception as e:
        print(f"Error getting case count: {e}")
        # Fallback: count table rows
        try:
            case_rows = NBS.find_elements(By.XPATH, '/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/tbody/tr')
            giardia_case_count = len(case_rows)
            print(f"Fallback: Found {giardia_case_count} case rows in table")
        except:
            # Ultimate fallback
            giardia_case_count = 20
            print("Could not determine case count, using default value of 20")
    
    # Check if there are any cases to process
    if giardia_case_count == 0:
        print("No Giardia cases found in queue. Exiting.")
        with open("patients_to_skip.txt", "w") as patient_writer:
            patient_writer.write("\n".join(patients_to_skip) + "\n")
        return
    
    # Set limit based on actual case count
    limit = giardia_case_count
    
    print(f"Set limit to {limit}")
    
    page = 2
    loop = tqdm(generator())
    for _ in loop:
        print(f"current limit: {limit}", "starting_iteration:", loop.n)
        
        #check if the bot has gone through the set limit of reviews
        if loop.n == limit:
            break
            
        try:
            #Sort review queue so that only giardia investigations are listed
            NBS.SortQueue(paths)
            print(f"sorting queue...: {NBS.queue_loaded}", "current_iteration:", loop.n)

            if NBS.queue_loaded:
                NBS.queue_loaded = None
                if gone_home > NBS.num_attempts and loop.n >= limit:
                    print("No case in approval queue, ending...")
                    break
                print("failed to go to home, skipping to approval queue...")
                gone_home += 1
                continue
            elif NBS.queue_loaded == False:
                NBS.queue_loaded = None
                print("failed to go to home, approval queue didn't load, breaking....")
                break
            
            NBS.CheckFirstCase(n)
            print("checked first case", "current_iteration:", loop.n)
            
            if NBS.condition == 'Giardiasis':
                NBS.GoToNCaseInApprovalQueue(n)
                print("navigated to first case in queue", "current_iteration:", loop.n)
                if NBS.queue_loaded:
                    NBS.queue_loaded = None
                    if gone_home > NBS.num_attempts and loop.n >= limit:
                        print("No case in approval queue, ending...")
                        break
                    print("failed to go to home, skipping to approval queue...")
                    gone_home += 1
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
                
                if not NBS.issues:
                    reviewed_ids.append(inv_id)
                    what_do.append("Approve Notification")
                    reason.append("Approved")
                    print("approved", "current_iteration:", loop.n)
                    NBS.ApproveNotification()
                    # NBS.SendGiardiaEmail("Hey, please don't change anything at all and just click CN", inv_id)
                    NBS.ReturnApprovalQueue()
                    print("returning to approval queue..", "current_iteration:", loop.n)

                if NBS.queue_loaded:
                    NBS.queue_loaded = None
                    if gone_home > NBS.num_attempts and loop.n >= limit:
                        print("No case in approval queue, ending...")
                        break
                    print("failed to go to home, skipping to approval queue...")
                    gone_home += 1
                    continue

                if len(NBS.issues) > 0:
                    NBS.SortQueue(paths)
                    print("sorting queue...", "current_iteration:", loop.n)

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
                        reason.append(' '.join(NBS.issues))
                        print("rejected", "current_iteration:", loop.n)

                        NBS.RejectNotification(n)
                        body = ''
                        if  all(case in NBS.issues  for case in ['City is blank.', 'County is blank.', 'Zip code is blank.']):
                            body = 'Hey, please only update City, Zip Code and County, then Click CN'
                        elif NBS.CorrectCaseStatus:
                            body = f'Hey, please only update the case status to {NBS.CorrectCaseStatus}, then click CN for this case.'
                        if body:
                            print('mail', body, "current_iteration:", loop.n)
                            NBS.SendGiardiaEmail(body, inv_id)

                        NBS.GoToApprovalQueue()
                        print(f"returning approval queue....: {NBS.queue_loaded}", "current_iteration:", loop.n)
                    elif NBS.final_name != NBS.initial_name:
                        print(f"here : {NBS.final_name} {NBS.initial_name}", "current_iteration:", loop.n)
                        print('Case at top of queue changed. No action was taken on the reviewed case.', "current_iteration:", loop.n)
                        NBS.num_fail += 1
            else:
                if attempt_counter < NBS.num_attempts:
                    attempt_counter += 1
                else:
                    attempt_counter = 0
                    print("No giardia cases in notification queue.", "current_iteration:", loop.n)
                    break
                    
        except Exception as e:
            error_list.append(str(e))
            error = True
            print(f"Exception occurred: {str(e)}", "current_iteration:", loop.n)
            
    print("ending, printing, saving", "current_iteration:", loop.n)
    
    if len(reviewed_ids) > 0:
        save_and_print_results("final")
    else:
        print("No final results to save.")
    
    with open("patients_to_skip.txt", "w") as patient_writer:
        patient_writer.write("\n".join(patients_to_skip) + "\n")
        
    if error: 
        raise Exception(error_list)

if __name__ == '__main__':
    start_giardia()
