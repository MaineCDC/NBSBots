# -*- coding: utf-8 -*-
"""
Created on Wed Apr 17 10:50:29 2024

@author: Jared.Strauch
"""

from base import NBSdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from fractions import Fraction
import re
from dateutil.relativedelta import relativedelta
from geopy.geocoders import Nominatim
import pandas as pd
from io import StringIO
from bs4 import BeautifulSoup
import smtplib
from email.message import EmailMessage
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException
from selenium.common.exceptions import NoSuchElementException



class Giardia(NBSdriver):
    """ A class inherits all basic NBS functionality from NBSdriver and adds
    methods for reviewing COVID case investigations for data accuracy and completeness. """
    def __init__(self, production=False):
        super().__init__(production)
        self.num_approved = 0
        self.num_rejected = 0
        self.num_fail = 0

    def StandardChecks(self):
        self.Reset()
        self.initial_name = self.patient_name
        
        self.CheckFirstNam
        self.CheckLastNam
        self.CheckDO
        self.CheckAg
        self.CheckAgeTyp
        self.CheckCu
        self.CheckMortalit
        self.CheckStAdd
        # street_address = self.ReadText( '//*[@id="DEM159"]') #, 'Street address is blank.'
        if any(x in self.street_address for x in ["HOMELESS", "NO ADDRESS", "NO FIXED ADDRESS", "UNSHELTERED"]):
            pass
        else: 
            self.CheckCity()
            self.CheckZip()
            self.CheckCounty()
            
        self.CheckState()
        self.CheckCountry()
        # self.CheckPhone()
        self.CheckRace()
        self.CheckEthnicity()

        self.go_to_tab_two()
        self.CheckCaseStatus()

        self.missing_lab_report = True
        self.earliest_date_received = None
        self.latest_date_received = None
        self.lab_specimen_collection_date = None
        missing_tab = self.go_to_tab_five()
        print("lab=rep")
        if not missing_tab:
            self.CheckLabReports()
            if not self.returned_by_link:
                self.go_to_tab_two()

        self.CheckJurisdiction()
        self.CheckProgramArea()
        self.CheckInvestigationStartDate()
        self.CheckInvestigationStatus()
        self.CheckSharedIndidcator()
        self.CheckReportDates()
        self.CheckReportingSourceType()
        self.CheckReportingOrganization()
        self.CheckInvestigator()
        self.CheckDateAssigned()

        

        self.CheckLabTestResult()
        # if self.case_status == "Confirmed":
        self.CheckLabName()
        self.CheckLabTestType()
        self.CheckSpecimenSource()
        self.CheckDateSpecimenCollected()

        self.CheckIllnessOnset()
        self.CheckAgeData()
        self.CheckWasSymptomatic()
        self.CheckHospitalization()   
        self.CheckDeath()
        self.CheckPregnancyStatus()
        self.CheckPatientTreated()
        self.CheckImmuneCompromised()  
        self.CheckCoInfection()
        self.CheckSecondaryToANotherCase()
        self.CheckWhereDiseaseWasAcquired()
        self.CheckTransmissionMode()
        self.CheckDetectionMethod()
        self.CheckConfirmationMethod() 
        self.CheckConfirmationDate()
        self.VerifyCaseStatus()
        self.CheckMmwrWeek()
        self.CheckMmwrYear()
        self.CheckDateClosed()

    ####################### Patient Demographics Check Methods ############################
    def CheckAge(self):
        """ Must provide age. """
        self.age = self.ReadText('//*[@id="INV2001"]')
        if not self.age:
            self.issues.append('Age is blank.')
            print(f"age: {self.age}")
        
    def CheckAgeType(self):
        """ Must age type must be one of Days, Months, Years. """
        self.age_type = self.ReadText('//*[@id="INV2002"]')
        if not self.age_type:
            self.issues.append('Age Type is blank.')
            print(f"age_type: {self.age_type}")
        elif self.age_type != "Days" and self.age_type != "Months" and self.age_type != "Years":
            self.issues.append('Age Type is not one of Days, Months, or Years.')
            print(f"age_type: {self.age_type}")
        
    
    def CheckPhone(self):
        """ If a phone number is provided make sure it is ten digits. """
        home_phone = self.ReadText('//*[@id="DEM177"]')
        work_phone = self.ReadText('//*[@id="NBS002"]')
        cell_phone = self.ReadText('//*[@id="NBS006"]')
        if home_phone:
            #check if phone is ten digits if it exists
            if len(re.findall(r'\d', str(home_phone))) != 10:
                self.issues.append('Phone number is not ten digits.')
                print(f"home_phone: {home_phone}")
        elif work_phone:
            #check if phone is ten digits if it exists
            if len(re.findall(r'\d', str(work_phone))) != 10:
                self.issues.append('Phone number is not ten digits.')
                print(f"work_phone: {work_phone}")
        elif cell_phone:
            #check if phone is ten digits if it exists
            if len(re.findall(r'\d', str(cell_phone))) != 10:
                self.issues.append('Phone number is not ten digits.')
                print(f"cell_phone: {cell_phone}")

    def CheckCurrentSex(self):
        """ Ensure patient current sex is not blank. """
        self.patient_sex = self.ReadText('//*[@id="DEM113"]')
        if not self.patient_sex:
            self.issues.append('Patient sex is blank.')
        elif self.patient_sex == "Unknown":
            comment = self.ReadText('//*[@id="DEM196"]')
            if not comment:
                self.issues.append('Patient sex is Unknown without a note.')

    def CheckMortality(self):
        mortality_as_of_date = self.CheckForValue('//*[@id="NBS097"]', "Mortality fields on patient page should not be blank.")
        is_deceased = self.CheckForValue('//*[@id="DEM127"]', "Mortality fields on patient page should not be blank.")
    
    def CheckJurisdiction(self):
        jurisdiction = self.CheckForValue('//*[@id="INV107"]', 'Jurisdiction cannot be blank.')
        if jurisdiction not in self.county:
            self.issues.append("Jurisdiction and county mismatch.")

    def CheckStAddr(self):
        self.street_address = self.ReadText( '//*[@id="DEM159"]')
        if not self.street_address:
            self.issues.append("Street address cannot be blank.")

    def CheckRace(self):
        returned_race = self.ReadText( '//*[@id="patientRacesViewContainer"]')
        if not returned_race:
            self.issues.append("Race cannot be blank.")
        
        definitive_races = ['White', 'Black or African American', 'Asian', 'American Indian or Alaska Native', 'Native Hawaiian or Other Pacific Islander']  #New code
        if 'Unknown' in returned_race and any(def_race in returned_race for def_race in definitive_races):                                                  #New code
            self.issues.append('Case rejected: Definitive race and Unknown race should not be selected together.')                            #New code
            print(f"race: {returned_race}.")

        
    ####################### Navigation Methods ############################
    def GoToGiardiasis(self):
        giardiasis_path = '//*[@id="tabs0head1"]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, giardiasis_path)))
        self.find_element(By.XPATH, giardiasis_path).click()
    
    ####################### Investigation Check Methods ############################
    def CheckProgramArea(self):
        program = self.CheckForValue('//*[@id="INV108"]', 'should be disease specific')

    def CheckInvestigationStartDate(self):
        """ Verify investigation start date is on or after report date. """
        self.investigation_start_date = self.ReadDate('//*[@id="INV147"]')
        if not self.investigation_start_date:
            self.issues.append(f"Investigation start date: {self.investigation_start_date} cannot be blank.")
            print(f"investigation start date: {self.investigation_start_date}")

    def CheckInvestigationStatus(self):
        status = self.CheckForValue('//*[@id="INV109"]', 'Investigation status date cannot be blank')
        if status.lower() == "open":
            self.issues.append("Investigation status is listed as 'Open'")
    
    def CheckSharedIndidcator(self):
        indicator = self.CheckForValue('//*[@id="NBS_UI_19"]/tbody/tr[5]/td[2]', 'Shared indicator is blank')

    ####################### Investigator Check Methods ############################
    def CheckInvestigator(self):
        investigator = self.ReadText('//*[@id="INV180"]')

    def CheckDateAssigned(self):
        date_assigned = self.ReadDate('//*[@id="INV110"]')
        if not date_assigned:
            self.issues.append("date assigned cannot be blank.")

    ################# Key Report Dates Check Methods ###############################
    def CheckReportDates(self):
        """ Check if the current value of Report Date matches the earliest
        Report Date from the associated labs. """
        self.reported_state_date = self.ReadDate('//*[@id="INV120"]')
        self.reported_county_date = self.ReadDate('//*[@id="INV121"]')
        self.report_date = self.ReadDate('//*[@id="INV111"]')

        if not self.reported_state_date:
            self.issues.append('Missing date reported to state.')
        
        if not self.reported_county_date:
            self.issues.append('Missing date reported to county.')

        if not self.report_date:
            self.issues.append('Missing report date.')

        dates = [self.reported_state_date, self.reported_county_date, self.report_date]
        # if all(date != self.latest_date_received and date != self.earliest_date_received for date in dates):
        #     self.issues.append("date mismatch with received dates")
        if (self.latest_date_received not in dates and self.earliest_date_received not in dates and self.case_status != "Probable" and not self.missing_lab_report):
            self.issues.append(f"Lab received dates and reported dates mismatched.")

    ####################### Supplmental Check Methods ############################
    def CheckLabReports(self):
        """ Pull lab reports from supplemental tab. """
        #Lab report info is only displayed if you click on the button after tick-borne. There could be more than one.
        html = self.find_element(By.XPATH, '//*[@id="eventLabReport"]').get_attribute('outerHTML')
        soup = BeautifulSoup(html, 'html.parser')
        self.Lab_report_table = pd.read_html(StringIO(str(soup)))[0]
        if len(self.Lab_report_table) > 0:
            if any(self.Lab_report_table["Date Received"] == "Nothing found to display."):
                if self.case_status and self.case_status != "Probable": 
                    self.issues.append("Missing lab report.")
                self.missing_lab_report = True
                self.earliest_date_received = None
                self.latest_date_received = None
                self.lab_specimen_collection_date = None
                return
            self.missing_lab_report = False
            self.earliest_date_received = pd.to_datetime(self.Lab_report_table["Date Received"], format="%m/%d/%Y %I:%M %p").min().date()
            self.latest_date_received = pd.to_datetime(self.Lab_report_table["Date Received"], format="%m/%d/%Y %I:%M %p").max().date()
            self.lab_specimen_collection_date = pd.to_datetime(self.Lab_report_table["Date Collected"], format="%m/%d/%Y").max().date()
            try:
                self.find_element(By.XPATH, '//*[@id="eventLabReport"]/tbody/tr[1]/td[1]/a').click()
                self.lab_specimen_source = self.ReadText('//*[@id="LAB165"]').lower()
            except (TimeoutException, NoSuchElementException):
                self.lab_specimen_collection_date = None

            if not self.lab_specimen_collection_date:
                self.lab_specimen_collection_date = self.ReadDate('//*[@id="LAB163"]')
            self.find_element(By.XPATH, '(//div[contains(@class, "returnToPageLink")]//a)[1]').click()
            self.returned_by_link = True
        else:
            if self.case_status and self.case_status != "Probable":
                self.issues.append("Missing lab report.")


    ####################### Patient Status Check Methods ############################
    def CheckDeath(self):
        """If died from illness is yes or no, need a death date """
        self.death_indicator =  self.ReadText('//*[@id="INV145"]') #,'Died from illness must be yes or no.'
        print(f"death: {self.death_indicator}")
        # if self.death_indicator in ['Yes', 'No'] and not self.discharge_date:
        #     self.issues.append('Death indicator should be unknown if no discharge date.')
        if self.death_indicator == "Yes":
            """ Death date must be present."""
            death_date = self.ReadDate('//*[@id="INV146"]')
            if not death_date:
                self.issues.append('Date of death is missing.')
                print(f"death: {self.death_indicator}")
            elif death_date > self.now:
                self.issues.append('Date of death date cannot be in the future.')
                print(f"death: {self.death_indicator}")
        elif self.death_indicator not in ['Yes', 'No', 'Unknown'] and self.case_status in ["Confirmed", "Probable"]:
            self.issues.append('Did case die from this illness cannot be blank.')
            print(f"death: {self.death_indicator}")

    def CheckHospitalization(self):
        """ Read hospitalization status. If yes need date and hospital """
        self.hospitalization_indicator = self.ReadText('//*[@id="INV128"]')
        if self.hospitalization_indicator not in ['Yes', 'No']:
            # and self.case_status in ["Confirmed", "Probable"]: 
            self.issues.append("Hospitalized answer cannot be blank or unknown.")
        if self.hospitalization_indicator == 'Yes':
            hospital_name = self.ReadText('//*[@id="INV184"]')
            if not hospital_name:
                self.issues.append('Missing name of hospital.')
                print(f"hospitalization, hospital_name: {hospital_name}")
            self.admission_date = self.ReadDate('//*[@id="INV132"]')
            if not self.admission_date:
                self.issues.append('Missing hospital admission date.')
                print(f"hospitalization, admission_date: {self.admission_date}")
            self.discharge_date = self.ReadDate('//*[@id="INV133"]')
            self.duration_in_hospital = self.ReadText('//*[@id="INV134"]')
            if self.admission_date and self.discharge_date and not self.duration_in_hospital:
                self.issues.append('Duration of hospitalization missing.')
                print(f"duration in hospital: {self.duration_in_hospital}")
      
    def CheckPregnancyStatus(self):
        """ Check that pregnancy status isn't blank."""
        pregnant_status = self.ReadText('//*[@id="INV178"]')
        pregnancy_due_date = self.ReadDate('//*[@id="ME8170"]')
        # if pregnant_status not in ['Yes', 'No', 'Unknown'] and self.patient_sex != "Male":
        #     self.issues.append('Pregnant status is blank.')
        if pregnant_status == "Yes" and not pregnancy_due_date:
            self.issues.append("Pregnancy due date missing.")

    def CheckImmuneCompromised(self):
        """ If patient is immune compromised, need condition info """
        self.Immune_compromised = self.ReadText('//*[@id="ME3129"]')
        if not self.Immune_compromised and self.case_status in ["Confirmed", "Probable"]:
            self.issues.append("Immune compromised cannot be blank.")

    
    def CheckCoInfection(self):
        """ Check that pregnancy status isn't blank."""
        co_infection = self.ReadText('//*[@id="ME11173"]')
        co_infection_condition = self.ReadText('//*[@id="ME11174"]')
        if not co_infection and self.case_status in ["Confirmed", "Probable"]:
            self.issues.append("Co-infection field cannot be blank.")
        if co_infection == "Yes" and not co_infection_condition:
            self.issues.append("Missing co-infection condition.")
    
    ####################### Clinical Check Methods ############################
    def CheckLabName(self):
        """ Check for follow-up tests """
        self.laboratory_name = self.ReadText('//*[@id="ME6105"]')
        if not self.laboratory_name and self.case_status == "Confirmed":
            self.issues.append("Confirmed case but no laboratory name.")
        print(f"laboratory name: {self.laboratory_name}")
    
    def CheckLabTestType(self):
        """ Check for follow-up tests """
        self.laboratory_test_type = self.ReadText('//*[@id="ME15109"]')
        other_test_type = self.ReadText('//*[@id="ME15111"]')
        if not self.laboratory_test_type and self.case_status == "Confirmed":
            self.issues.append("Confirmed case but no laboratory test type.")
        print(f"laboratory test type: {self.laboratory_test_type}")

        if self.laboratory_test_type == "Other":
            if not other_test_type:
                self.issues.append("Lab Test Type is Other, but other test type is blank.")
    

    def CheckLabTestResult(self):
        """ Check for follow-up tests """
        self.laboratory_test_result = self.ReadText('//*[@id="ME15110"]')
        if self.laboratory_test_result != "Positive" and self.case_status == 'Confirmed':
            if self.laboratory_test_result.lower() == "pending":
                self.issues.append("Confirmed case but lab test result pending.")
            else:
                self.issues.append("Confirmed case but no lab test result selected.")
        print(f"laboratory test result: {self.laboratory_test_result}")

    def CheckSpecimenSource(self):
        """ Check for follow-up tests """
        specimen_source = self.ReadText('//*[@id="ME11165"]').lower()
        other_specimen_source = self.ReadText('//*[@id="ME12173"]')
        if not specimen_source:
            if self.case_status == "Confirmed":
                self.issues.append("Confirmed case but no specimen source selected.")
        else:
            if self.lab_specimen_source and specimen_source not in self.lab_specimen_source:
                self.issues.append("Specimen source doesn't match lab report: Needs EOC review.")
            
            if specimen_source == "Other" and not other_specimen_source:
                self.issues.append('Other speciment source cannot be vlank when speciment source is "Other"')
        print(f"specimen source: {specimen_source}")
        
    def CheckDateSpecimenCollected(self):
        """ Check for follow-up tests """
        date_specimen_collected = self.ReadDate('//*[@id="ME8117"]')
        if not date_specimen_collected and self.case_status == "Confirmed":
            self.issues.append("date specimen collected cannot be blank when Case status is confirmed.")
        else:
            if self.lab_specimen_collection_date and self.lab_specimen_collection_date != date_specimen_collected:
                self.issues.append("Specimen collection dates do not match dates on lab report.")
        print(f"date specimen collected: {date_specimen_collected}")
        

    def CheckSecondaryToANotherCase(self):
        secondary_to = self.CheckForValue('//*[@id="ME11175"]', 'secondary to another case cannot be blank')
        others_iii = self.CheckForValue('//*[@id="ME11176"]', 'Others III cannot be blank')
        if not secondary_to and self.case_status == ["Confirmed", "Probable"]:
            self.issues.append("Secondary to Another Case cannot be blank.")
        
        if not others_iii and self.case_status == ["Confirmed", "Probable"]:
            self.issues.append("Others ill cannot be blank.")
    
    def CheckDiagnosisDate(self):
        diagnosis_date = self.CheckForValue('//*[@id="INV136"]', 'Diagnosis date cannot be blank.')
        if diagnosis_date and diagnosis_date != self.collection_date:
            self.issues.append('Diagnosis date should be same as collection date.')

    def CheckIllnessOnset(self):
        """ Check if a patient has an illness onset date. """
        self.IllnessOnset = self.ReadDate('//*[@id="INV137"]')
        self.IllnessEnd = self.ReadDate('//*[@id="INV138"]')
        print(f"Illness_length: {self.IllnessOnset}")
        if self.IllnessOnset and self.IllnessEnd  and self.IllnessEnd < self.IllnessOnset:
            self.issues.append('Illness end date cannot precede illness onset date.')
            print(f"Illness_length: {self.IllnessOnset}")

        if not self.IllnessOnset and self.case_status in ["Confirmed", "Probable"]:
            self.issues.append(f'“Illness onset date: {self.IllnessOnset}” should not be blank.')
            print(f"Illness_onset: {self.IllnessOnset}")
    
    def CheckIllnessDuration(self):
        self.illnessDuration = self.ReadText('//*[@id="INV139"]')
        self.illnessDurationUnits = self.ReadText('//*[@id="INV140"]')

    def CheckAgeData(self):
        """ Check for follow-up tests """
        self.age_at_onset = self.ReadText('//*[@id="INV143"]')
        print(f"age at onset: {self.age_at_onset}")
        self.age_at_onset_units = self.ReadText('//*[@id="INV144"]')
        print(f"age at onset units: {self.age_at_onset}")

        if not self.age_at_onset and self.case_status in ["Confirmed", "Probable"]:
            self.issues.append('Age at onset is missing.')
        
        if not self.age_at_onset_units and self.case_status in ["Confirmed", "Probable"]:
            self.issues.append('Age at onset units is missing.')
        
    def CheckWasSymptomatic(self):

        """ Check for follow-up tests """
        self.symptomatic = self.ReadText('//*[@id="ME12174"]')
        print(f"was symptomatic: {self.symptomatic}")

        if self.symptomatic not in ["Yes", "No"] and self.case_status in ["Confirmed", "Probable"]:
            self.issues.append('Confirmed or probable needs to be symptomatic.')

    ####################### Epidemiologic Check Methods ############################
    def CheckWhereDiseaseWasAcquired(self):
        """ Check where disease was acquired."""
        disease_acquired = self.ReadText('//*[@id="INV152"]')
        imported_country = self.ReadText('//*[@id="INV153"]')
        imported_state = self.ReadText('//*[@id="INV154"]')

        if disease_acquired == "international" and not imported_country:
            self.issues.append("Internationally acquired but no country specified.")
        
        if disease_acquired == "Out of State" and not imported_state:
            self.issues.append("Out of state acquired but no state specified.")

    
    def CheckTransmissionMode(self):
        """ Check that transmission mode isn't blank."""
        transmission_mode = self.CheckForValue('//*[@id="INV157"]', "Transmission mode cannot be blank.")

    # def CheckConfirmationDate(self):
    #     confirmationDate = self.ReadDate('//*[@id="INV162"]')
    #     if not confirmationDate:
    #         self.issues.append("Confirmation date is missing.")

    def CheckDateClosed(self):
        date_closed = self.ReadDate('//*[@id="ME11163"]')
        date_closed_text = self.ReadText('//*[@id="ME11163"]')
        if not date_closed:
            self.issues.append(f"Date closed: {date_closed}-text{date_closed_text} should not be blank.")
            print(f"date_closed: {date_closed}-text{date_closed_text}")

    def CheckPatientTreated(self):
        patient_treated = self.ReadText('//*[@id="ME8171"]')
        if not patient_treated and self.case_status in ["Confirmed", "Probable"]:
            self.issues.append("Patient treated field cannot be blank.")

    def CheckCaseStatus(self):
        self.case_status = self.ReadText('//*[@id="INV163"]')

    def VerifyCaseStatus(self):
        confirmed = self.laboratory_test_result == "Positive" and self.symptomatic == "Yes"
        probable = self.symptomatic == "Yes" and "Epidemiologically linked" in self.confirmation_method
        
        if not self.case_status or self.case_status in ["Suspect", "Unknown"]:
            self.issues.append("Case status incorrect or missing.")
        elif self.case_status == "Confirmed" and not confirmed:
            self.issues.append("Does not meet confirmed case criteria.")
        elif self.case_status == "Probable" and not probable:
            self.issues.append("Does not meet probable case criteria.")
        elif self.case_status == "Not a Case" and (probable or confirmed):
            self.issues.append("Incorrect case status.")

        # if confirmed:
        #     if self.case_status != "Confirmed":
        #         self.issues.append("Meets case definition for a confirmed case but isn't a confirmed case")
        # elif probable:
        #     if self.case_status != "Probable":
        #         self.issues.append("Meets case definition for a probable case but isn't a probable case")
        # elif confirmed is False and probable is False and self.CaseStatus != "Not a Case":
        #     self.issues.append("Meets case definition for Not a Case case but isn't Not a Case")

    
    #### notification controls ####
    # def RejectNotification(self, n=1):
    #     """ Reject notification on first case in notification queue.
    #     To be used when issues were encountered during review of the case."""
    #     reject_path = f'//*[@id="parent"]/tbody/tr[{n}]/td[2]/img'
    #     main_window_handle = self.current_window_handle
    #     WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, reject_path)))
    #     self.find_element(By.XPATH,reject_path).click()
    #     rejection_comment_window = None
    #     for handle in self.window_handles:
    #         if handle != main_window_handle:
    #             rejection_comment_window = handle
    #             break
    #     if rejection_comment_window:
    #         self.switch_to.window(rejection_comment_window)
    #         timestamp = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    #         self.issues.append('-nbsbot ' + timestamp)
    #         self.find_element(By.XPATH,'//*[@id="rejectComments"]').send_keys(' '.join(self.issues))
    #         self.find_element(By.XPATH,'/html/body/form/table/tbody/tr[3]/td/input[1]').click()
    #         self.switch_to.window(main_window_handle)
    #         self.num_rejected += 1

    # def ApproveNotification(self):
    #     """ Approve notification on first case in notification queue. """
    #     main_window_handle = self.current_window_handle
    #     self.find_element(By.XPATH,'//*[@id="createNoti"]').click()
    #     for handle in self.window_handles:
    #         if handle != main_window_handle:
    #             approval_comment_window = handle
    #             break
    #     self.switch_to.window(approval_comment_window)
    #     self.find_element(By.XPATH,'//*[@id="botcreatenotId"]/input[1]').click()
    #     self.switch_to.window(main_window_handle)
    #     self.num_approved += 1
    
    def SendGiardiaEmail(self, body, inv_id):
        message = EmailMessage()
        message.set_content(body)
        message['Subject'] = f'Giardia Bot {inv_id}'
        message['From'] = self.nbsbot_email
        message['To'] = ', '.join(["disease.reporting@maine.gov"])
        smtpObj = smtplib.SMTP(self.smtp_server)
        smtpObj.send_message(message)
        print('sent email', inv_id)