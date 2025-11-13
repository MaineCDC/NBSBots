'''
NOTE: deprecated
The code block below has been commented out, because I kept getting permission issues with the chrome driver
but this solves it, since there's a chrome driver being used within the directory

from selenium import webdriver
import os
driver=webdriver.Chrome()

'''
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# initialize chromedriver
chrome_driver_path = "chromedriver.exe"  # Replace with your custom path
# chrome_driver_path=ChromeDriverManager().install()
service = Service(chrome_driver_path)
driver = webdriver.Chrome(service=service)

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd
import sys, re
import win32com.client as win32
import getpass
from pathlib import Path
from shutil import rmtree
import time
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.common.exceptions import NoAlertPresentException
import configparser
import smtplib
from email.message import EmailMessage
from selenium.webdriver.common.by import By
from geopy.geocoders import Nominatim
from usps import USPSApi, Address
import json
from io import StringIO




class NBSdriver(webdriver.Chrome):
    """ A class to provide basic functionality in NBS via Selenium. """
    def __init__(self, production=False):
        self.production = production
        self.read_config()
        self.get_email_info()
        self.get_usps_user_id()
        if self.production:
            self.site = 'https://nbs.iphis.maine.gov/'
        else:
            self.site = 'https://nbstest.state.me.us/'

        self.Reset()
        self.GetObInvNames()
        self.not_a_case_log = []
        self.lab_data_issues_log = []

        self.options = webdriver.ChromeOptions()
        self.options.add_argument('log-level=3')
        self.options.add_argument('--ignore-ssl-errors=yes')
        self.options.add_argument('--ignore-certificate-errors')
        super(NBSdriver, self).__init__(options = self.options)
        self.issues = []
        self.num_attempts = 3
        self.queue_loaded = None
        self.wait_before_timeout = 30
        self.sleep_duration = 300 #3300 #Value in seconds


    def GetObInvNames(self):
        """ Read list of congregate setting outbreak investigators from config.cfg. """
        self.outbreak_investigators = self.config.get('OutbreakInvestigators', 'Investigators').split(', ')
        
    def Reset(self):
        """ Clear values of attributes assigned during case investigation review.
        To be used on initialization and between case reviews. """
        self.issues = []
        self.is_deceased = None #new
        self.now = datetime.now().date()
        self.collection_date = None
        self.serology_collection_date = None
        self.cong_aoe = None
        self.cong_setting_indicator = None
        self.county = None
        self.country = None #new variable
        self.culture_done = None #new
        self.culture_positive = None #new
        self.state = None #new
        self.current_report_date = None
        self.current_status = None
        self.death_indicator = None
        self.dob = None
        self.discharge_date = None
        self.date_closed = None #new
        self.epi = None #new
        self.first_responder = None
        self.follow_up_tests = False       #new variable
        self.fr_aoe = None
        self.hcw_aoe = None
        self.healthcare_worker = None
        self.hosp_aoe = None
        self.hospitalization_indicator = None
        self.icu_aoe = None
        self.icu_indicator = None
        self.immpact = None
        self.investigation_start_date = None
        self.investigator = None
        self.jurisdiction = None #new variable to allow access from multiple functions
        self.labs = None
        self.lab_specimen_source = None #new
        self.lab_specimen_collection_date = None #new
        self.lab_report_date = None #new
        self.lab_is_serology = False #new
        self.ltf = None
        self.negative_lab_result = False #new
        self.preg_aoe = None
        self.patient_sex = None
        self.report_date = None
        self.reporting_organization = None #new
        self.reporting_provider = None #new
        self.returned_by_link = False #new
        self.earliest_date_received = None
        self.latest_date_received = None
        self.missing_lab_report = False
        self.status = None
        self.symp_aoe = None
        self.symptoms = None
        self.symptoms_list = [] #new variable initially undeclared
        self.serology_test_type = None #new variable 
        self.titer_value = None #new
        self.vax_recieved = None
        self.initial_name = None #new variable initially undeclared
        self.final_name = None  #new variable initially undeclared
        self.CaseStatus = None  #new variable initially undeclared
        self.CorrectCaseStatus = None  #new variable initially undeclared
        self.slept = 0 #new
        self.travel_outside_home = None #new
        #self.travel_info = None #new

########################### NBS Navigation Methods ############################
    def get_credentials(self):
        """ A method to prompt user to provide a valid username and RSA token
        to log in to NBS. Must """
        self.username = input('Enter your SOM username ("first_name.last_name"):')
        self.passcode = input('Enter your RSA passcode:')

    def set_credentials(self, username, passcode):
        """ A method to prompt user to provide a valid username and RSA token
        to log in to NBS. Must """
        self.username = username
        self.passcode = passcode

    def log_in(self):
        """ Log in to NBS. """
        self.get(self.site)
        print('passed')
        self.switch_to.frame("contentFrame")
        self.find_element(By.ID, "username").send_keys(self.username) #find_element_by_id() has been deprecated
        self.find_element(By.ID, 'passcode').send_keys(self.passcode)
        WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[2]/p[2]/input[1]')))
        self.find_element(By.XPATH,'/html/body/div[2]/p[2]/input[1]').click()
        time.sleep(3) #wait for the page to load, I'm not sure why the following wait to be clickable does not handle this, but this fixed the error
        #print(str(self.current_url))
        print(self.page_source) #for some reason removing this makes nbsbot unable to log in to nbs
        WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="bea-portal-window-content-4"]/tr/td/h2[4]/font/a'))) #switch to element_to_be_clickable
        self.find_element(By.XPATH,'//*[@id="bea-portal-window-content-4"]/tr/td/h2[4]/font/a').click()
    
    def go_to_tab_one(self):
        path = '//*[@id="tabs0head0"]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, path)))
        self.find_element(By.XPATH, path).click()

    def go_to_tab_two(self):
        path = '//*[@id="tabs0head1"]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, path)))
        self.find_element(By.XPATH, path).click()
    
    def go_to_tab_three(self):
        path = '//*[@id="tabs0head2"]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, path)))
        self.find_element(By.XPATH, path).click()
    
    def go_to_tab_five(self):
        path = '//*[@id="tabs0head4"]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, path)))
        self.find_element(By.XPATH, path).click()

    ######################### Name Information Check Methods #######################
    def CheckFirstName(self):
        """ Must provide first name. """
        first_name = self.CheckForValue( '//*[@id="DEM104"]', 'First name is blank.')

    def CheckLastName(self):
        """ Must provide last name. """
        last_name = self.CheckForValue( '//*[@id="DEM102"]', 'last name is blank.')

    ###################### Other Personal Details Check Methods ####################
    def CheckDOB(self):
        """ Must provide DOB. """
        self.dob = self.ReadDate('//*[@id="DEM115"]')
        if not self.dob:
            self.issues.append('DOB is blank.')
            print(f"dob: {self.dob}")
        elif self.dob > self.now:
            self.issues.append('DOB cannot be in the future.')
            print(f"dob: {self.dob}")

    def go_to_id(self, id):
        """ Navigate to specific patient by NBS ID from Home. """
        self.find_element(By.XPATH,'//*[@id="DEM229"]').send_keys(id)
        self.find_element(By.XPATH,'//*[@id="patientSearchByDetails"]/table[2]/tbody/tr[8]/td[2]/input[1]').click()
        search_result_path = '//*[@id="searchResultsTable"]/tbody/tr/td[1]/a'
        WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, search_result_path)))
        self.find_element(By.XPATH, search_result_path).click()

    def clean_patient_id(self, patient_id):
        """Remove the leading and trailing characters from local patient
        ids to leave an id that is searchable in through the front end of NBS."""
        if patient_id[0:4] == 'PSN1':
            patient_id = patient_id[4:len(patient_id)-4]
        elif patient_id[0:4] == 'PSN2':
            patient_id = '1' + patient_id[4:len(patient_id)-4]
        return patient_id

    def go_to_summary(self):
        """ Within a patient profile navigate to the Summary tab."""
        self.find_element(By.XPATH,'//*[@id="tabs0head0"]').click()

    def go_to_events(self):
        """ Within patient profile navigate to the Events tab. """
        events_path = '//*[@id="tabs0head1"]'
        try:
            WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, events_path)))
            self.find_element(By.XPATH, events_path).click()
            error_encountered = False
        except TimeoutException:
            error_encountered = True
        return error_encountered

    def go_to_demographics(self):
        """ Within a patient profile navigate to the Demographics tab."""
        demographics_path = '//*[@id="tabs0head2"]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, demographics_path)))
        self.find_element(By.XPATH,'//*[@id="tabs0head2"]').click()

    def go_to_home(self):
        """ Go to NBS Home page. """
        #xpath = '//*[@id="bd"]/table[1]/tbody/tr/td[1]/table/tbody/tr/td[1]/a'
        partial_link = 'Home'
        for _ in range(self.num_attempts):
            try:
                #WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))
                #self.find_element(By.XPATH, xpath).click()
                WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, partial_link)))
                self.find_element(By.PARTIAL_LINK_TEXT, partial_link).click()
                self.home_loaded = True
                break
            except TimeoutException:
                self.home_loaded = False
        # print(f"Made {self.num_attempts} unsuccessful attempts to load Home page. A persistent issue with NBS was encountered. {self.home_loaded}")
        # if not self.home_loaded:
        #     sys.exit(print(f"Made {self.num_attempts} unsuccessful attempts to load Home page. A persistent issue with NBS was encountered."))

    def GoToApprovalQueue(self):
        """ Navigate to approval queue from Home page. """
        partial_link = 'Approval Queue for Initial Notifications'
        try:
            WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, partial_link)))
            self.find_element(By.PARTIAL_LINK_TEXT, partial_link).click()
        except TimeoutException:
            self.HandleBadQueueReturn()

    def ReturnApprovalQueue(self):
        """ Return to Approval Queue from an investigation initally accessed from the queue. """
        xpath = '//*[@id="bd"]/div[1]/a'
        try:
            WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))
            self.find_element(By.XPATH, xpath).click()
        except TimeoutException:
            self.HandleBadQueueReturn()

    def SortQueue(self, paths:dict):
        #Sort review queue so that only Anaplasma investigations are listed
        try:    
            #clear all filters
            WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, paths['clear_filter_path'])))
            self.find_element(By.XPATH, paths['clear_filter_path']).click()
            time.sleep(5)

            
            #open condition dropdown menu
            WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, paths['description_path'])))
            WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, paths['description_path'])))
            self.find_element(By.XPATH, paths['description_path']).click()
            time.sleep(1)

            #clear checkboxes
            WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, paths['clear_checkbox_path'])))
            self.find_element(By.XPATH, paths['clear_checkbox_path']).click()
            time.sleep(1)

            #select all tests
            for test in paths['tests']:
                try:
                    results = self.find_elements(By.XPATH,f"//label[contains(text(),'{test}')]")
                    for result in results:
                        result.click()
                except (NoSuchElementException, ElementNotInteractableException) as e:
                    pass
            time.sleep(1)

            #click ok
            try:
                WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, paths['click_ok_path'])))
                self.find_element(By.XPATH, paths['click_ok_path']).click()
            except (NoSuchElementException, TimeoutException):
                #click cancel and go back to home page to wait for more ELRs
                WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, paths['click_cancel_path'])))
                self.find_element(By.XPATH, paths['click_cancel_path']).click()
                #self.go_to_home()
                time.sleep(3)
                print("about to sleep")
                self.Sleep()
                #this wont work if we are not running the for loop to cycle through the queue,
                #c]omment out if not running the whole thing
                
            time.sleep(1)
            print(f"sleep count {self.slept}")
            #sort chronologically, oldest first
            WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, paths['submit_date_path'])))
            self.find_element(By.XPATH, paths['submit_date_path']).click()
            WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, paths['submit_date_path'])))
            self.find_element(By.XPATH, paths['submit_date_path']).click() #---here
        except (TimeoutException, ElementClickInterceptedException):
            self.HandleBadQueueReturn()

    def SortApprovalQueue(self):
        """ Sort approval queue so that case are listed chronologically by
        notification creation date and in reverse alpha order so that
        "2019 Novel..." is at the top. """
        clear_filter_path = '//*[@id="removeFilters"]/a/font'
        submit_date_path = '//*[@id="parent"]/thead/tr/th[3]/a'
        condition_path = '//*[@id="parent"]/thead/tr/th[8]/a'
        description_path = '//html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/img'
        clear_checkbox_path = '/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[2]/input'
        try:
            # Clear all filters
            WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, clear_filter_path)))
            self.find_element(By.XPATH, clear_filter_path).click()
            # The logic for this is somewhat weird but here is my understanding of what happens.
            # If we have anything in the queue that isn't covid-19 the bot will run until it hits that case and then stall out.
            # To prevent this we can select covid-19 cases from the condition menu, but if there are no covid-19 cases we still
            # have to pick something from the dropdown menu or cancel out. We will cancel out of the dropdown menu if there are
            # no covid-19 cases which will give us only non-covid-19 cases. The check for covid-19 later on will prevent us
            # from reviewing the next case in the queue and it will hit the wait until we have more covid-19 cases. I think this
            # will allow for conditions besides covid-19 in the queue and allow us to process all covid-19 cases without
            # stalling the bot permanently once it runs into a non-covid-19 case.
            # Open Condition dropdown menu
            time.sleep(3)
            WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, description_path)))
            self.find_element(By.XPATH, description_path).click()
            # Clear checkboxes
            WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, clear_checkbox_path)))
            self.find_element(By.XPATH, clear_checkbox_path).click()
            try:
                # Click on the 2019 Novel Coronavirus checkbox
                self.find_element(By.XPATH, "//label[contains(text(),'2019 Novel Coronavirus')]/input").click()
                # Click on the okay button
                self.find_element(By.XPATH,'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[1]/input[1]').click()
            except NoSuchElementException:
                self.find_element(By.XPATH,'/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[1]/input[2]').click()             
            # Double click submit date for chronological order.
            WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, submit_date_path)))
            self.find_element(By.XPATH, submit_date_path).click()
            WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, submit_date_path)))
            self.find_element(By.XPATH, submit_date_path).click()
            # Double click condition for reverse alpha order.
            WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, condition_path)))
            self.find_element(By.XPATH,condition_path).click()
            WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, condition_path)))
            self.find_element(By.XPATH,condition_path).click()
            WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, condition_path)))
        except (TimeoutException, ElementClickInterceptedException):
            self.HandleBadQueueReturn()

    def HandleBadQueueReturn(self):
        """ When a request is sent to NBS to load or filter the approval queue
        and "Nothing found to display", or anything other than the populated
        queue is returned, navigate back to the home page and request the queue
        again."""
        # Recursion seems like a good idea here, but if the queue is truly empty there will be nothing to display and recursion will result in a stack overflow.
        for _ in range(self.num_attempts):
            try:
                self.go_to_home()
                if not self.home_loaded:
                    self.queue_loaded = False
                    break
                self.GoToApprovalQueue()
                self.queue_loaded = True
                break
            except TimeoutException:
                self.queue_loaded = False
        if not self.queue_loaded:
            print(f"Made {self.num_attempts} unsuccessful attempts to load approval queue. Either to queue is truly empty, or a persistent issue with NBS was encountered.")

    def GoToNPage(self, n):
        if n >= 2:
            next_page_path = f'//*[@title="Go to page {n}"]'
            WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, next_page_path)))
            self.find_element(By.XPATH, next_page_path).click()
        print(f"Moved to page {n}")
        
    def CheckFirstCase(self, n=1):
        """ Ensure that first case is COVID and save case's name for later use."""
        try:
            self.condition = self.find_element(By.XPATH, f'//*[@id="parent"]/tbody/tr[{n}]/td[8]/a').get_attribute('innerText')
            self.patient_name = self.find_element(By.XPATH, f'//*[@id="parent"]/tbody/tr[{n}]/td[7]/a').get_attribute('innerText')
        except NoSuchElementException:
            self.condition = None
            self.patient_name = None

    def GoToFirstCaseInApprovalQueue(self):
        """ Navigate to first case in the approval queue. """
        xpath_to_case = '//*[@id="parent"]/tbody/tr[1]/td[8]/a'
        xpath_to_first_name = '//*[@id="DEM104"]'
        try:
            # Make sure queue loads properly before navigating to first case.
            WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, xpath_to_case)))
            self.find_element(By.XPATH, xpath_to_case).click()
            # Make sure first case loads properly before moving on.
            WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, xpath_to_first_name)))
        except TimeoutException:
            self.HandleBadQueueReturn()

    def GoToNCaseInApprovalQueue(self, n=1):
        """ Navigate to first case in the approval queue. """
        xpath_to_case = f'//*[@id="parent"]/tbody/tr[{n}]/td[8]/a'
        xpath_to_first_name = '//*[@id="DEM104"]'
        try:
            # Make sure queue loads properly before navigating to first case.
            WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, xpath_to_case)))
            self.find_element(By.XPATH, xpath_to_case).click()
            # Make sure first case loads properly before moving on.
            WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, xpath_to_first_name)))
        except TimeoutException:
            self.HandleBadQueueReturn()

    def GoToCaseInfo(self):
        """ Within a COVID investigation navigate to the Case Info tab. """
        case_info_tab_path = '//*[@id="tabs0head1"]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, case_info_tab_path)))
        self.find_element(By.XPATH, case_info_tab_path ).click()

    def GoToCOVID(self):
        """ Within a COVID investigation navigate to the COVID tab. """
        covid_tab_path = '//*[@id="tabs0head2"]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, covid_tab_path)))
        self.find_element(By.XPATH, covid_tab_path).click()

    def go_to_lab(self, lab_id):
        """ Navigate to a lab from a patient profile navigate to a lab. """
        lab_report_table_path = '//*[@id="lab1"]'
        lab_report_table = self.ReadTableToDF(lab_report_table_path)
        if len(lab_report_table) > 1:
            lab_row_index = lab_report_table[lab_report_table['Event ID'] == lab_id].index.tolist()[0]
            lab_row_index = str(int(lab_row_index) + 1)
            lab_path = f'/html/body/div[2]/form/div/table[4]/tbody/tr[2]/td/div[2]/table/tbody/tr/td/div[1]/div[5]/div/table/tbody/tr/td/table/tbody/tr[{lab_row_index}]/td[1]/a'
        else:
            lab_path = '/html/body/div[2]/form/div/table[4]/tbody/tr[2]/td/div[2]/table/tbody/tr/td/div[1]/div[5]/div/table/tbody/tr/td/table/tbody/tr/td[1]/a'
        self.find_element(By.XPATH,lab_path).click()

    def read_investigation_table(self):
        """ Read the investigations table in the Events tab of a patient profile
        of all investigations on record, both open and closed."""
        investigation_table_path = '//*[@id="inv1"]'
        investigation_table = self.ReadTableToDF(investigation_table_path)
        if type(investigation_table) == pd.core.frame.DataFrame:
            investigation_table['Start Date'] = pd.to_datetime(investigation_table['Start Date'])
        return investigation_table

    def go_to_investigation_by_index(self, index):
        """Navigate to an existing investigation based on its position in the
        Investigations table in the Events tab of a patient profile."""
        if index > 1:
            existing_investigation_path = f'/html/body/div[2]/form/div/table[4]/tbody/tr[2]/td/div[2]/table/tbody/tr/td/div[1]/div[3]/div/table/tbody/tr[2]/td/table/tbody/tr[{str(index)}]/td[1]/a'
        elif index == 1:
            existing_investigation_path = f'/html/body/div[2]/form/div/table[4]/tbody/tr[2]/td/div[2]/table/tbody/tr/td/div[1]/div[3]/div/table/tbody/tr[2]/td/table/tbody/tr/td[1]/a'
        self.find_element(By.XPATH, existing_investigation_path).click()

    def go_to_investigation_by_id(self, inv_id):
        """Navigate to an investigation with a given id from a patient profile."""
        inv_table = self.read_investigation_table()
        inv_row = inv_table[inv_table['Investigation ID'] == inv_id]
        inv_index = int(inv_row.index.to_list()[0]) + 1
        self.go_to_investigation_by_index(inv_index)

    def return_to_patient_profile_from_inv(self):
        """ Go back to the patient profile from within an investigation."""
        return_to_file_path = '//*[@id="bd"]/div[1]/a'
        self.find_element(By.XPATH, return_to_file_path).click()

    def return_to_patient_profile_from_lab(self):
        """ Go back to the patient profile from within a lab report."""
        return_to_file_path = '//*[@id="doc3"]/div[1]/a'
        self.find_element(By.XPATH, return_to_file_path).click()

    def click_submit(self):
        """ Click submit button to save changes."""
        submit_button_path = '/html/body/div/div/form/div[2]/div[1]/table[2]/tbody/tr/td[2]/table/tbody/tr/td[1]/input'
        self.find_element(By.XPATH, submit_button_path).click()

    def click_manage_associations_submit(self):
        """ Click submit button in the Manage Associations window."""
        submit_button_path = '/html/body/div[2]/div/table[2]/tbody/tr/td/table/tbody/tr/td[2]/input'
        self.find_element(By.XPATH, submit_button_path).click()

    def enter_edit_mode(self):
        """From within an investigation click the edit button to enter edit mode."""
        edit_button_path = '/html/body/div/div/form/div[2]/div[1]/table[2]/tbody/tr/td[2]/table/tbody/tr/td[1]/input'
        self.find_element(By.XPATH, edit_button_path).click()
        try:
            self.switch_to.alert.accept()
        except NoAlertPresentException:
            pass

    def click_cancel(self):
        """ Click cancel."""
        cancel_path = '//*[@id="Cancel"]'
        self.find_element(By.XPATH, cancel_path).click()
        self.switch_to.alert.accept()

    def go_to_manage_associations(self):
        """ Click button to navigate to the Manage Associations page from an investigation."""
        manage_associations_path = '//*[@id="manageAssociations"]'
        self.find_element(By.XPATH, manage_associations_path).click()
        try:
            self.switch_to.alert.accept()
        except NoAlertPresentException:
            pass

            
    def CheckInvestigationStatus(self):
        """ Only accept closed investigations for review. """
        inv_status = self.ReadText('//*[@id="INV109"]')
        if not inv_status:
            self.issues.append('Investigation status is blank.')
        elif inv_status == 'Open':
            self.issues.append('Investigation status is open.')

################# Key Report Dates Check Methods ###############################
    def CheckReportDate(self):
        """ Check if the current value of Report Date matches the earliest
        Report Date from the associated labs. """
        self.current_report_date = self.ReadDate('//*[@id="INV111"]')
        if not self.current_report_date:
            self.issues.append('Missing report date.')
        elif self.current_report_date > self.investigation_start_date:
            self.issues.append('Report date cannot be after investigation start date.')
        elif self.report_date != self.current_report_date:
            self.issues.append('Report date mismatch.')

        if (self.earliest_date_received or self.latest_date_received) and (self.report_date != self.earliest_date_received and self.report_date != self.latest_date_received):
            self.issues.append('Report date does not match any recieved date.')

    def CheckCountyStateReportDate(self):
        """ Check if the current value of county report date is consistent with
        the current value of earliest report to state date and the report date. """
        current_county_date = self.ReadDate('//*[@id="INV120"]')
        current_state_date = self.ReadDate('//*[@id="INV121"]')
            
        if current_county_date:
            if self.earliest_date_received and current_county_date > self.earliest_date_received or  self.earliest_date_received and  current_county_date < self.earliest_date_received:
                self.issues.append(f"Earliest county report date should be {self.earliest_date_received}")

            if self.current_report_date and current_county_date < self.current_report_date:
                self.issues.append('Earliest report to county cannot be prior to inital report date.')
            elif self.investigation_start_date and current_county_date > self.investigation_start_date:
                self.issues.append('Earliest report to county date cannot be after investigation start date')
        else:
            self.issues.append('Report to county date missing.')

        if current_state_date:
            if self.earliest_date_received and current_state_date > self.earliest_date_received or self.earliest_date_received and current_state_date < self.earliest_date_received:
                self.issues.append(f"Earliest state report date should be {self.earliest_date_received}")

            if self.current_report_date and current_state_date < self.current_report_date:
                self.issues.append('Earliest report to state cannot be prior to inital report date.')
            elif self.investigation_start_date and current_state_date > self.investigation_start_date:
                self.issues.append('Earliest report to state date cannot be after investigation start date.')
        else:
            self.issues.append('Report to state date missing.')

        if current_county_date:
            if current_state_date:
                if current_county_date != current_state_date:
                    self.issues.append('Earliest dates reported to county and state do not match.')

############ Demographic/Address Check Methods #####################
    def CheckZip(self):
        """ Must provide zip code. """
        self.zipcode = self.CheckForValue( '//*[@id="DEM163"]', 'Zip code is blank.')

    def CheckJurisdiction(self):
        """ Jurisdiction and county must match unless jurisdiction is 'Out of State'. """
        self.jurisdiction = self.ReadText('//*[@id="INV107"]') #,'Jurisdiction is blank.'
        if self.jurisdiction == 'Out of State' and self.CaseStatus != 'Not a Case':                 #new code
            self.issues.append("Out of state - should be Not a Case.")                      #new code

        if self.jurisdiction and self.jurisdiction.lower().replace(" county", "") not in self.county.lower().replace(" county", "") and self.jurisdiction != 'Out of State':                    #new code
            self.issues.append('County and jurisdiction mismatch.')                               #new code
        print(f"jurisdiction: {self.jurisdiction}")

    def CheckCounty(self):
        """ Must provide county unless the jurisdiction is 'Out of State'. """
        self.county = self.CheckForValue( '//*[@id="DEM165"]', 'County is blank.')                                   #new code
        
    def CheckCountry(self):
        """ Must provide country. """
        self.country = self.CheckForValue( '//*[@id="DEM167"]', 'Country is blank.')
        if self.country and self.country != 'UNITED STATES':
            self.issues.append("Out of State")
            # self.GoToApprovalQueue
            return
            # self.issues.append('Out of State') #new code
            # Country listed is not USA.

    def CheckState(self):
        """ Must provide state and if it is not Maine case should be not a case. """
        state = self.CheckForValue( '//*[@id="DEM162"]', 'State is blank.')
        if state != 'Maine':
            self.issues.append('State is not Maine.')
            print(f"state: {state}")

    def CheckStateANA(self):
        """ Must provide state and if it is not Maine case should be not a case. """
        self.state = self.CheckForValue( '//*[@id="DEM162"]', 'State is blank.')
        
    
    def CheckCity(self):
        """ Must provide city. """
        self.city = self.CheckForValue( '//*[@id="DEM161"]', 'City is blank.')

################### Reporting Organization Check Methods #######################
    def CheckReportingSourceType(self):
        """ Ensure that reporting source type is not empty. """
        reporting_source_type = self.ReadText('//*[@id="INV112"]')
        if not reporting_source_type:
            self.issues.append('Reporting source type is blank.')

    def CheckReportingOrganization(self):
        """ Ensure that reporting organization is not empty. """
        self.reporting_organization = self.ReadText('//*[@id="INV183"]')
        if not self.reporting_organization:
            self.issues.append('Reporting organization is blank.')
    
    ######################### Case Status Check Methods ############################

    def CheckWhereDisease(self):
        where_was_disease_acquired = self.ReadText('//*[@id="INV152"]') 
            
        if where_was_disease_acquired == "Indigenous":
            if "Yes" in self.travel_outside_home:
                self.issues.append("Disease acquired should not be “indigenous” if any travel outside home county.")
            
            elif any(option != "No" for option in self.travel_outside_home):
                self.issues.append("Cannot be indigenous without travel questions all being no.")


            if (self.culture_done and self.culture_done not in  ['No', 'Unknown']) or (self.culture_positive and self.culture_positive not in  ['No', 'Unknown']):
                self.issues.append('Culture done and Culture positive should be blank or unknown, Where disease was acquired says Indigenous but travel history is unknown')
        else:
            if all(option == "No" for option in self.travel_outside_home):
                self.issues.append("If all 3 travel questions are no, where was disease acquired should be indigenous.")
            
    def CheckConfirmationMethod(self):
        """ Confirmation Method must be blank or consistent with correct case status."""
        self.confirmation_method =  self.ReadText('//*[@id="INV161"]')
        # if not self.confirmation_method: #new code
        #     self.issues.append("Confirmation method is missing")
        #     print(f"confirmation_method: {self.confirmation_method}")

    def CheckDetectionMethod(self):
        """ Ensure Detection Method is not blank. """
        detection_method = self.CheckForValue( '//*[@id="INV159"]', 'Detection mode blank.')

    def CheckConfirmationDate(self):
        """ Confirmation date must be on or after report date. """
        confirmation_date = self.ReadDate('//*[@id="INV162"]')
        if not confirmation_date:
            self.issues.append(f'Confirmation date is blank.{confirmation_date}')
            print(f"confirmation_date: {confirmation_date}")
        # elif confirmation_date < self.report_date:
        #     self.issues.append('Confirmation date cannot be prior to report date.')
        #     print(f"confirmation_date: {confirmation_date}")
        else:
            if self.investigation_start_date and confirmation_date < self.investigation_start_date:
                self.issues.append("confirmation date cannot be before investigation start date.")
            if confirmation_date > self.now:
                self.issues.append('Confirmation date cannot be in the future.')
                print(f"confirmation_date: {confirmation_date}")
        
        
        return confirmation_date
    
    def CheckAdmissionDate(self):
        """ Check for hospital admission date."""
        self.admission_date = self.ReadDate('//*[@id="INV132"]')
        # if not self.admission_date:
        #     self.issues.append('Admission date is missing.')
        #     print(f"admission_date: {self.admission_date}")
        if self.admission_date and self.admission_date > self.now:
            self.issues.append('Admission date cannot be in the future.')
            print(f"admission_date: {self.admission_date}")

    def CheckDischargeDate(self):
        """ Check for hospital discharge date."""
        self.discharge_date = self.ReadDate('//*[@id="INV133"]')
        if self.discharge_date:                                                         #commented out
            if self.admission_date:
                if self.discharge_date < self.admission_date:
                    self.issues.append('Discharge date must be after admission date.')
                    print(f"discharge_date: {self.discharge_date}")
            elif pd.to_datetime(self.discharge_date).date() > self.now:
                self.issues.append('Discharge date cannot be in the future.')
                print(f"discharge_date: {self.discharge_date}")

    def CheckMmwrWeek(self):
        """ MMWR week must be provided."""
        mmwr_week = self.CheckForValue( '//*[@id="INV165"]', "MMWR Week is blank.")
        

    def CheckMmwrYear(self):
        """ MMWR year must be provided."""
        mmwr_year = self.CheckForValue( '//*[@id="INV166"]', "MMWR Year is blank.")

############ Ethnicity and Race Information Check Methods #####################
    def CheckEthnicity(self):
        """ Must provide ethnicity. """
        self.ethnicity = self.CheckForValue('//*[@id="DEM155"]','Ethnicity is blank.')

############### Performing Lab Check Methods ##################################
    def CheckPerformingLaboratory(self):
        """ Ensure that preforming laboratory is not empty. """
        reporting_organization = self.ReadText('//*[@id="ME6105"]')
        if not reporting_organization:
            self.issues.append('Laboratory name is blank.')

############################# Data Reading/Validation Methods ##################################

    def CheckForValue(self, xpath, blank_message):
        """ If value is blank add appropriate message to list of issues. """
        value = self.find_element(By.XPATH, xpath).get_attribute('innerText')
        value = value.replace('\n','')
        if not value:
            self.issues.append(blank_message)
        return value

    def check_for_value_bool(self, path):
        """ Return boolean value based on whether a value is present."""
        value = self.ReadText(path)
        if value:
            check = True
        else:
            check = False
        return check

    def ReadDate(self, xpath, attribute='innerText'):
        """ Read date from NBS and return a datetime.date object. """
        date = self.find_element(By.XPATH, xpath).get_attribute(attribute)
        try:
            date_pattern = r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+$'
            if re.match(date_pattern, date.strip()):
                date = datetime.strptime(date.strip(), '%Y-%m-%d %H:%M:%S.%f').date()
            else:
                date = datetime.strptime(date.strip(), '%m/%d/%Y').date()
        except ValueError:
            date = ''
        return date

    def CheckIfField(self, parent_xpath, child_xpath, value, message):
        """ If parent field is value ensure that child field is not blank. """
        parent = self.find_element(By.XPATH, parent_xpath).get_attribute('innerText')
        parent = parent.replace('\n','')
        if parent == value:
            child = self.find_element(By.XPATH, child_xpath).get_attribute('innerText')
            child = child.replace('\n','')
            if not child:
                self.issues.append(message)

    def ReadText(self, xpath):
        """ A method to read the text of any web element identified by an Xpath
        and remove leading an trailing carriage returns sometimes included by
        Selenium's get_attribute('innerText')."""
        value = self.find_element(By.XPATH, xpath).get_attribute('innerText')
        value = value.replace('\n','')
        return value

    def ReadTableToDF(self, xpath):
        """ A method to read tables into pandas Data Frames for easy manipulation. """
        try:
            html = self.find_element(By.XPATH, xpath).get_attribute('innerHTML')
            soup = BeautifulSoup(html, 'html.parser')
            table = pd.read_html(StringIO(str(soup)))[0]
            table.fillna('', inplace = True)
        except ValueError:
            table = None
        return table

    def ReadPatientID(self):
        """ Read patient ID from within patient profile. """
        patient_id = self.ReadText('//*[@id="bd"]/table[3]/tbody/tr[1]/td[2]/span[2]')
        return patient_id

    def Sleep(self):
        """ Pause all action for the specified number of seconds. """
        self.slept += 1
        for i in range(self.sleep_duration):
            time_remaining = self.sleep_duration - i
            print(f'Sleeping for: {time_remaining//60:02d}:{time_remaining%60:02d}', end='\r', flush=True)
            time.sleep(1)
        print('Sleeping for: 00:00', end='\r', flush=True)

    def send_email_local_outlook_client (self, recipient, cc, subject, message, attachment = None):
        """ Send an email using local Outlook client."""
        self.clear_gen_py()
        outlook = win32.Dispatch('outlook.application')
        mail = outlook.CreateItem(0)
        mail.GetInspector
        mail.To = recipient
        mail.CC = cc
        mail.Subject = subject
        mail.Body = message
        if attachment != None:
            mail.Attachments.Add(attachment)
        mail.Send()

    def clear_gen_py(self):
        """ Clear the contents of the the gen_py directory to ensure emails can
        always be sent."""
        # Construct to path gen_py directory if it exists.
        current_user = getpass.getuser().lower()
        gen_py_path = r'C:\Users' +'\\' + current_user + r'\AppData\Local\Temp\gen_py'
        
        gen_py_path = Path(gen_py_path)

        # If gen_py exists delete it and all contents.
        if gen_py_path.exists() and gen_py_path.is_dir():
            rmtree(gen_py_path)

    def read_config(self):
        """ Read in data from config.cfg"""
        self.config = configparser.ConfigParser()
        self.config.read('config.cfg')

    def get_email_info(self):
        """ Read information required for NBSbot to send emails via an smtp
        server to various email lists."""
        self.smtp_server = self.config.get('email', 'smtp_server')
        self.nbsbot_email = self.config.get('email', 'nbsbot_email')
        self.covid_informatics_list = self.config.get('email', 'covid_informatics_list')
        self.covid_admin_list = self.config.get('email', 'covid_admin_list')
        self.covid_commander = self.config.get('email', 'covid_commander')

    def get_usps_user_id(self):
        """ Extract the USPS User ID from the config file for later use in the
        zip_code_lookup() method."""
        self.usps_user_id = self.config.get('usps', 'user_id')

    def send_smtp_email(self, receiver, subject, body, email_name):
        """ Send emails using an SMTP server """
        message = EmailMessage()
        message.set_content(body)
        message['Subject'] = subject
        message['From'] = self.nbsbot_email
        message['To'] = ', '.join([receiver])
        try:
           smtpObj = smtplib.SMTP(self.smtp_server)
           smtpObj.send_message(message)
           print(f"Successfully sent {email_name}.")
        except smtplib.SMTPException:
           print(f"Error: unable to send {email_name}.")

    def get_main_window_handle(self):
        """ Run after login to identify and store the main window handle that the handles for pop-up windows can be differentiated."""
        self.main_window_handle = self.current_window_handle

    def switch_to_secondary_window(self):
        """ Set a secondary window as the current window in order to interact with the pop up."""
        new_window_handle = None
        for handle in self.window_handles:
            if handle != self.main_window_handle:
                new_window_handle = handle
                break
        if new_window_handle:
            self.switch_to.window(new_window_handle)

    def select_checkbox(self, xpath):
        """ Ensure the a given checkbox or radio button is selected. If not selected then click it to select."""
        checkbox = self.find_element(By.XPATH, xpath)
        if not checkbox.is_selected():
            checkbox.click()

    def unselect_checkbox(self, xpath):
        """ Ensure the a given checkbox or radio button is not selected. If selected then click it to un-select."""
        checkbox = self.find_element(By.XPATH, xpath)
        if checkbox.is_selected():
            checkbox.click()

    def county_lookup(self, city, state):
        """ Use the Nominatim geocode service via the geopy API to look up the county of a given town/city and state."""
        geolocator = Nominatim(user_agent = 'nbsbot')
        location = geolocator.geocode(city + ', ' + state)
        if location:
            location = location[0].split(', ')
            county = [x for x in location if 'County' in x]
            if len(county) == 1:
                county = county[0].split(' ')[0]
            else:
                county = ''
        else:
            county = ''
        return county

    def zip_code_lookup(self, street, city, state):
        """ Given a street address, city, and state use the USPS API via the usps
        Python package to lookup the associated zip code."""
        address = Address(
            name='',
            address_1=street,
            city=city,
            state=state,
            zipcode=''
        )
        usps = USPSApi(self.usps_user_id, test=True)
        try:
            validation = usps.validate_address(address)
            if not 'Address Not Found' in json.dumps(validation.result):
                zip_code = validation.result['AddressValidateResponse']['Address']['Zip5']
            else:
                zip_code = ''
        except Exception:
            zip_code = ''
        return zip_code

    def check_for_error_page(self):
        """ See if NBS encountered an error."""
        error_page_path = '/html/body/table/tbody/tr/td/table/tbody/tr[2]/td/table/tbody/tr/td/table/tbody/tr[2]/td[1]'
        try:
            if self.ReadText(error_page_path) == '\xa0Error Page':
                nbs_error = True
            else:
                nbs_error = False
        except Exception:
            nbs_error = False
        return nbs_error

    def go_to_home_from_error_page(self):
        """ Go to NBS Home page from an NBS error page. """
        xpath = '/html/body/table/tbody/tr/td/table/tbody/tr[1]/td/table/tbody/tr/td/table/tbody/tr/td[1]/a'
        for _ in range(self.num_attempts):
            try:
                WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))
                self.find_element(By.XPATH, xpath).click()
                self.home_loaded = True
                break
            except TimeoutException:
                self.home_loaded = False
        if not self.home_loaded:
            sys.exit(print(f"Made {self.num_attempts} unsuccessful attempts to load Home page. A persistent issue with NBS was encountered."))

    def write_general_comment(self, note):
        """Write a note in the general comments box of an investigation."""
        xpath = '//*[@id="INV167"]'
        self.find_element(By.XPATH, xpath).send_keys(note)

    def RejectNotification(self, n=1):
        """ Reject notification on first case in notification queue.
        To be used when issues were encountered during review of the case."""
        print("issues seen in reject:", self.issues)
        reject_path = f'//*[@id="parent"]/tbody/tr[{n}]/td[2]/img'
        main_window_handle = self.current_window_handle
        WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, reject_path)))
        self.find_element(By.XPATH,reject_path).click()
        rejection_comment_window = None
        for handle in self.window_handles:
            if handle != main_window_handle:
                rejection_comment_window = handle
                break
        if rejection_comment_window:
            self.switch_to.window(rejection_comment_window)
            timestamp = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
            self.issues.append('-nbsbot ' + timestamp)
            self.find_element(By.XPATH,'//*[@id="rejectComments"]').send_keys(' '.join(self.issues))
            self.find_element(By.XPATH,'/html/body/form/table/tbody/tr[3]/td/input[1]').click()
            self.switch_to.window(main_window_handle)
            self.num_rejected += 1
            
    def ApproveNotification(self):
        """ Approve notification on first case in notification queue. """
        main_window_handle = self.current_window_handle
        self.find_element(By.XPATH,'//*[@id="createNoti"]').click()
        for handle in self.window_handles:
            if handle != main_window_handle:
                approval_comment_window = handle
                break
        self.switch_to.window(approval_comment_window)
        self.find_element(By.XPATH,'//*[@id="botcreatenotId"]/input[1]').click()
        self.switch_to.window(main_window_handle)
        self.num_approved += 1
        
    #new code added from covidnotificationbot, it also inherits from here
    def SendManualReviewEmail(self):
        """ Send email containing NBS IDs that required manual review."""
        if (len(self.not_a_case_log) > 0) | (len(self.lab_data_issues_log) > 0):
            subject = 'Cases Requiring Manual Review'
            email_name = 'manual review email'
            body = "COVID Commander,\nThe case(s) listed below have been moved to the rejected notification queue and require manual review.\n\nNot a case:"
            for id in self.not_a_case_log:
                body = body + f'\n{id}'
            body = body + '\n\nAssociated lab issues:'
            for id in self.lab_data_issues_log:
                body = body + f'\n{id}'
            body = body + '\n\n-Nbsbot'
            #self.send_smtp_email(recipient, cc, subject, body)
            self.send_smtp_email(self.covid_commander, subject, body, email_name)
            self.not_a_case_log = []
            self.lab_data_issues_log = []
