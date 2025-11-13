# -*- coding: utf-8 -*-
"""
Created on Wed Mar 26 2025

@author: Vaishnavi.Appidi
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

from dotenv import load_dotenv
import os
from decorator import error_handle

def generator():
    while True:
        yield

is_in_production = os.getenv('ENVIRONMENT', 'production') != 'development'


@error_handle
def start_strep(username, passcode):
    
    from .strep import Strep

    load_dotenv()
    
    reviewed_ids = []
    what_do = []
    reason = []
    
    NBS = Strep(production=True)  # production=True & Test = is_in_production
    if is_in_production:
        print("Production Environment")
    else:
        print("Development Environment")
        
    NBS.set_credentials(username, passcode)
    NBS.log_in()
    NBS.GoToApprovalQueue()
    #NBS.reviewed_ids = []
    patients_to_skip = set()
    error_list = []
    error = False
    n = 1
    attempt_counter = 0
    
    with open("patients_to_skip.txt", "r") as patient_reader:
        patients_to_skip |= set(patient_reader.readlines())

    limit = 41
    loop = tqdm(generator())
    for _ in loop:
        #check if the bot haa gone through the set limit of reviews
        if loop.n == limit:
            break
        try:
            #Sort review queue so that only strep investigations are listed
            paths = {
                "clear_filter_path":'//*[@id="removeFilters"]/a/font',
                "description_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/img',
                "clear_checkbox_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[2]/input',
                "click_ok_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[1]/input[1]',
                "click_cancel_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[1]/input[2]',
                "tests":["STREPTOCOCCUS PYOGENES","Group A Streptococcus, invasive"],
                "submit_date_path":'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[3]/a'
            }
            
            NBS.SortQueue(paths)
            if NBS.queue_loaded:
                NBS.queue_loaded = None
                continue
            elif NBS.queue_loaded == False:
                NBS.queue_loaded = None
                #NBS.SendManualReviewEmail()
                #NBS.Sleep()
                continue
            
            NBS.CheckFirstCase()
            if NBS.condition == 'Group A Streptococcus, invasive':
                NBS.GoToNCaseInApprovalQueue(n)
                if NBS.queue_loaded:
                    NBS.queue_loaded = None
                    continue
                inv_id = NBS.find_element(By.XPATH,'//*[@id="bd"]/table[3]/tbody/tr[2]/td[1]/span[2]').text 
                '''if any(inv_id in skipped_patients for skipped_patients in patients_to_skip):
                    print(f"present, {inv_id}")
                    NBS.ReturnApprovalQueue()
                    n = n + 1
                    continue'''
                
                NBS.StandardChecks()
                if not NBS.issues:
                    reviewed_ids.append(inv_id)
                    what_do.append("Approved Notification")
                    reason.append('No issues found.')
                    print("Approved Notification")
                    NBS.ApproveNotification()
                    #NBS.SendStrepEmail("Hey, please don't change anything at all and just click CN", inv_id)
                NBS.ReturnApprovalQueue()
                if NBS.queue_loaded:
                    NBS.queue_loaded = None
                    continue
                if len(NBS.issues) > 0:
                    NBS.SortQueue(paths)
                    if NBS.queue_loaded:
                        NBS.queue_loaded = None
                        continue
                    NBS.CheckFirstCase()

                    NBS.final_name = NBS.patient_name
                    '''if NBS.country != 'UNITED STATES':
                        print("Skipping patient. No action carried out")
                        patients_to_skip.append(inv_id)'''
                    if NBS.final_name == NBS.initial_name:
                        reviewed_ids.append(inv_id)
                        what_do.append("Reject Notification")
                        reason.append(' '.join(NBS.issues))
                        NBS.RejectNotification()
                        body = ''
                        if  all(case in NBS.issues  for case in ['City is blank.', 'County is blank.', 'Zip code is blank.']):
                            body = 'Hey, please only update City, Zip Code and County, then Click CN'
                        elif NBS.CorrectCaseStatus:
                            body = f'Hey, please only update the case status to {NBS.CorrectCaseStatus}, then click CN for this case.'
                        if body:
                            print('mail', body)
                            NBS.SendStrepEmail(body, inv_id)
                        # NBS.ReturnApprovalQueue()
                    elif NBS.final_name != NBS.initial_name:
                        print(f"here : {NBS.final_name} {NBS.initial_name}")
                        print('Case at top of queue changed. No action was taken on the reviewed case.')
                        NBS.num_fail += 1
            else:
                if attempt_counter < NBS.num_attempts:
                    attempt_counter += 1
                else:
                    attempt_counter = 0
                    print("No Group A strep cases in notification queue.")
                    NBS.SendManualReviewEmail()
                    #NBS.Sleep()
                    break
        except Exception as e:
            # raise Exception(e)
            error_list.append(str(e))
            error = True
        #     # print(tb)
        #     with open("error_log.txt", "a") as log:
        #         log.write(f"{datetime.now().date().strftime('%m_%d_%Y')} | Group A Strep - {str(tb)}")
        #     #NBS.send_smtp_email(NBS.covid_informatics_list, 'ERROR REPORT: NBSbot(Group A Strep Notification Review) AKA Athena', tb, 'error email')
            
    NBS.iGAS_notification_bot = True
    NBS.SendBotRunEmail()
    #NBS.CreateExcelSheet()
    
    print("ending, printing, saving")
    bot_act = pd.DataFrame(
        {'Inv ID': reviewed_ids,
        'Action': what_do,
        'Reason': reason
        })
    bot_act.to_excel(f"saved/Strep/Strep_bot_activity_{datetime.now().date().strftime('%m_%d_%Y')}.xlsx")
    print("Excel sheet created")

    '''completion_message = (
    f"Group A Strep case closing bot has finished running on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. "
    f"Total labs reviewed: {len(reviewed_ids)}."
)
    NBS.send_smtp_email("disease.reporting@maine.gov", "Group A Strep Case Closing Bot Completed", completion_message, "Daily Bot Run Notification")'''



    # body = "The list of Group A Strep notifications that need to be manually reviewed are in the attached spreadsheet."
    
    # message = EmailMessage()
    # message.set_content(body)
    # message['Subject'] = 'Notification Review Report: NBSbot(Group A Strep Notification Review) AKA Group A Strep'
    # message['From'] = NBS.nbsbot_email
    # message['To'] = ', '.join(["disease.reporting@maine.gov"])
    # with open(f"Strep_bot_activity_1{datetime.now().date().strftime('%m_%d_%Y')}.xlsx", "rb") as f:
    #     message.add_attachment(
    #         f.read(),
    #         filename=f"Anaplasma_bot_activity_{datetime.now().date().strftime('%m_%d_%Y')}.xlsx",
    #         maintype="application",
    #         subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    #     )
    # smtpObj = smtplib.SMTP(NBS.smtp_server)
    # smtpObj.send_message(message)
    
    with open("patients_to_skip.txt", "w") as patient_writer:
        patient_writer.write("\n".join(patients_to_skip) + "\n")
    
    if error: 
        raise Exception(error_list)

if __name__ == '__main__':
    start_strep()
