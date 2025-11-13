from Base import NBSdriver
import pandas as pd
import smtplib, ssl
from email.message import EmailMessage
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, date
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from selenium import webdriver
driver=webdriver.Chrome()

class HepBNotificationReview(NBSdriver):
    """ A class to review HepB cases in the notification queue.
    It inherits from NBSdriver."""

    def __init__(self, production=False):
        super().__init__(production)
        self.num_approved = 0
        self.num_rejected = 0
        self.num_fail = 0
        # self.Reset()
        # self.read_config()
        # self.GetObInvNames()
        # self.not_a_case_log = []
        # self.lab_data_issues_log = []

    def StandardChecks(self):
        """ A method to conduct checks that must be done on all cases regardless of investigator. """
        self.Reset()
        self.initial_name = self.patient_name
        # Check Patient Tab
        self.CheckFirstName()
        self.CheckLastName()
        self.CheckDOB()
        self.CheckAge()
        self.CheckCurrentSex()
        self.CheckStAddr()
        self.CheckCity()
        self.CheckState()
        self.CheckZip()
        self.CheckCounty()
        self.CheckCountry()
        self.CheckEthnicity()
        self.CheckRace()
        self.GoToSupplementalTab() ### change Xpath whille pushing to production
        # Read Associated labs
        self.ReadAssociatedLabs()
        self.GetCollectionDate()
        self.GetReceivedDate()
        # # Check Case Info Tab
        self.GoToCaseInfo()
        self.CheckJurisdiction()
        self.CheckProgramArea()
        self.CheckInvestigationStartDate()
        self.CheckInvestigationStatus()
        self.CheckSharedIndicator()
        self.CheckInvestigationType() # acute or chronic
        ##investigator info
        self.CheckInvestigator()
        self.CheckInvestigatorAssignDate()
        # reporting info
        self.CheckReportDate()
        self.CheckCountyStateReportDate()
        self.CheckReportingSourceType()
        self.CheckReportingOrganization()
        self.CheckCaseStatusNew() #CaseStatusNew
        self.CheckMmwrYear()       
        self.GoToHepatitisCore()
        self.ReasonForTesting()
        self.CheckSymptoms() #symptoms
        self.CheckJaundice()
        self.CheckHospitalizationIndicator()
        if self.hospitalization_indicator == 'Yes':
            self.CheckAdmissionDate()
            self.CheckDischargeDate()
        self.CheckPregnancy() #pregnancy status
        self.CheckDieFromIllness()
        self.liverenzymelevels() #alt_sgpt_result
        self.CheckDiagnosticTestResults() #diagnostic test results
        self.CaseClassificationHepB()

    def CheckInvestigationType(self):
        """ Check if investigation type is acute or chronic."""
        self.investigation_type_name =self.find_element(By.XPATH, '//*[@id="bd"]/h1/table/tbody/tr[1]/td[1]/a')
        self.investigation_type = self.investigation_type_name.text.strip()
        investigation_type = self.investigation_type.lower()
        self.chronic_inv = False
        self.acute_inv = False
        if 'chronic' in investigation_type:
            self.chronic_inv = True
        elif 'acute' in investigation_type:
            self.acute_inv = True
        print(f"Investigation type: {self.investigation_type}")
        print(f"Chronic investigation: {self.chronic_inv}, Acute investigation: {self.acute_inv}")
       
    def CheckClosedDate(self):
        """ Check if a closed date is provided and makes sense"""
        closed_date = self.ReadDate('//*[@id="ME11163"]')
        if not closed_date:
            self.issues.append('Investigation closed date is blank.')
        elif closed_date > self.now:
            self.issues.append('Closed date cannot be in the future.')
        elif closed_date < self.investigation_start_date:
            self.issues.append('Closed date cannot be before investigation start date.')

#################### Hospital Check Methods ###################################
    def CheckHospitalizationIndicator(self):       #Was the patient hospitalized for this illness?:	
        """ Read hospitalization status. If an investigation was conducted it must be Yes or No """
        self.hospitalization_indicator = self.ReadText('//*[@id="INV128"]')
        self.hospital_name = self.ReadText('//*[@id="INV184"]')
        self.patient_die_from_illness = self.ReadText('//*[@id="INV145"]')
        if self.hospitalization_indicator.lower() not in ['yes', 'no']:
            self.issues.append("Patient hospitalized must be 'Yes' or 'No'.")
        elif self.hospitalization_indicator.lower() == 'yes' and not self.hospital_name:
            self.issues.append('Hospitalized but no hospital listed.')
        elif self.hospitalization_indicator.lower() == 'no' and self.hospital_name:
            self.issues.append('Hospitalized is No but hospital name is listed.')
            
    def CheckAdmissionDate(self):
        """ Check for hospital admission date."""
        self.admission_date = self.ReadDate('//*[@id="INV132"]')
        if self.admission_date and self.admission_date > self.now:
            self.issues.append('Admission date cannot be in the future.')
        if self.hospitalization_indicator.lower() == 'no' and self.admission_date:
            self.issues.append('Not hospitalized but Admission date is listed.')
        elif self.hospitalization_indicator.lower() == 'yes' and not self.admission_date:
            self.issues.append('Hospitalized but no Admission date.')

    def CheckDischargeDate(self):
        """ Check for hospital discharge date."""
        self.discharge_date = self.ReadDate('//*[@id="NBS_INV_GENV2_UI_3"]/tbody/tr[4]/td[2]|//*[@id="INV133"]')
        if self.hospitalization_indicator.lower() == "yes":
            if not self.discharge_date and self.patient_die_from_illness != 'Unknown':
                self.issues.append(f'patient hospitalized is {self.hospitalization_indicator} and patient die from illness is {self.patient_die_from_illness} but Discharge date is not listed.')
        elif self.hospitalization_indicator.lower() == 'no' and self.discharge_date:
            self.issues.append('Hospitalization indicator is No but discharge date is provided.')
        if self.admission_date:
            if self.discharge_date and self.discharge_date < self.admission_date:
                self.issues.append('Discharge date must be after admission date.')
        '''if self.discharge_date and self.patient_die_from_illness != 'Unknown':
            self.issues.append('If discharge date is listed then "Did patient die from this illness" should be Unknown.')'''
        if self.discharge_date:
            if not self.patient_die_from_illness:
                self.issues.append('Discharge date is listed - "Did patient die from this illness" cannot be blank.')
            if self.patient_die_from_illness == 'Unknown':
                self.issues.append('Discharge date is listed - "Did patient die from this illness" cannot be Unknown.')
        elif self.discharge_date and self.discharge_date > self.now:
            self.issues.append('Discharge date cannot be in the future.')
            
    def CheckDeathDate(self):
        """ Death date must be present."""
        death_date = self.ReadDate('//*[@id="INV146"]')
        if not death_date:
            self.issues.append('Date of death is blank.')
        elif death_date > self.now:
            self.issues.append('Date of death date cannot be in the future')

    def CheckProgramArea(self):
        """ Program area must be Airborne. """
        program_area = self.ReadText('//*[@id="INV108"]')
        if not program_area:
            self.issues.append('Program area is blank.')
        elif program_area != 'Hepatitis':
            self.issues.append('Program Area is not "Hepatitis".')
            
    def CheckSharedIndicator(self):
        """ Ensure shared indicator is yes. """
        shared_indicator = self.ReadText('//*[@id="NBS_UI_19"]/tbody/tr[5]/td[2]')
        if shared_indicator.lower() != 'yes':
            self.issues.append('Shared indicator not selected.')

    def CheckStateCaseID(self):
        """ State Case ID must be provided. """
        case_id = self.ReadText('//*[@id="INV173"]')
        if not case_id:
            self.issues.append('State Case ID is blank.')

########################### Parse and process labs ############################
    def GoToSupplementalTab(self):
        """ Navigate to the supplemental information tab."""
        supplemental_info_tab_path = '//*[@id="tabs0head6"]'
        for i in range(3):
            try:
                WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, supplemental_info_tab_path)))
                self.find_element(By.XPATH, supplemental_info_tab_path ).click()
                break
            except Exception as e:
                print(f"{e} has occured for supplemental_info_tab_path, retry_number: {i}")

    def ReadAssociatedLabs(self):
        """ Read table of associated labs."""
        self.labs = self.ReadTableToDF('//*[@id="viewSupplementalInformation1"]/tbody')
        self.name_match = False
        lab_reports = self.find_elements(By.XPATH, '//*[@id="eventLabReport"]/tbody/tr')
        self.dna_date, self.hbsag_date, self.total_anti_hbc_date, self.igm_anti_hbc_date, self.hbeag_date, self.anti_hbs_date, self.anti_hbe_date = (None,) * 7
        self.dna_dates = {}
        self.test_names = []
        self.text = ['hepatitis b virus dna', 'hepatitis b virus, dna', 'hepatitis b virus (hbv)','Hepatitis B virus (HBV)']
        self.text1 = ['hepatitis b virus surface antigen (hbsag)','hepatitis b virus surface antigen', 'hepatitis b virus surface ag', 'hbsag', 'hepatitis b surface ag','hepatitis b virus surface antigen, neutralization','hbsag confirmation','hep b surface ag','hepatitis b virus, antigen'] 
        self.text3 = ['igm anti-hbc', 'hep b core ab, igm', 'hepatitis b virus igm antibody', 'hepatitis b virus core antibody, igm']
        self.text2 = ['hepatitis b virus core ab', 'hepatitis b virus core antibody', 'hepatitis b virus total antibody', 'hbv core ab, igg/igm diff', 'hep b core ab, tot', 'total anti-hbc', 'hepatitis b virus core antibodies, total']
        self.text4 = ['hbeag', 'hepatitis b virus e antigen', 'hep b e ag', 'hepatitis be virus antigen (hbeag)']
        self.text5 = ['hepatitis b virus surface antibody', 'hepatitis b virus (hbv), antibody', 'hepatitis b virus surface antibody (hbsab)']
        self.text6 = ['anti-hbe', 'anti-hbe antibody', 'hepatitis b virus e antibody', 'hep be ab']
        for risk in lab_reports:
            cells = risk.find_elements(By.TAG_NAME, 'td')
            date_collected = datetime.strptime(cells[2].text.strip(), "%m/%d/%Y").date()
            if cells[3].find_elements(By.TAG_NAME, 'div'):
                div_tags = cells[3].find_elements(By.TAG_NAME, 'div')
                for tag in div_tags:
                    self.result = tag.text.strip()
                    data_exists = [x for x in self.text if x in self.result.lower()]
                    if data_exists:
                        if self.dna_dates.get('hepatitis b virus, dna'):
                            #if 'positive' in self.result.lower():
                            self.dna_dates['hepatitis b virus, dna'].append(date_collected)
                            self.test_names.append(self.result)
                        else:
                            #if 'positive' in self.result.lower():
                            self.dna_dates['hepatitis b virus, dna'] = [date_collected]
                            self.test_names.append(self.result)
                            
                    elif any(x in self.result.lower() for x in self.text1):
                        if self.dna_dates.get('hepatitis b virus surface antigen'):
                            if 'positive' in self.result.lower():
                                self.dna_dates['hepatitis b virus surface antigen'].append(date_collected)
                                self.test_names.append(self.result)
                        else:
                            self.dna_dates['hepatitis b virus surface antigen'] = [date_collected]
                            self.test_names.append(self.result)
                
                    elif any(x in self.result.lower() for x in self.text3):
                        if self.dna_dates.get('igm anti-hbc'):
                            self.dna_dates['igm anti-hbc'].append(date_collected)
                            self.test_names.append(self.result)
                        else:
                            self.dna_dates['igm anti-hbc'] = [date_collected]
                            self.test_names.append(self.result)
                            
                    elif any(x in self.result.lower() for x in self.text2):
                        if self.dna_dates.get('hepatitis b virus core ab'):
                            self.dna_dates['hepatitis b virus core ab'].append(date_collected)
                            self.test_names.append(self.result)
                        else:
                            self.dna_dates['hepatitis b virus core ab'] = [date_collected]
                            self.test_names.append(self.result)
                            
                    elif any(x in self.result.lower() for x in self.text4):
                        if self.dna_dates.get('hepatitis b virus e antigen'):
                            self.dna_dates['hepatitis b virus e antigen'].append(date_collected)
                            self.test_names.append(self.result)
                        else:
                            self.dna_dates['hepatitis b virus e antigen'] = [date_collected]
                            self.test_names.append(self.result)
                            
                    elif any(x in self.result.lower() for x in self.text5):
                        if self.dna_dates.get('hepatitis b virus surface antibody'):
                            self.dna_dates['hepatitis b virus surface antibody'].append(date_collected)
                            self.test_names.append(self.result)
                        else:
                            self.dna_dates['hepatitis b virus surface antibody'] = [date_collected]
                            self.test_names.append(self.result)
                            
                    elif any(x in self.result.lower() for x in self.text6):
                        if self.dna_dates.get('anti-hbe'):
                            self.dna_dates['anti-hbe'].append(date_collected)
                            self.test_names.append(self.result)
                        else:
                            self.dna_dates['anti-hbe'] = [date_collected]
                            self.test_names.append(self.result)
            else:
                self.result = cells[3].text.strip()
                if any(x in self.result.lower() for x in self.text):
                    if self.dna_dates.get('hepatitis b virus, dna'):
                        self.dna_dates['hepatitis b virus, dna'].append(date_collected)
                        self.test_names.append(self.result)
                    else:
                        self.dna_dates['hepatitis b virus, dna'] = [date_collected]
                        self.test_names.append(self.result)
                        
                elif any(x in self.result.lower() for x in self.text1):
                    if self.dna_dates.get('hepatitis b virus surface antigen'):
                        if 'positive' in self.result.lower():
                            self.dna_dates['hepatitis b virus surface antigen'].append(date_collected)
                            self.test_names.append(self.result)
                    else:
                        if 'positive' in self.result.lower():
                            self.dna_dates['hepatitis b virus surface antigen'] = [date_collected]
                            self.test_names.append(self.result)
                
                elif any(x in self.result.lower() for x in self.text3):
                    if self.dna_dates.get('igm anti-hbc'):
                        self.dna_dates['igm anti-hbc'].append(date_collected)
                        self.test_names.append(self.result)
                    else:
                        self.dna_dates['igm anti-hbc'] = [date_collected]
                        self.test_names.append(self.result)        
                
                elif any(x in self.result.lower() for x in self.text2):
                    if self.dna_dates.get('hepatitis b virus core ab'):
                        self.dna_dates['hepatitis b virus core ab'].append(date_collected)
                        self.test_names.append(self.result)
                    else:
                        self.dna_dates['hepatitis b virus core ab'] = [date_collected]
                        self.test_names.append(self.result)
                        
                elif any(x in self.result.lower() for x in self.text4):
                    if self.dna_dates.get('hepatitis b virus e antigen'):
                        self.dna_dates['hepatitis b virus e antigen'].append(date_collected)
                        self.test_names.append(self.result)
                    else:
                        self.dna_dates['hepatitis b virus e antigen'] = [date_collected]
                        self.test_names.append(self.result)
                        
                elif any(x in self.result.lower() for x in self.text5):
                    if self.dna_dates.get('hepatitis b virus surface antibody'):
                        self.dna_dates['hepatitis b virus surface antibody'].append(date_collected)
                        self.test_names.append(self.result)
                    else:
                        self.dna_dates['hepatitis b virus surface antibody'] = [date_collected]
                        self.test_names.append(self.result)
                        
                elif any(x in self.result.lower() for x in self.text6):
                    if self.dna_dates.get('anti-hbe'):
                        self.dna_dates['anti-hbe'].append(date_collected)
                        self.test_names.append(self.result)
                    else:
                        self.dna_dates['anti-hbe'] = [date_collected]
                        self.test_names.append(self.result)
        self.test1_names =  [x.split(':')[0].strip() for x in self.test_names]   
        self.result_check_dna = []
        self.result_check_antigen = []
        self.result_check_core = []
        self.result_check_igm = []
        self.result_check_anti_hbs = []
        self.result_check_hbeag = []
        self.result_check_anti_hbe = []
        for key, value in self.dna_dates.items():
            if key == "hepatitis b virus, dna":
                for x in self.test1_names:
                    for y in self.test_names:
                        if x.lower() in self.text:
                            if x in y:
                                self.result_check_dna = y.split(':')[1].strip().lower()
                                self.dna_date = min(value)
            elif key == "hepatitis b virus surface antigen":
                if len(value) > 1:
                    for x in self.test1_names:
                        for y in self.test_names:
                            if x.lower() in self.text1:
                                if x in y:
                                    self.result_check_antigen = y.split(':')[1].strip().lower()
                                    self.hbsag_date = min(value)
                else:
                    for x in self.test1_names:
                        for y in self.test_names:
                            if x.lower() in self.text1:
                                if x in y:
                                    self.result_check_antigen = y.split(':')[1].strip().lower()
                                    self.hbsag_date = min(value)
            elif key == "hepatitis b virus core ab":
                self.total_anti_hbc_date = min(value)
                for x in self.test1_names:
                    for y in self.test_names:
                        if x.lower() in self.text2:
                            if x in y:
                                self.result_check_core = y.split(':')[1].strip().lower()
            elif key == "igm anti-hbc":
                self.igm_anti_hbc_date = min(value)
                for x in self.test1_names:
                    for y in self.test_names:
                        if x.lower() in self.text3:
                            if x in y:
                                self.result_check_igm = y.split(':')[1].strip().lower()
            elif key == "hepatitis b virus e antigen":
                self.hbeag_date = min(value)
                for x in self.test1_names:
                    for y in self.test_names:
                        if x.lower() in self.text4:
                            if x in y:
                                self.result_check_hbeag = y.split(':')[1].strip().lower()
            elif key == "hepatitis b virus surface antibody":
                self.anti_hbs_date = min(value)
                for x in self.test1_names:
                    for y in self.test_names:
                        if x.lower() in self.text5:
                            if x in y:
                                self.result_check_anti_hbs = y.split(':')[1].strip().lower()
            elif key == "hepatitis b virus e antibody":
                self.hbeab_date = min(value)
                for x in self.test1_names:
                    for y in self.test_names:
                        if x.lower() in self.text6:
                            if x in y:
                                self.result_check_anti_hbe = y.split(':')[1].strip().lower()
        for index in range(len(self.labs)):
            row_df = self.labs.iloc[[index]]
            if row_df['Test Results'].str.contains('hepatitis b', na=False, case=False).any():
                self.labs = self.labs.loc[index]
                self.name_match = True
                break
        if not self.name_match:
            self.labs = pd.DataFrame()
            self.issues.append('Test results does not have hepatitis b.')

    def GetReceivedDate(self):
        """Find earliest report date by reviewing associated labs"""
        if self.labs['Date Received'][0] == 'Nothing found to display.':
            self.received_date = datetime(1900, 1, 1).date()
        else:
            if isinstance(self.labs['Date Received'], str):
                self.labs['Date Received'] = pd.to_datetime(self.labs['Date Received'],format = '%m/%d/%Y %I:%M %p').date()
                self.received_date = self.labs['Date Received']
            elif isinstance(self.labs['Date Received'], pd.Series):
                try:
                    self.labs['Date Received'] = pd.to_datetime(self.labs['Date Received'],format = '%m/%d/%Y %I:%M %p').dt.date
                except Exception as e:
                    self.labs['Date Received'] = pd.to_datetime(self.labs['Date Received'], errors='coerce').dt.date  #format = '%m/%d/%Y%I:%M %p',
                self.received_date = self.labs['Date Received'].min()

    def GetCollectionDate(self):
        """Find earliest collection date by reviewing associated labs"""
        if self.labs['Date Received'][0] == 'Nothing found to display.':
            self.collection_date = datetime(1900, 1, 1).date()
        else:
            # Check for any associated labs missing collection date:
            # 1. Set collection date to 01/01/2100 to avoid type errors.
            # 2. Log patient id for manual review.
            if isinstance(self.labs['Date Collected'], str):
                if self.labs['Date Collected'] == 'No Date':
                    if self.labs['Date Collected'] in ['No Date', 'Date Collected']:
                        self.labs['Date Collected'] = '01/01/2100'
                    self.issues.insert(0,'**SOME ASSOCIATED LABS MISSING COLLECTION DATE: CENTRAL EPI REVIEW REQUIRED**')
                    self.lab_data_issues_log.append(self.ReadPatientID())
                self.labs['Date Collected'] = pd.to_datetime(self.labs['Date Collected'], format = '%m/%d/%Y').date()
                self.collection_date = self.labs['Date Collected']
            elif isinstance(self.labs['Date Collected'], pd.Series):
                no_col_dt_labs = self.labs.loc[self.labs['Date Collected'] == 'No Date']
                if len(no_col_dt_labs) > 0:
                    self.labs.loc[self.labs['Date Collected'] == 'No Date', 'Date Collected'] = '01/01/2100'
                    self.issues.insert(0,'**SOME ASSOCIATED LABS MISSING COLLECTION DATE: CENTRAL EPI REVIEW REQUIRED**')
                    self.lab_data_issues_log.append(self.ReadPatientID())
                self.labs['Date Collected'] = pd.to_datetime(self.labs['Date Collected'], format = '%m/%d/%Y').dt.date
                self.collection_date = self.labs['Date Collected'].min()

    
    def CheckDieFromIllness(self):
        """ Died from illness should be yes or no. """
        self.did_patient_die_from_illness =  self.ReadText('//*[@id="INV145"]')
        self.illness_onset_date = self.ReadDate('//*[@id="INV137"]')
        self.is_patient_deceased=self.ReadText('//*[@id="DEM127"]')
        patient_deceased_date = self.ReadDate('//*[@id="DEM128"]')
        self.death_date = self.ReadDate('//*[@id="INV146"]')
        self.illness_end_date = self.ReadDate('//*[@id="INV138"]')
        if self.illness_end_date and self.illness_end_date < self.illness_onset_date:
            self.issues.append('Illness end date cannot be before onset date.')
        if self.hospitalization_indicator.lower() == 'yes' and not self.did_patient_die_from_illness:
            self.issues.append(f'patient hospitalized is {self.hospitalization_indicator} but "Did the patient die from this illness" is blank.')
        elif self.did_patient_die_from_illness.lower() == 'yes':
            if not self.is_patient_deceased or self.is_patient_deceased.lower() == 'no':
                self.issues.append(f'Patient died from illness is {self.did_patient_die_from_illness} but patient deceased is {self.is_patient_deceased}.')
            if not self.death_date:
                self.issues.append('Patient died from illness is yes but death date is blank.')
            if self.death_date and patient_deceased_date != self.death_date:
                self.issues.append('Patient died from illness is yes, patient deceased date should be the same as death date.') 
            if patient_deceased_date and patient_deceased_date > self.now :
                self.issues.append('Patient died from illness is yes but patient deceased date cannot be in the future.') 
            if self.death_date and self.illness_end_date and self.death_date != self.illness_end_date:
                self.issues.append('Patient died from illness is yes, death date should be the same as illness end date.')   
        elif self.did_patient_die_from_illness.lower() == 'unknown':
            if self.hospitalization_indicator.lower() == 'no':
                self.issues.append('Patient died from illness is unknown but patient hospitalized is no.')
            elif self.hospitalization_indicator.lower() == 'yes' and self.discharge_date:
                self.issues.append('Patient died from illness is unknown but patient hospitalized is yes and discharge date is not blank.')
            #if self.illness_end_date:
                #self.issues.append('Patient died from illness is unknown but illness end date is not blank.')
        '''elif self.did_patient_die_from_illness.lower() == 'no':
            if self.hospitalization_indicator.lower() == 'yes' and not self.discharge_date:
                self.issues.append('Patient died from illness is no but patient hospitalized is yes and discharge date is blank.')'''

    def liverenzymelevels(self):
        """ Check if ALT/SGPT result is provided and is a number."""
        self.alt_sgpt_result = self.ReadText('//*[@id="1742_6"]')
        self.alt_specimen_date = self.ReadDate('//*[@id="INV826"]')
        self.total_bilirubin_result = self.ReadText('//*[@id="ME119001"]')
        self.bili_specimen_date = self.ReadDate('//*[@id="ME120002"]')
        if self.alt_sgpt_result and not self.alt_specimen_date:
            self.issues.append('ALT/SGPT result is provided but specimen date is not.')
        if self.total_bilirubin_result and not self.bili_specimen_date:
            self.issues.append('Total Bilirubin result is provided but specimen date is not.')
        
    def CheckDiagnosticTestResults(self):  
        self.hbsag_specimen_date = self.ReadDate('//*[@id="LP38331_2_DT"]')
        self.hbsag_result = self.ReadText('//*[@id="LP38331_2"]')
        self.total_hbc_result = self.ReadText('//*[@id="LP38323_9"]')
        self.total_hbc_specimen_date = self.ReadDate('//*[@id="LP38323_9_DT"]')
        self.igm_hbc_result = self.ReadText('//*[@id="LP38325_4"]')
        self.igm_hbc_specimen_date = self.ReadDate('//*[@id="LP38325_4_DT"]')
        self.hbdna_result = self.ReadText('//*[@id="LP38320_5"]')
        self.hbdna_specimen_date = self.ReadDate('//*[@id="LP38320_5_DT"]')
        self.hbeag_result = self.ReadText('//*[@id="LP38329_6"]')
        self.hbeag_specimen_date = self.ReadDate('//*[@id="LP38329_6_DT"]')
        self.hbsab_result = self.ReadText('//*[@id="ME116006"]')
        self.hbsab_specimen_date = self.ReadDate('//*[@id="ME117002"]')
        self.hbeab_result = self.ReadText('//*[@id="ME121005"]')
        self.hbeab_specimen_date = self.ReadDate('//*[@id="ME121002"]')
        self.positive_results = ['detected', 'reactive', 'positive', 'pos']
        self.negative_results = ['not detected', 'negative', 'non-reactive','neg']
        
        dna_dates_new = {
            'hepatitis b virus, dna': [self.hbdna_result, self.hbdna_specimen_date],
            'hepatitis b virus surface antigen': [self.hbsag_result, self.hbsag_specimen_date],
            'hepatitis b virus core ab': [self.total_hbc_result, self.total_hbc_specimen_date],
            'igm anti-hbc': [self.igm_hbc_result, self.igm_hbc_specimen_date],
            'hepatitis b virus e antigen': [self.hbeag_result, self.hbeag_specimen_date],
            'hepatitis b virus surface antibody': [self.hbsab_result, self.hbsab_specimen_date],
            'anti-hbe': [self.hbeab_result, self.hbeab_specimen_date]
        }
        self.data = []
        self.data = [key.strip().lower() for key in self.dna_dates.keys() if key.strip().lower()]
        for item in self.data:
            if item.lower() in self.text:
                if item.lower() in dna_dates_new or [x for x in self.text if x == item.lower()]:
                    del dna_dates_new[item.lower()]
                if not self.hbdna_result:
                    self.issues.append('Hepatitis B DNA result is missing.')
                if not self.hbdna_specimen_date:
                    self.issues.append('Hepatitis B DNA result is provided but specimen date is not.')
                if self.dna_date and self.hbdna_specimen_date != self.dna_date:
                    self.issues.append('Hepatitis B DNA specimen date does not match the collection date from associated lab reports.')
                result_dna = (any(x in self.result_check_dna.lower() for x in self.positive_results) and any(x in self.hbdna_result.lower() for x in self.positive_results)) or (any(x in self.result_check_dna.lower() for x in self.negative_results) and any(x in self.hbdna_result.lower() for x in self.negative_results))
                if not result_dna:
                    self.issues.append(f'Hepatitis B DNA result and associated lab result- result mismatch.')
            if item.lower() in self.data:
                if item.lower() in self.text1:
                    if item.lower() in dna_dates_new or [x for x in self.text1 if x == item.lower()]:
                        del dna_dates_new[item.lower()]
                    if not self.hbsag_result:
                        self.issues.append('Hepatitis B surface antigen result is missing.')
                    if self.hbsag_result and not self.hbsag_specimen_date:
                        self.issues.append('Hepatitis B surface antigen result is provided but specimen date is not.')
                    if self.hbsag_date and self.hbsag_specimen_date != self.hbsag_date:
                        self.issues.append('Hepatitis B surface antigen specimen date does not match the collection date from associated lab reports.')
                    result_ag = (any(x in self.result_check_antigen.lower() for x in self.positive_results) and any(x in self.hbsag_result.lower() for x in self.positive_results)) or (any(x in self.result_check_antigen.lower() for x in self.negative_results) and any(x in self.hbsag_result.lower() for x in self.negative_results))
                    if not result_ag:
                        self.issues.append(f'Hepatitis B surface antigen result and associated lab result- result mismatch.')
            if item.lower() in self.text2:
                if item.lower() in dna_dates_new or [x for x in self.text2 if x == item.lower()]:
                    del dna_dates_new[item.lower()]
                if not self.total_hbc_result:
                    self.issues.append('Total Hepatitis B core antibody result is missing.')
                if self.total_hbc_result and not self.total_hbc_specimen_date:
                    self.issues.append('Total Hepatitis B core antibody result is provided but specimen date is not.')
                if self.total_anti_hbc_date and self.total_hbc_specimen_date != self.total_anti_hbc_date:
                    self.issues.append('Total Hepatitis B core antibody specimen date does not match the collection date from associated lab reports.')
                result_core = (any(x in self.result_check_core.lower() for x in self.positive_results) and any(x in self.total_hbc_result.lower() for x in self.positive_results)) or (any(x in self.result_check_core.lower() for x in self.negative_results) and any(x in self.total_hbc_result.lower() for x in self.negative_results))
                if not result_core:
                    self.issues.append(f'Total Hepatitis B core antibody result and associated lab result- result mismatch.')

            if item.lower() in self.text3:
                if item.lower() in dna_dates_new or [x for x in self.text3 if x == item.lower()]:
                    del dna_dates_new[item.lower()]
                if not self.igm_hbc_result:
                    self.issues.append('IgM Hepatitis B core antibody result is missing.')
                if self.igm_hbc_result and not self.igm_hbc_specimen_date:
                    self.issues.append('IgM Hepatitis B core antibody result is provided but specimen date is not.')
                if self.igm_anti_hbc_date and self.igm_hbc_specimen_date != self.igm_anti_hbc_date:
                    self.issues.append('IgM Hepatitis B core antibody specimen date does not match the collection date from associated lab reports.')
                result_igm = (any(x in self.result_check_igm.lower() for x in self.positive_results) and any(x in self.igm_hbc_result.lower() for x in self.positive_results)) or (any(x in self.result_check_igm.lower() for x in self.negative_results) and any(x in self.igm_hbc_result.lower() for x in self.negative_results))
                if not result_igm:
                    self.issues.append(f'IgM Hepatitis B core antibody result and associated lab result- result mismatch.')

            if item.lower() in self.text4:
                if item.lower() in dna_dates_new or [x for x in self.text4 if x == item.lower()]:
                    del dna_dates_new[item.lower()]
                if not self.hbeag_result:
                    self.issues.append('Hepatitis B e antigen result is missing.')
                if self.hbeag_result and not self.hbeag_specimen_date:
                    self.issues.append('Hepatitis B e antigen result is provided but specimen date is not.')
                if self.hbeag_date and self.hbeag_specimen_date and self.hbeag_specimen_date != self.hbeag_date:
                    self.issues.append('Hepatitis B e antigen specimen date does not match the collection date from associated lab reports.')
                result_hbeag = (any(x in self.result_check_hbeag.lower() for x in self.positive_results) and any(x in self.hbeag_result.lower() for x in self.positive_results)) or (any(x in self.result_check_hbeag.lower() for x in self.negative_results) and any(x in self.hbeag_result.lower() for x in self.negative_results))
                if not result_hbeag:
                    self.issues.append(f'Hepatitis B e antigen result and associated lab result- result mismatch.')

            if item.lower() in self.text5:
                if item.lower() in dna_dates_new or [x for x in self.text5 if x == item.lower()]:
                    del dna_dates_new[item.lower()]
                if not self.hbsab_result:
                    self.issues.append('Hepatitis B surface antibody result is missing.')
                if self.hbsab_result and not self.hbsab_specimen_date:
                    self.issues.append('Hepatitis B surface antibody result is provided but specimen date is not.')
                if self.anti_hbs_date and self.hbsab_specimen_date != self.anti_hbs_date:
                    self.issues.append('Hepatitis B surface antibody specimen date does not match the collection date from associated lab reports.')
                result_hbsab = (any(x in self.result_check_anti_hbs.lower() for x in self.positive_results) and any(x in self.hbsab_result.lower() for x in self.positive_results)) or (any(x in self.result_check_anti_hbs.lower() for x in self.negative_results) and any(x in self.hbsab_result.lower() for x in self.negative_results))
                if not result_hbsab:
                    self.issues.append(f'Hepatitis B surface antibody result and associated lab result- result mismatch.')

            if item.lower() in self.text6:
                if item.lower() in dna_dates_new or [x for x in self.text6 if x == item.lower()]:
                    del dna_dates_new[item.lower()]
                if not self.hbeab_result:
                    self.issues.append('Hepatitis B e antibody result is missing.')
                if self.hbeab_result and not self.hbeab_specimen_date:
                    self.issues.append('Hepatitis B e antibody result is provided but specimen date is not.')
                if self.hbeab_date and self.hbeab_specimen_date != self.hbeab_date:
                    self.issues.append('Hepatitis B e antibody specimen date does not match the collection date from associated lab reports.')
                result_hbeab = (any(x in self.result_check_anti_hbe for x in self.positive_results) and any(x in self.hbeab_result.lower() for x in self.positive_results)) or (any(x in self.result_check_anti_hbe.lower() for x in self.negative_results) and any(x in self.hbeab_result.lower() for x in self.negative_results))
                if not result_hbeab:
                    self.issues.append(f'Hepatitis B e antibody result and associated lab result- result mismatch.')
        for key, value in dna_dates_new.items():
            if value[0]:
                self.issues.append(f'{key} associated labs are not matching with diagnostic results.')
            if value[1]:
                self.issues.append(f'{key} associated labs are not matching with diagnostic specimen date.')
                 
    def CheckPregnancy(self):
        """ Check if patient is pregnant. """
        patient_sex = self.ReadText('//*[@id="DEM113"]')
        pregnant_status = self.ReadText('//*[@id="INV178"]')
        Due_date = self.ReadDate('//*[@id="INV579"]')
        self.delivered_infant = self.ReadText('//*[@id="ME116003"]')
        self.referral_perinatal_case = self.ReadText('//*[@id="ME122001"]')
        self.Delivery_date = self.ReadDate('//*[@id="ME116004"]')
        today = date.today()
        age_days = (today - self.dob).days
        if patient_sex and patient_sex.lower() == 'female' and  5113 <= age_days <= 18263 :
            if not pregnant_status:
                self.issues.append('Female of reproductive age, must enter pregnancy status.')
            if not self.delivered_infant:
                self.issues.append('Female of reproductive age, must enter if deliverd an infant in the past 24 months.')
            elif pregnant_status.lower() == 'yes':
                if not Due_date:
                    self.issues.append('Indicated case is pregnant but due date is missing (estimate is OK).')
            if self.delivered_infant.lower() == 'yes' and not self.Delivery_date :
                    self.issues.append('Indicated Delivered an infant in the last 24 months but date of delivery is missing (estimate is OK).')
            if (self.referral_perinatal_case.lower() == 'no' or not self.referral_perinatal_case) and (pregnant_status.lower() == 'yes' or self.delivered_infant.lower() == 'yes'):
                self.issues.append('If patient is pregnant or recently delivered then must be referred for perinatal case management.')
                    
    def CheckCaseStatusNew(self):
        """ Transmission mode should blank or airborne"""
        transmission_method =  self.ReadText('//*[@id="INV157"]')
        detection_method = self.ReadText('//*[@id="INV159"]')
        confirmation_method = self.ReadText('//*[@id="INV161"]')
        confirmation_date = self.ReadDate('//*[@id="INV162"]')
        self.current_case_status = self.ReadText('//*[@id="INV163"]')
        if not transmission_method:
            self.issues.append('Transmission mode is blank.')
        elif transmission_method not in ['Indeterminate','Bloodborne']:
            self.issues.append('Transmission mode should be Indeterminate or Bloodborne.')
        if not detection_method :
            self.issues.append('Detection method is blank.')
        if not confirmation_method:
            self.issues.append('Confirmation method is blank.')
        elif self.current_case_status == 'Confirmed' and confirmation_method !='Laboratory confirmed':
            self.issues.append('Confirmation method should be Laboratory confirmed if case status is confirmed.')
        elif self.current_case_status == 'Probable' and confirmation_method !='Laboratory report':
            self.issues.append('If probable, confirmation method should be Laboratory Report.')
        if not confirmation_date:
            self.issues.append('Confirmation date is blank.')
        elif confirmation_date < self.received_date:
            self.issues.append('Confirmation date cannot be prior to report date.')
        elif confirmation_date > self.now:
            self.issues.append('Confirmation date cannot be in the future.')
        """ Case status must be consistent with associated labs. """
        if not self.current_case_status or self.current_case_status in ['Unknown', 'Suspect']:
            self.issues.append('Case status is unknown or suspect or blank.')
            
    def GoToHepatitisCore(self):
        hepatitis_core_tab_path = '//*[@id="tabs0head2"]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, hepatitis_core_tab_path)))
        self.find_element(By.XPATH, hepatitis_core_tab_path ).click()
    
    def GoToHepExtension(self):
        hepatitis_extension_tab_path = '//*[@id="tabs0head3"]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, hepatitis_extension_tab_path)))
        self.find_element(By.XPATH, hepatitis_extension_tab_path ).click()    
    
    def ReasonForTesting(self):
        self.reason_for_testing = self.ReadText('//*[@id="INV575"]')
        alt_sgpt_results = self.ReadText('//*[@id="1742_6"]')
        total_bilirubin_result = self.ReadText('//*[@id="ME119001"]')
        self.is_patient_symptomatic = self.ReadText('//*[@id="INV576"]')
        self.was_patient_jaundiced = self.ReadText('//*[@id="INV578"]')
        
        if not self.reason_for_testing:
            self.issues.append('Must select reason for testing.')
        elif self.reason_for_testing == 'Prenatal screening' and self.patient_sex != 'Female' and 14 <= self.age >= 49:
            self.issues.append('Prenatal screening but patient is not female of reproductive age.')
        elif self.reason_for_testing == 'Screening of asymptomatic patient w/ risk factors':
            self.GoToHepExtension()
            if self.chronic_inv:
                if self.is_patient_symptomatic == "Yes" or self.was_patient_jaundiced == "Yes":### write code for asymptomatic patient with risk factors and without risk factors
                    self.issues.append('Reason for testing is screening of asymptomatic patient with risk factors but patient is symptomatic or was jaundiced.')
                if self.is_patient_symptomatic == "No" or self.was_patient_jaundiced == "No":
                    patient_employed_medical = self.ReadText('//*[@id="INV648"]') # yes, no, unknown
                    mothers_country_of_birth = self.ReadText('//*[@id="MTH109"]')  #UNITED STATES
                    self.risks = self.ReadElement('//*[@id="NBS_INV_HEPCHBC_UI_4"]/tbody')
                    row_data = []
                    if self.risks:
                        cells = self.risks.find_elements(By.TAG_NAME, 'td')
                        #cells = [risk.text for risk in cells if risk.text]
                        #row_data.extend(cells)
                    if patient_employed_medical: 
                        row_data.append(patient_employed_medical)
                    if mothers_country_of_birth:
                        row_data.append('Yes' if mothers_country_of_birth != "UNITED STATES" else "No")
                    row_data1 = [x.split(':')[1].strip() for x in row_data]
                    if 'Yes' in set(row_data1):
                        pass
                    elif 'Yes' not in set(row_data1):
                        self.issues.append('Risk factors are blank.')
                    elif 'No' in set(row_data1) or 'Unknown' in set(row_data1):
                        self.issues.append('Reason for testing is screening of asymptomatic patient with risk factors but no risk factors are listed.')
            elif self.acute_inv:
                period_prior_to_onset = self.ReadText('//*[@id="INV602"]')  
                types_of_contacts = self.ReadElement('//*[@id="NBS_INV_HEPACBC_UI_7"]/tbody')
                sexual_drug_exposure = self.ReadElement('//*[@id="NBS_INV_HEPACBC_UI_9"]/tbody')
                tattoting_risk_factors = self.ReadElement('//*[@id="NBS_INV_HEPACBC_UI_16"]/tbody')
                incarceration_risk_factors = self.ReadElement('//*[@id="NBS_INV_HEPACBC_UI_19"]/tbody')
                incarceration_six_months = self.ReadElement('//*[@id="NBS_INV_HEPACBC_UI_20"]/tbody')
                self.male_sex_partners = self.ReadText('//*[@id="INV605"]')
                self.female_sex_partners = self.ReadText('//*[@id="INV606"]')
                row_data_new = []
                if sexual_drug_exposure:
                    cells = sexual_drug_exposure.find_elements(By.TAG_NAME, 'tr')
                    for risk in cells:
                        cells = risk.find_elements(By.TAG_NAME, 'td')
                        row_data_new.extend([risk.text for risk in cells if risk.text])
                if tattoting_risk_factors:
                    cells = tattoting_risk_factors.find_elements(By.TAG_NAME, 'tr')
                    for risk in cells:
                        cells = risk.find_elements(By.TAG_NAME, 'td')
                        row_data_new.extend([risk.text for risk in cells if risk.text])
                if incarceration_risk_factors:
                    cells = incarceration_risk_factors.find_elements(By.TAG_NAME, 'tr')
                    for risk in cells:
                        cells = risk.find_elements(By.TAG_NAME, 'td')
                        row_data_new.extend([risk.text for risk in cells if risk.text])
                if incarceration_six_months:
                    cells = incarceration_six_months.find_elements(By.TAG_NAME, 'tr')
                    for risk in cells:
                        cells = risk.find_elements(By.TAG_NAME, 'td')
                        row_data_new.extend([risk.text for risk in cells if risk.text])
                if types_of_contacts:
                    cells = types_of_contacts.find_elements(By.TAG_NAME, 'tr')
                    for risk in cells:
                        cells = risk.find_elements(By.TAG_NAME, 'td')
                        row_data_new.extend([risk.text for risk in cells if risk.text])
                if self.male_sex_partners and self.female_sex_partners and (int(self.male_sex_partners)>0 or int(self.female_sex_partners)>0):
                    row_data_new.append('Yes')
                if period_prior_to_onset: 
                    row_data_new.append(period_prior_to_onset)
                row_data2 = [x.split(':')[1].strip() for x in row_data_new]
                if 'Yes' in set(row_data2):
                        pass
                elif 'Yes' not in set(row_data2):
                    self.issues.append('Risk factors are blank.')
                elif 'No' in set(row_data2) or 'Unknown' in set(row_data2):  
                    self.issues.append('Reason for testing is screening of asymptomatic patient with risk factors but no risk factors are listed.')
                self.GoToHepatitisCore()
        elif self.reason_for_testing == 'Screening of asymptomatic patient w/o risk factors':
            self.GoToHepExtension()
            if self.chronic_inv:
                if self.is_patient_symptomatic == "Yes" or self.was_patient_jaundiced == "Yes":### write code for asymptomatic patient with risk factors and without risk factors
                    self.issues.append('Reason for testing is screening of asymptomatic patient with risk factors but patient is symptomatic or was jaundiced.')
                if self.is_patient_symptomatic == "No" or self.was_patient_jaundiced == "No":
                    row_data = []
                    patient_employed_medical = self.ReadText('//*[@id="INV648"]') # yes, no, unknown
                    mothers_country_of_birth = self.ReadText('//*[@id="MTH109"]')  #UNITED STATES
                    self.risks = self.ReadElement('//*[@id="NBS_INV_HEPCHBC_UI_4"]/tbody')
                    if self.risks:
                        cells = self.risks.find_elements(By.TAG_NAME, 'tr')
                        for risk in cells:
                            cells = risk.find_elements(By.TAG_NAME, 'td')
                            row_data.extend([risk.text for risk in cells if risk.text])
                    if patient_employed_medical:
                        row_data.append(patient_employed_medical)
                    if mothers_country_of_birth:
                        row_data.append('Yes' if mothers_country_of_birth != "UNITED STATES" else "No")
                    if 'Yes' in set(row_data) or 'Unknown' in set(row_data):
                        self.issues.append('Reason for testing is screening of asymptomatic patient without risk factors but risk factors are listed.')
            elif self.acute_inv:
                period_prior_to_onset = self.ReadText('//*[@id="INV602"]')  
                types_of_contacts = self.ReadElement('//*[@id="NBS_INV_HEPACBC_UI_7"]/tbody')
                sexual_drug_exposure = self.ReadElement('//*[@id="NBS_INV_HEPACBC_UI_9"]/tbody')
                tattoting_risk_factors = self.ReadElement('//*[@id="NBS_INV_HEPACBC_UI_16"]/tbody')
                incarceration_risk_factors = self.ReadElement('//*[@id="NBS_INV_HEPACBC_UI_19"]/tbody')
                incarceration_six_months = self.ReadElement('//*[@id="NBS_INV_HEPACBC_UI_20"]/tbody')
                self.male_sex_partners = self.ReadText('//*[@id="INV605"]')
                self.female_sex_partners = self.ReadText('//*[@id="INV606"]')
                row_data_new = []
                if sexual_drug_exposure:
                    cells = sexual_drug_exposure.find_elements(By.TAG_NAME, 'tr')
                    for risk in cells:
                        cells = risk.find_elements(By.TAG_NAME, 'td')
                        row_data_new.extend([risk.text for risk in cells if risk.text])
                if tattoting_risk_factors:
                    cells = tattoting_risk_factors.find_elements(By.TAG_NAME, 'tr')
                    for risk in cells:
                        cells = risk.find_elements(By.TAG_NAME, 'td')
                        row_data_new.extend([risk.text for risk in cells if risk.text])
                if incarceration_risk_factors:
                    cells = incarceration_risk_factors.find_elements(By.TAG_NAME, 'tr')
                    for risk in cells:
                        cells = risk.find_elements(By.TAG_NAME, 'td')
                        row_data_new.extend([risk.text for risk in cells if risk.text])
                if incarceration_six_months:
                    cells = incarceration_six_months.find_elements(By.TAG_NAME, 'tr')
                    for risk in cells:
                        cells = risk.find_elements(By.TAG_NAME, 'td')
                        row_data_new.extend([risk.text for risk in cells if risk.text])
                if types_of_contacts:
                    cells = types_of_contacts.find_elements(By.TAG_NAME, 'tr')
                    for risk in cells:
                        cells = risk.find_elements(By.TAG_NAME, 'td')
                        row_data_new.extend([risk.text for risk in cells if risk.text])
                if period_prior_to_onset: 
                    row_data_new.append(period_prior_to_onset)
                if self.male_sex_partners or self.female_sex_partners or (int(self.male_sex_partners)>0 or int(self.female_sex_partners)>0):
                    row_data_new.append('Yes')
                if 'Yes' in set(row_data_new) or 'Unknown' in set(row_data_new):
                    self.issues.append('Reason for testing is screening of asymptomatic patient without risk factors but risk factors are listed.')
                self.GoToHepatitisCore()
        elif self.reason_for_testing == 'Symptoms of acute hepatitis':
            if self.is_patient_symptomatic != 'Yes' or self.was_patient_jaundiced != 'Yes':
                self.issues.append('Reason for testing is symptoms of acute hepatitis but no symptoms are listed.')
        elif self.reason_for_testing == 'Unknown':
            pass
        elif self.reason_for_testing == 'Year of birth (1945-1965)':
            if not self.dob or (self.dob.year < 1945 or self.dob.year > 1965):
                self.issues.append('Year of birth is not between 1945 and 1965 but reason for testing is year of birth.')
        elif self.reason_for_testing.lower() == 'Other (specify)':
            other_reason_for_testing = self.ReadText('//*[@id="INV901"]')
            if not other_reason_for_testing:
                self.issues.append('Other is selected for reason for testing but did not specify other reason for testing.')
        self.GoToHepatitisCore() 
        '''if self.reason_for_testing.lower() == 'evaluation of elevated liver enzymes': 
            if total_bilirubin_result and alt_sgpt_results:
                try:
                    alt_value = int(alt_sgpt_results) if alt_sgpt_results else 0
                    bili_value = float(total_bilirubin_result) if total_bilirubin_result else 0.0
                    if alt_value < 200 or bili_value < 3.0:
                        self.issues.append('Reason for testing is evaluation of elevated liver enzymes but ALT < 200 or Bili < 3.0.')
                except ValueError:
                    self.issues.append('ALT/SGPT result is not a valid number.')
            else:
                self.issues.append('Reason for testing is evaluation of elevated liver enzymes but ALT/SGPT or Total Bilirubin result is not provided.')'''

    def CheckSymptoms(self):
        """ Check if symptoms are indicated. """
        self.symptoms = self.ReadText('//*[@id="ME117001"]')
        self.jaundice_onset_date = self.ReadDate('//*[@id="ME116002"]')
        self.illness_onset_date = self.ReadDate('//*[@id="INV137"]')
        if self.is_patient_symptomatic.lower() == 'yes':
            if not self.symptoms:
                self.issues.append('Symptoms is Yes but no symptoms are listed.')
            elif self.symptoms.lower() == 'none':
                self.issues.append('Symptomatic but no symptoms are listed.')
            if not self.illness_onset_date :
                self.issues.append('Symptomatic but no onset date is listed.')
    
    def CheckJaundice(self):
        """ Check if patient was jaundiced. """
        if self.was_patient_jaundiced.lower() == 'yes' and not self.jaundice_onset_date:
            self.issues.append('Patient was jaundiced but no jaundice onset date is listed.')

    def CaseClassificationHepB(self):
        from dateutil.relativedelta import relativedelta
        """ Check if patient is pregnant. """
        diff = relativedelta(self.now, self.dob)
        months_diff = diff.years * 12 + diff.months
        previous_investigation_acute = self.ReadText('//*[@id="ME10099141"]')  
        previous_inv_acute_date = self.ReadDate('//*[@id="ME10099138"]')
        previous_investigation_chronic = self.ReadText('//*[@id="ME10099142"]')  
        previous_inv_chronic_date = self.ReadDate('//*[@id="ME10099140"]')
        documented_neg_hbsag_test = self.ReadText('//*[@id="ME10095102"]') 
        neg_hbsag_date = self.ReadDate('//*[@id="ME10083106"]')
        self.symptoms_likely_diagnosis = self.ReadText('//*[@id="ME10083103"]')  # xpath for symptoms likely diagnosis
        self.diagnosed_another_state = self.ReadText('//*[@id="ME10095108"]')  # xpath for diagnosed another state
        if self.diagnosed_another_state.lower() == "yes" and self.current_case_status.lower() != "not a case":
            self.issues.append('Incorrect case classification, should be not a case.')
        elif self.diagnosed_another_state.lower() == "yes" and self.current_case_status.lower() == "not a case":
            self.issues = []
            pass
        elif months_diff > 24:
            combined_texts = [t.lower() for t in self.text + self.text1 + self.text4]
            check_items = [x.lower() for x in self.test1_names if x.lower() in combined_texts]
            if (any(x in self.result_check_dna for x in self.positive_results) or any(x in self.result_check_antigen for x in self.positive_results) or any(x in self.result_check_hbeag for x in self.positive_results)):
                if previous_investigation_chronic.lower() in ["confirmed", "probable"]:
                    if self.current_case_status.lower() != "not a case":
                        self.issues.append('Incorrect case classification, should be not a case.')
                    elif self.current_case_status.lower() == "not a case":
                        self.issues = []
                        pass
                elif previous_investigation_acute.lower() in ["confirmed", "probable"]:
                    time_diff = self.collection_date - previous_inv_acute_date
                    diff_months = time_diff.days
                    if time_diff.days > 180:
                        if self.chronic_inv == False or self.current_case_status.lower() != "confirmed":
                            self.issues.append('incorrect case classification, should be chronic confirmed hepatitis b.')
                    else:
                        if self.current_case_status.lower() != "not a case":
                            self.issues.append('incorrect case classification, should be not a case.')
                        elif self.current_case_status.lower() == "not a case":
                            self.issues = []
                            pass
                else:
                    if documented_neg_hbsag_test.lower() == "yes":
                        if self.acute_inv == False or self.current_case_status.lower() != "confirmed":
                            self.issues.append('incorrect case classification, should be acute confirmed.')
                    elif not documented_neg_hbsag_test or documented_neg_hbsag_test.lower() == "no":
                        if any(item in self.text for item in self.data) and any(x in self.result_check_dna for x in self.positive_results): # dna positive
                            if any(item in self.text3 for item in self.data) and any(x in self.result_check_igm for x in self.positive_results): # igm positive
                                if self.acute_inv == False or self.current_case_status.lower() != "confirmed":
                                    self.issues.append('incorrect case classification, should be acute confirmed.')
                            else:
                                if any(item in self.text3 for item in self.data) and any(x in self.result_check_igm for x in self.negative_results): # igm negative
                                    if self.chronic_inv == False or self.current_case_status.lower() != "confirmed":
                                        self.issues.append('incorrect case classification, should be chronic confirmed.')    
                                elif not self.result_check_igm or self.result_check_igm.lower() == "unknown":
                                    if self.was_patient_jaundiced.lower() == 'yes' or (self.alt_sgpt_result and int(self.alt_sgpt_result) >200) or (self.total_bilirubin_result and self.total_bilirubin_result.replace('.','',1).isdigit()and float(self.total_bilirubin_result)>3.0):
                                        if not self.symptoms_likely_diagnosis or self.symptoms_likely_diagnosis.lower() == "yes":
                                            if self.chronic_inv == False or self.current_case_status.lower() != "confirmed":
                                                self.issues.append('incorrect case classification, should be chronic confirmed.') 
                                        else:
                                            if self.acute_inv == False or self.current_case_status.lower() != "confirmed":
                                                self.issues.append('incorrect case classification, should be acute confirmed.')
                                    else:
                                        if self.chronic_inv == False or self.current_case_status.lower() != "confirmed":
                                            self.issues.append('incorrect case classification, should be chronic confirmed.')
                        #dna negative condition
                        else:
                            if  any(item not in self.text for item in self.data)  or (self.data in self.text and any(x in self.result_check_dna for x in self.negative_results)): # dna negative
                                if any(item in self.text1 for item in self.data) and any(x in self.result_check_antigen for x in self.positive_results):# surface antigen positive
                                    if any(item in self.text3 for item in self.data) and any(x in self.result_check_igm for x in self.positive_results): # igm positive
                                        if self.acute_inv == False and self.current_case_status.lower() != "confirmed":
                                            self.issues.append('incorrect case classification, should be acute confirmed.')
                                    elif any(item in self.text3 for item in self.data) and any(x in self.result_check_igm for x in self.negative_results):# igm negative
                                        if any(item in self.text2 for item in self.data) and any(x in self.result_check_core for x in self.positive_results):# total antibody positive
                                            if self.chronic_inv == False and self.current_case_status.lower() != "confirmed":
                                                self.issues.append('incorrect case classification, should be chronic confirmed.')
                                        else:
                                            if any(item in self.text2 for item in self.data) and any(x in self.result_check_core for x in self.negative_results):# total antibody negative
                                                if self.current_case_status.lower() != "not a case":
                                                    self.issues.append('incorrect case classification, should be not a case.')
                                                elif self.current_case_status.lower() == "not a case":
                                                    self.issues = []
                                                    pass
                                            elif not self.total_hbc_result or self.total_hbc_result.lower() == "unknown":# total antibody unknown/Not done
                                                if self.chronic_inv == False or self.current_case_status.lower() != "probable":
                                                    self.issues.append('incorrect case classification, should be chronic probable.')
                                    #anti HBc igm - no/ not done condition
                                    else:
                                        if not self.result_check_igm or self.result_check_igm.lower() == "unknown":# igm unknown/ not done
                                            if self.was_patient_jaundiced.lower() == 'yes' or (self.alt_sgpt_result and int(self.alt_sgpt_result) >200) or (self.total_bilirubin_result and self.total_bilirubin_result.replace('.','',1).isdigit()and float(self.total_bilirubin_result)>3.0):
                                                if not self.symptoms_likely_diagnosis or self.symptoms_likely_diagnosis.lower() == "yes":
                                                    if any(item in self.text4 for item in self.data) and any(x in self.result_check_hbeag for x in self.positive_results):# hbeag positive
                                                        if self.chronic_inv == False and self.current_case_status.lower() != "confirmed":
                                                            self.issues.append('incorrect case classification, should be chronic confirmed.')
                                                    else:
                                                        if any(item in self.text2 for item in self.data) and any(x in self.result_check_core for x in self.positive_results):
                                                            if self.chronic_inv == False and self.current_case_status.lower() != "confirmed":
                                                                self.issues.append('incorrect case classification, should be chronic confirmed.')
                                                        elif any(item in self.text2 for item in self.data) and any(x in self.result_check_core for x in self.negative_results):
                                                            if self.chronic_inv == False or self.current_case_status.lower() != "probable":
                                                                self.issues.append('incorrect case classification, should be chronic probable.')
                                                else:
                                                    if self.acute_inv == False and self.current_case_status.lower() != "probable":
                                                        self.issues.append('incorrect case classification, should be acute probable.')
                                            else:
                                                if any(item in self.text4 for item in self.data) and any(x in self.result_check_hbeag for x in self.positive_results):# hbeag positive
                                                    if self.chronic_inv == False or self.current_case_status.lower() != "confirmed":
                                                        self.issues.append('incorrect case classification, should be chronic confirmed.')
                                                elif not self.result_check_hbeag or any(x in self.result_check_hbeag for x in self.negative_results):
                                                    if any(item in self.text2 for item in self.data) and any(x in self.result_check_core for x in self.positive_results):# total antibody positive
                                                            if self.chronic_inv == False and self.current_case_status.lower() != "confirmed":
                                                                self.issues.append('incorrect case classification, should be chronic confirmed.')
                                                    elif any(item in self.text2 for item in self.data) and any(x in self.result_check_core for x in self.negative_results):# total antibody negative
                                                        if self.chronic_inv == False or self.current_case_status.lower() != "probable":
                                                            self.issues.append('incorrect case classification, should be chronic probable.')
                            else:
                                    if any(item in self.text1 for item in self.data) and any(x in self.result_check_antigen for x in self.negative_results):# surface antigen negative
                                        if any(item in self.text4 for item in self.data) and any(x in self.result_check_hbeag.lower() for x in self.positive_results):# hbeag positive
                                            if any(item in self.text3 for item in self.data) and any(x in self.result_check_igm.lower() for x in self.positive_results):# igm positive
                                                if self.acute_inv == False and self.current_case_status.lower() != "confirmed":
                                                    self.issues.append('incorrect case classification, should be acute confirmed.')
                                            else:
                                                if any(item in self.text3 for item in self.data) and any(x in self.result_check_igm.lower() for x in self.negative_results):# igm negative
                                                    if any(item in self.text2 for item in self.data) and any(x in self.result_check_core.lower() for x in self.positive_results):# total antibody positive
                                                        if self.chronic_inv == False and self.current_case_status.lower() != "confirmed":
                                                            self.issues.append('incorrect case classification, should be chronic confirmed.')
                                                    else:
                                                        if any(item in self.text2 for item in self.data) and any(x in self.result_check_core.lower() for x in self.negative_results):# total antibody negative
                                                            if self.chronic_inv == False and self.current_case_status.lower() != "probable":
                                                                self.issues.append('incorrect case classification, should be chronic probable.')
            else:
                if any(item in self.text3 for item in self.data) and any(x in self.result_check_igm.lower() for x in self.positive_results):# igm positive
                    if previous_investigation_acute.lower() in ["confirmed", "probable"] or previous_investigation_chronic.lower() in ["confirmed", "probable"]:
                        if self.current_case_status.lower() != "not a case":
                            self.issues.append('incorrect case classification, should be not a case.')
                        elif self.current_case_status.lower() == "not a case":
                            self.issues = []
                            pass
                    else:
                        if self.was_patient_jaundiced.lower() == 'yes' or (self.alt_sgpt_result and int(self.alt_sgpt_result) >200) or (self.total_bilirubin_result and self.total_bilirubin_result.replace('.','',1).isdigit()and float(self.total_bilirubin_result)>3.0):
                            if not self.symptoms_likely_diagnosis or self.symptoms_likely_diagnosis.lower() == "yes":
                                if self.current_case_status.lower() != "not a case":
                                    self.issues.append('incorrect case classification, should be not a case.')
                                elif self.current_case_status.lower() == "not a case":
                                    self.issues = []
                                    pass
                            else:
                                if self.acute_inv == False and self.current_case_status.lower() != "probable":
                                    self.issues.append('incorrect case classification, should be acute probable.')
                        else:
                            if self.current_case_status.lower() != "not a case":
                                    self.issues.append('incorrect case classification, should be not a case.')
                            elif self.current_case_status.lower() == "not a case":
                                self.issues = []
                                pass
                else:
                    if self.current_case_status.lower() != "not a case":
                        self.issues.append('incorrect case classification, should be not a case.')
                    elif self.current_case_status.lower() == "not a case":
                        self.issues = []
                        pass
        else:
            if self.current_case_status.lower() != "not a case":
                self.issues.append('incorrect case classification, should be not a case. Investigate as Perinatal Hepatitis B.')
            elif self.current_case_status.lower() == "not a case":
                self.issues = []
                pass
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
    
    def SendHepBnotificationreviewEmail(self, body, inv_id):
        message = EmailMessage()
        message.set_content(body)
        message['Subject'] = f'HepBnotificationreviewBot {inv_id}'
        message['From'] = self.nbsbot_email
        message['To'] = ', '.join(["disease.reporting@maine.gov"])
        smtpObj = smtplib.SMTP(self.smtp_server)
        smtpObj.send_message(message)
        print('sent email', inv_id)