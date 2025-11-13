from Base import NBSdriver
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, date
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from selenium import webdriver
driver=webdriver.Chrome()

class Athena(NBSdriver):
    """ A class to review COVID-19 cases in the notification queue.
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
        # Check Patient Tab
        self.CheckFirstName()
        self.CheckLastName()
        self.CheckDOB()
        self.CheckCurrentSex()
        self.CheckStAddr()
        self.CheckCity()
        self.CheckState()
        self.CheckZip()
        self.CheckCounty()
        self.CheckCountry()
        self.CheckInvestigator()
        self.CheckEthnicity()
        self.CheckRace()

        # Read Associated labs
        self.ReadAssociatedLabs()
        self.AssignLabTypes()
        self.DetermineCaseStatus()
        self.GetCollectionDate()
        self.GetReportDate()

        # # Check Case Info Tab
        self.GoToCaseInfo()
        self.CheckJurisdiction()
        self.CheckProgramArea()
        self.CheckInvestigationStartDate()
        self.CheckInvestigationStatus()
        self.CheckSharedIndicator()
        self.CheckStateCaseID()
        self.CheckLostToFollowUp()
        self.CheckReportDate()
        self.CheckInvestigatorAssignDate()
        self.CheckCountyStateReportDate()
        self.CheckReportingSourceType()
        self.CheckReportingOrganization()
        self.CheckPreformingLaboratory()
        self.CheckCollectionDate()
        self.CheckCurrentStatus()
        self.CheckProbableReason()

        self.CheckHospitalizationIndicator()
        if self.hospitalization_indicator == 'Yes':
            self.CheckHospitalName()
            self.CheckAdmissionDate()
            self.CheckDischargeDate()

        self.CheckIcuIndicator()
        if self.icu_indicator == 'Yes':
            self.CheckIcuAdmissionDate()
            if type(self.icu_admission_date) is date:
                self.CheckIcuDischargeDate()

        self.CheckDieFromIllness()
        if self.death_indicator == 'Yes':
            self.CheckDeathDate()

        self.CheckCongregateSetting()
        if self.cong_setting_indicator == 'Yes':
            self.CheckCongregateFacilityName()

        self.CheckFirstResponder()
        if self.first_responder == 'Yes':
            self.CheckFirstResponderOrg()

        self.CheckHealthcareWorker()
        if self.healthcare_worker == 'Yes':
            self.CheckHealtcareWorkerFacility()
            self.CheckHealthcareWorkerJob()
            if self.healthcare_worker_job == 'Other':
                self.CheckHealthcareWorkerJobOther()
            self.CheckHealthcareWorkerSetting()
            if self.healthcare_worker_setting == 'Other':
                self.CheckHealthcareWorkerSettingOther()

        self.CheckConfirmationDate()
        self.CheckCaseStatus()
        self.CheckMmwrWeek()
        self.CheckMmwrYear()
        self.CheckClosedDate()

#################### Housing Check Methods ###################################
    def CheckCongregateSetting(self):
        """ Check if a patient lives in congregate setting."""
        if self.site == 'https://nbstest.state.me.us/':
            xpath = '//*[@id="95421_4"]'
        else:
            xpath = '//*[@id="ME3130"]'
        self.cong_setting_indicator = self.ReadText(xpath)
        if self.investigator:
            if (self.investigator_name in self.outbreak_investigators) & (self.cong_setting_indicator not in ['Yes', 'No']):
                self.issues.append('Congregate setting question must be answered with "Yes" or "No".')
            elif (self.ltf != 'Yes') & (not self.cong_setting_indicator):
                self.issues.append('Congregate setting status must have a value.')

    def CheckCongregateFacilityName(self):
        """ Need a congregate faciltiy name if patient lives in congregate setting."""
        if self.investigator_name:
            cong_fac_name = self.CheckForValue('//*[@id="ME134008"]','Name of congregate facility is missing.')

#################### First Responder Check Methods #############################
    def CheckFirstResponder(self):
        """ Check if a patient is a first responder."""
        self.first_responder =  self.ReadText('//*[@id="ME59100"]')
        if (self.investigator) & (self.investigator_name not in self.outbreak_investigators) & (self.ltf != 'Yes') & (not self.first_responder):
            self.issues.append('First responder question must be answered.')

    def CheckFirstResponderOrg(self):
        """ Check first responder organization."""
        if self.investigator_name:
            first_responder_org = self.CheckForValue('//*[@id="ME59116"]','First responder organization is blank.')

#################### Healthcare Worker Check Methods ###########################
    def CheckHealthcareWorker(self):
        """ Check if patient is a healthcare worker."""
        self.healthcare_worker = self.ReadText('//*[@id="NBS540"]')
        if self.investigator:
            if (self.investigator_name in self.outbreak_investigators) & (self.healthcare_worker not in ['Yes', 'No']):
                self.issues.append('Healthcare worker questions must be answered with "Yes" or "No".')
            elif (self.ltf != 'Yes') & (not self.healthcare_worker):
                self.issues.append('Healthcare worker question is blank.')

    def CheckHealtcareWorkerFacility(self):
        """ If the patient is a healthcare worker then a facility name must be provided."""
        if (self.ltf != 'Yes') & (self.investigator):
            healthcare_worker_fac =  self.CheckForValue('//*[@id="ME10103"]','Healthcare worker facility is blank.')

    def CheckHealthcareWorkerJob(self):
        """ If the patient is a healthcare worker then an occupation name must be provided."""
        xpath = '//*[@id="14679004"]'
        if (self.ltf != 'Yes') & (self.investigator):
            self.healthcare_worker_job =  self.CheckForValue(xpath,'Healthcare worker occupation is blank.')
        else:
            self.healthcare_worker_job = self.ReadText(xpath)

    def CheckHealthcareWorkerJobOther(self):
        """ If the patient is a healthcare worker and occupation is other then name must be provided."""
        if (self.ltf != 'Yes') & (self.investigator):
            healthcare_worker_job_other =  self.CheckForValue('//*[@id="14679004Oth"]','Healthcare worker other occupation is missing.')

    def CheckHealthcareWorkerSetting(self):
        """ If the patient is a healthcare worker then healthcare setting name must be provided."""
        xpath = '//*[@id="NBS683"]'
        if (self.ltf != 'Yes') & (self.investigator):
            self.healthcare_worker_setting =  self.CheckForValue(xpath, 'Healthcare worker setting is blank.')
        else:
            self.healthcare_worker_setting =  self.ReadText(xpath)

    def CheckHealthcareWorkerSettingOther(self):
        """ If the patient is a healthcare worker and setting is other then name must be provided."""
        healthcare_worker_setting_other =  self.CheckForValue('//*[@id="NBS683Oth"]','Healthcare worker other setting is missing.')

###################### COVID-19 Case Details Check Methods #####################
    def CheckCurrentStatus(self):
        """ Check if current status in the investigation is consistent with the
        associated labs. """
        self.current_status = self.ReadText('//*[@id="NBS548"]')
        if (self.current_status == 'Probable Case') & (self.status != 'P'):
            self.issues.append('Current status mismatch.')
        elif (self.current_status == 'Laboratory-confirmed case') & (self.status != 'C'):
            self.issues.append('Current status mismatch.')
        elif not self.current_status:
            self.issues.append('Current status is blank.')

    def CheckProbableReason(self):
        """ Check if probable reason is consistent with current status and case
        status. """
        probable_reason = self.ReadText('//*[@id="NBS678"]')
        probable_reason = probable_reason.replace('\n','')
        if (probable_reason == 'Meets Presump Lab and Clinical or Epi') & ((self.status != 'P') | (self.current_status != 'Probable Case')):
            self.issues.append('Status inconsistency.')
        elif probable_reason in ['Meets Clinical/Epi, No Lab Conf', 'Meets Vital Records, No Lab Confirm']:
            self.issues.append('Probable reason does not include a lab. Human review required.')
        elif (not probable_reason) & (self.status not in ['C', 'S']):
            self.issues.append('Probable reason is blank and correct status is not confirmed or suspect.')

###################### Exposure Information Check Methods ######################
    def CheckExposureSection(self):
        """ Make sure that exposure section contains at least one 'Yes' and if
        more than one that "Unknown exposure" is not included."""
        html = self.find_element(By.XPATH, '//*[@id="NBS_UI_GA21014"]/tbody').get_attribute('innerHTML')
        soup = BeautifulSoup(html, 'html.parser')
        num_exposures = str(soup).count('Yes')
        unknown_exposure = self.ReadText('//*[@id="NBS667"]')
        if num_exposures == 0:
            self.issues.append('Exposure section is not complete.')
        elif (unknown_exposure == 'Yes') & (num_exposures > 1):
            self.issues.append('If unknown exposure is selected then no other exposures should be indicated.')

    def CheckDomesticTravel(self):
        """ If domestic travel is indicated states involved must be specified."""
        parent_xpath = '//*[@id="INV664"]'
        child_xpath = '//*[@id="82754_3"]'
        message = "State(s) must be specified when domestic travel is 'Yes'."
        self.CheckIfField(parent_xpath, child_xpath, 'Yes', message)

    def CheckShipTravel(self):
        """ If travel by boat is indicated vessel name must be specified."""
        parent_xpath = '//*[@id="473085002"]'
        child_xpath = '//*[@id="NBS690"]'
        message = "When travel by boat is indicated vessel name must be specified."
        self.CheckIfField(parent_xpath, child_xpath, 'Yes', message)

    def CheckSchoolExposure(self):
        """ If school exposure is indicated ensure that facility name is
        provided."""
        if self.site == 'https://nbs.iphis.maine.gov/':
            school_exposure = self.ReadText('//*[@id="257698009"]')
            if school_exposure == 'Yes':
                school_name = self.ReadText('//*[@id="ME62100"]')
                university_name = self.ReadText('//*[@id="ME62101"]')
                if (not school_name) & (not university_name):
                    self.issues.append("If school/university exposure is indicated then school/university name must be specified.")
                if school_name == 'Other':
                    other_school_name = self.ReadText('//*[@id="ME62100Oth"]')
                    if not other_school_name:
                        self.issues.append('Other school name is blank.')
                if university_name == 'Other':
                    other_university_name = self.ReadText('//*[@id="ME62101Oth"]')
                    if not other_university_name:
                        self.issues.append('Other university name is blank.')

    def CheckDaycareExposure(self):
        """ If daycare exposure is indicated ensure that facility name is
        provided."""
        if self.site == 'https://nbs.iphis.maine.gov/':
            daycare_exposure = self.ReadText('//*[@id="413817003"]')
            if daycare_exposure == 'Yes':
                daycare_name = self.ReadText('//*[@id="ME10106"]')
                if (not daycare_name):
                    self.issues.append("If daycare exposure is indicated then daycare name must be specified.")


    def CheckOutbreakExposure(self):
        """ If outbreak exposure is indicated then outbreak name must be provided.
        If the case is assigned to outbreak investigator outbreak exposure section must be complete."""
        outbreak_exposure_path = '//*[@id="INV150"]'
        outbreak_name_path = '//*[@id="ME125032"]'
        check_condition = 'Yes'
        message = "Outbreak name must be provided if outbreak exposure is indicated."

        if self.investigator_name in self.outbreak_investigators:
            ob_exposure = self.ReadText(outbreak_exposure_path)
            if ob_exposure != 'Yes':
                self.issues.append('Outbreak exposure must be "Yes" and outbreak name must be specified.')
            else:
                self.CheckForValue(outbreak_name_path, 'Outbreak name in exposure section is blank.')
        else:
            self.CheckIfField(outbreak_exposure_path, outbreak_name_path, check_condition, message)


######################### Case Status Check Methods ############################
    def CheckTransmissionMode(self):
        """ Transmission mode should blank or airborne"""
        transmission_method =  self.ReadText('//*[@id="INV157"]')
        if transmission_method not in ['', 'Airborne']:
            self.issues.append('Transmission mode should be blank or airborne.')

    def CheckCaseStatus(self):
        """ Case status must be consistent with associated labs. """
        current_case_status = self.ReadText('//*[@id="INV163"]')
        status_pairs = {'Confirmed':'C', 'Probable':'P', 'Suspect':'S', 'Not a Case':'N'}
        if current_case_status == 'Not a Case':
            self.issues.insert(0,'**NOT A CASE: CENTRAL EPI REVIEW REQUIRED - NO FURTHER INVESTIGATOR ACTION REQUIRED**')
            id = self.ReadPatientID()
            if id not in self.not_a_case_log:
                self.not_a_case_log.append(self.ReadPatientID())
        elif not current_case_status:
            self.issues.append('Case status is blank.')
        elif status_pairs[current_case_status] != self.status:
            self.issues.append('Case status mismatch.')

    def CheckLostToFollowUp(self):
        """ Check if case is lost to follow up. """
        self.ltf = self.ReadText('//*[@id="ME64100"]')
        self.ltf = self.ltf.replace('\n', '')
        if self.ltf == 'Unknown':
            self.issues.append('Lost to follow up inidicator cannot be unknown.')
        elif (not self.ltf) & self.investigator:
            self.issues.append('Lost to follow up cannot be blank.')

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
    '''def CheckHospitalizationIndicator(self):
        """ Read hospitalization status. If an investigation was conducted it must be Yes or No """
        self.hospitalization_indicator = self.ReadText('//*[@id="INV128"]')
        if (self.ltf != 'Yes') & (self.investigator):
            if self.hospitalization_indicator not in ['Yes', 'No']:
                self.issues.append("Patient hospitalized must be 'Yes' or 'No'.")

    def CheckHospitalName(self):
        """" If the case is hospitalized then a hospital name must be provided. """
        hospital_name = self.ReadText('//*[@id="INV184"]')
        if not hospital_name:
            self.issues.append('Hospital name missing.')
    
    def CheckIcuIndicator(self):
        """ If case is hospitalized then we should know if they were ever in the ICU."""
        self.icu_indicator = self.ReadText('//*[@id="309904001"]')
        if (self.ltf != 'Yes') & (self.hospitalization_indicator == 'Yes') & (self.investigator):
            if not self.icu_indicator:
                self.issues.append('ICU indicator is blank.')

    def CheckIcuAdmissionDate(self):
        """ Check for ICU admission date."""
        self.icu_admission_date = self.ReadDate('//*[@id="NBS679"]')
        if not self.icu_admission_date:
            self.issues.append('ICU admission date is missing.')
        elif self.icu_admission_date > self.now:
            self.issues.append('ICU admission date cannot be in the future.')

    def CheckIcuDischargeDate(self):
        """ Check for ICU discharge date. """
        icu_discharge_date = self.ReadDate('//*[@id="NBS680"]')
        if not icu_discharge_date:
            self.issues.append('ICU discharge date is missing.')
        elif icu_discharge_date < self.icu_admission_date:
            self.issues.append('ICU discharge date must be after admission date.')
        elif icu_discharge_date > self.now:
            self.issues.append('ICU discharge date cannot be in the future.')

    def CheckDieFromIllness(self):
        """ Died from illness should be yes or no. """
        self.death_indicator =  self.CheckForValue('//*[@id="INV145"]','Died from illness must be yes or no.')

    def CheckDeathDate(self):
        """ Death date must be present."""
        death_date = self.ReadDate('//*[@id="INV146"]')
        if not death_date:
            self.issues.append('Date of death is blank.')
        elif death_date > self.now:
            self.issues.append('Date of death date cannot be in the future')'''

################### Investigation Details Check Methods ########################
    '''def CheckJurisdiction(self):
        """ Jurisdiction and county must match. """
        jurisdiction = self.CheckForValue('//*[@id="INV107"]','Jurisdiction is blank.')
        if jurisdiction not in self.county:
            self.issues.append('County and jurisdiction mismatch.')

    def CheckProgramArea(self):
        """ Program area must be Airborne. """
        program_area = self.CheckForValue('//*[@id="INV108"]','Program Area is blank.')
        if program_area != 'Airborne and Direct Contact Diseases':
            self.issues.append('Program Area is not "Airborne and Direct Contact Diseases".')

    def CheckInvestigationStartDate(self):
        """ Verify investigation start date is on or after report date. """
        self.investigation_start_date = self.ReadDate('//*[@id="INV147"]')
        if not self.investigation_start_date:
            self.issues.append('Investigation start date is blank.')
        elif self.investigation_start_date < self.report_date:
            self.issues.append('Investigation start date must be on or after report date.')
        elif self.investigation_start_date > self.now:
            self.issues.append('Investigation start date cannot be in the future.')'''

    # def CheckInvestigationStatus(self):
    #     """ Only accept closed investigations for review. """
    #     inv_status = self.ReadText('//*[@id="INV109"]')
    #     if not inv_status:
    #         self.issues.append('Investigation status is blank.')
    #     elif inv_status == 'Open':
    #         self.issues.append('Investigation status is open.')

    def CheckSharedIndicator(self):
        """ Ensure shared indicator is yes. """
        shared_indicator = self.ReadText('//*[@id="NBS_UI_19"]/tbody/tr[5]/td[2]')
        if shared_indicator != 'Yes':
            self.issues.append('Shared indicator not selected.')

    def CheckStateCaseID(self):
        """ State Case ID must be provided. """
        case_id = self.ReadText('//*[@id="INV173"]')
        if not case_id:
            self.issues.append('State Case ID is blank.')


########################### Parse and process labs ############################
    def ReadAssociatedLabs(self):
        """ Read table of associated labs."""
        self.labs = self.ReadTableToDF('//*[@id="viewSupplementalInformation1"]/tbody')
        if self.labs['Date Received'][0] == 'Nothing found to display.':
            self.issues.append('No labs associated with investigation.')

    def AssignLabTypes(self):
        """ Determine lab type (PCR, Ag, or Ab) for each associated lab."""
        pcr_flags = ['RNA', 'PCR', 'NAA', 'GENE', 'PRL SCV2', 'CEPHID', 'NAAT', 'CARY MEDICAL CENTER']
        ag_flags = ['AG', 'ANTIGEN', 'VERITOR']
        ab_flags = ['AB', 'IGG', 'IGM', 'IGA', 'Antibod', 'T-DETECT']
        test_types = [('pcr', pcr_flags), ('antigen', ag_flags), ('antibody', ab_flags)]
        for type in test_types:
            self.labs[type[0]] = self.labs['Test Results'].apply(lambda results: any(flag in results.upper() for flag in type[1]))

    def DetermineCaseStatus(self):
        """Review lab types to determine case status.
        PCR => confirmed
        Antigen => probable
        Antibody => suspect
        """
        if any(self.labs.pcr):
            self.status = 'C'
        elif any(self.labs.antigen):
            self.status = 'P'
        elif any(self.labs.antibody):
            self.status = 'S'
        else:
            self.status = ''
            self.issues.insert(0,'**UNABLE TO DETERMINE CORRECT STATUS: CENTRAL EPI REVIEW REQUIRED**')
            id = self.ReadPatientID()
            if id not in self.lab_data_issues_log:
                self.lab_data_issues_log.append(self.ReadPatientID())

    def GetReportDate(self):
        """Find earliest report date by reviewing associated labs"""
        if self.labs['Date Received'][0] == 'Nothing found to display.':
            self.report_date = datetime(1900, 1, 1).date()
        else:
            self.labs['Date Received'] = pd.to_datetime(self.labs['Date Received'], format = '%m/%d/%Y%I:%M %p').dt.date
            self.report_date = self.labs['Date Received'].min()

    def GetCollectionDate(self):
        """Find earliest collection date by reviewing associated labs"""
        if self.labs['Date Received'][0] == 'Nothing found to display.':
            self.collection_date = datetime(1900, 1, 1).date()
        else:
            # Check for any associated labs missing collection date:
            # 1. Set collection date to 01/01/2100 to avoid type errors.
            # 2. Log patient id for manual review.
            no_col_dt_labs = self.labs.loc[self.labs['Date Collected'] == 'No Date']
            if len(no_col_dt_labs) > 0:
                self.labs.loc[self.labs['Date Collected'] == 'No Date', 'Date Collected'] = '01/01/2100'
                self.issues.insert(0,'**SOME ASSOCIATED LABS MISSING COLLECTION DATE: CENTRAL EPI REVIEW REQUIRED**')
                self.lab_data_issues_log.append(self.ReadPatientID())
            self.labs['Date Collected'] = pd.to_datetime(self.labs['Date Collected'], format = '%m/%d/%Y').dt.date
            self.collection_date = self.labs['Date Collected'].min()

    def ReadAoes(self):
        """ Read AOEs from associated labs. """
        aoe_flags = {'icu_aoe':'Admitted to ICU for condition:\xa0Y'
                    ,'hcw_aoe':'Hospitalized for condition of interest:\xa0Y'
                    ,'symp_aoe':'Has symptoms for condition:\xa0Y'
                    ,'hosp_aoe':'Hospitalized for condition of interest:\xa0Y'
                    ,'cong_aoe':'Resides in a congregate care setting:\xa0Y'
                    ,'fr_aoe':'First Responder:\xa0Y'
                    ,'preg_aoe': 'Pregnancy Status:\xa0Y'}
        for aoe in aoe_flags.keys():
            self.labs[aoe] = self.labs.apply(lambda row: aoe_flags[aoe] in row['Test Results'], axis=1 )
        self.icu_aoe =  any(self.labs.icu_aoe)
        self.hcw_aoe =  any(self.labs.hcw_aoe)
        self.symp_aoe =  any(self.labs.symp_aoe)
        self.hosp_aoe =  any(self.labs.hosp_aoe)
        self.cong_aoe =  any(self.labs.cong_aoe)
        self.fr_aoe = any(self.labs.fr_aoe)
        self.preg_aoe = any(self.labs.preg_aoe)

######################## Administrative Questions Check Methods ###############
    def CheckFirstAttemptDate(self):
        """ Verify that first attempt to contact date is provided and greater
        than or equal to investigation start date. """
        first_attempt_date = self.ReadDate('//*[@id="ME64102"]')
        if not ((self.ltf == 'Yes') & (self.cong_setting_indicator == 'Yes')):
            if not first_attempt_date:
                self.issues.append('First attempt to contact date is blank.')
            elif first_attempt_date < self.investigation_start_date:
                self.issues.append('First attempt to contact must be on or after investigation start date.')
            elif first_attempt_date > self.now:
                self.issues.append('First attempt to contact date cannot be in the future.')


########################### AOE Check Methods ##################################
    def CheckHospAOE(self):
        """ Ensure that if AOEs show a patient as hosptialized the investigation matches."""
        if self.hosp_aoe & (self.hospitalization_indicator != 'Yes'):
            self.issues.append('AOEs indicate that the case is hospitalized, but the investigation does not.')

    def CheckIcuAOE(self):
        """ Ensure that if AOEs show a patient as in the ICU the investigation matches."""
        if self.hospitalization_indicator == 'Yes':
            if self.icu_aoe & (self.icu_indicator != 'Yes'):
                self.issues.append('AOEs indicate that the case is in the ICU, but the investigation does not.')

    def CheckHcwAOE(self):
        """ Ensure that if AOEs show a patient is a healthcare worker the investigation matches."""
        if self.hcw_aoe & (self.healthcare_worker != 'Yes'):
            self.issues.append('AOEs indicate that the case is a healthcare worker, but the investigation does not.')

    def CheckSympAOE(self):
        """ Ensure that if AOEs show a patient is symptomatic the investigation matches."""
        if self.symp_aoe & (self.symptoms != 'Yes'):
            self.issues.append('AOEs indicate that the case is symptomatic, but the investigation does not.')

    def CheckCongAOE(self):
        """ Ensure that if AOEs show a patient lives in a congregate setting the
        investigation matches."""
        if self.symp_aoe & (self.cong_setting_indicator != 'Yes'):
            self.issues.append('AOEs indicate that the case lives in a congregate setting, but the investigation does not.')

    def CheckFirstResponderAOE(self):
        """ Ensure that if AOEs show a patient is a first responder that the
        investigation matches."""
        if self.fr_aoe & (self.first_responder != 'Yes'):
            self.issues.append('AOEs indicate that the case is a first responder, but the investigation does not.')

    def CheckPregnancyAOE(self):
        """ Ensure that if AOEs show a patient is pregnany that the
        investigation matches."""
        pregnant_status = self.ReadText('//*[@id="INV178"]')
        if self.preg_aoe & (pregnant_status != 'Yes'):
            self.issues.append('AOEs indicate that the case is pregnant, but the investigation does not.')

############### Preforming Lab Check Methods ##################################
    # def CheckPreformingLaboratory(self):
    #     """ Ensure that preforming laboratory is not empty. """
    #     reporting_organization = self.ReadText('//*[@id="ME6105"]')
    #     if not reporting_organization:
    #         self.issues.append('Performing laboratory is blank.')

    def CheckCollectionDate(self):
        """ Check if collection date is present and matches earliest date from
        associated labs. """
        current_collection_date = self.ReadDate('//*[@id="NBS550"]')
        if not current_collection_date:
            self.issues.append('Collection date is missing.')
        elif current_collection_date != self.collection_date:
            self.issues.append('Collection date mismatch.')
        elif current_collection_date > self.investigation_start_date:
            self.issues.append('Collection date cannot be after investigation start date.')


############ Ethnicity and Race Information Check Methods #####################
    def CheckNonWhiteEthnicity(self):
        """Ensure that all ehthnicaly non-white cases are assigned for investigation."""
        if (not self.investigator) & (self.ethnicity == 'Hispanic or Latino'):
            self.issues.append('Case is Hispanic or Latinx and should be assigned for investigation.')

    def CheckRace(self):
        """ Must provide race and selection must make sense. """
        self.race = self.CheckForValue('//*[@id="patientRacesViewContainer"]','Race is blank.')
        # Race should only be unknown if no other options are selected.
        ambiguous_answers = ['Unknown', 'Other', 'Refused to answer', 'Not Asked']
        for answer in ambiguous_answers:
            if (answer in self.race) and (self.race != answer) and (self.race == 'Native Hawaiian or Other Pacific Islander'):
                self.issues.append('"'+ answer + '"' + ' selected in addition to other options for race.')

    def CheckNonWhiteRace(self):
        """Ensure that all racially non-white cases are assigned for investigation."""
        if not self.investigator:
            non_white_races = ['Black or African American', 'Asian', 'American Indian or Alaska Native', 'Native Hawaiian or Other Pacific Islander']
            if any(non_white_race in self.race for non_white_race in non_white_races):
                self.issues.append('Race is non-white, case should be assigned for investigation.')

    ###################### Other Personal Details Check Methods ####################
    '''def CheckDOB(self):
        """ Must provide DOB. """
        self.dob = self.ReadDate('//*[@id="DEM115"]')
        if not self.dob:
            self.issues.append('DOB is blank.')
            print(f"dob: {self.dob}")
        elif self.dob > self.now:
            self.issues.append('DOB cannot be in the future.')
            print(f"dob: {self.dob}")

    def CheckCurrentSex(self):
        """ Ensure patient current sex is not blank. """
        patient_sex = self.CheckForValue('//*[@id="DEM113"]','Current Sex is blank.')'''

#################### Reporting Address Check Methods ###########################
    '''def CheckStAddr(self):
        """ Must provide street address. """
        street_address = self.CheckForValue( '//*[@id="DEM159"]', 'Street address is blank.')'''

    # def CheckCity(self):
    #     """ Must provide city. """
    #     city = self.CheckForValue( '//*[@id="DEM161"]', 'City is blank.')

    # def CheckState(self):
    #     """ Must provide state and if it is not Maine case should be not a case. """
    #     state = self.CheckForValue( '//*[@id="DEM162"]', 'State is blank.')
    #     if state != 'Maine':
    #         self.issues.append('State is not Maine.')
    #         print(f"state: {state}")

    ####################### Investigator Check Methods ############################
    '''def CheckInvestigator(self):
        """ Check if an investigator was assigned to the case. """
        investigator = self.ReadText('//*[@id="INV180"]')
        self.investigator_name = investigator
        if investigator:
            self.investigator = True
        else:
            self.investigator = False

    def CheckInvestigatorAssignDate(self):
        """ If an investigator was assinged then there should be an investigator
        assigned date. """
        if self.investigator:
            assigned_date = self.ReadText('//*[@id="INV110"]')
            if not assigned_date:
                self.issues.append('Missing investigator assigned date.')
                print(f"investigator_assigned_date: {assigned_date}")'''

    def ExposureChecks(self):
        """ A method to conduct all checks required to review the exposure section. """
        self.CheckExposureSection()
        self.CheckDomesticTravel()
        self.CheckShipTravel()
        self.CheckSchoolExposure()
        self.CheckDaycareExposure()
        self.CheckOutbreakExposure()
        self.CheckTransmissionMode()
        self.CheckDetectionMethod()

    def AOEChecks(self):
        """ A method to read and check all AOEs."""
        self.ReadAoes()
        self.CheckHospAOE()
        self.CheckIcuAOE()
        self.CheckHcwAOE()
        self.CheckSympAOE()
        self.CheckCongAOE()
        self.CheckFirstResponderAOE()
        self.CheckPregnancyAOE()

    def CaseInvestigatorReview(self):
        """ Conduct the case review required when an investigation is assigned to a case investigator. """
        self.CheckFirstAttemptDate()

        if self.ltf != 'Yes':
            #self.CheckNumCloseContacts()
            self.ExposureChecks()
        # Check COVID Tab.
        self.GoToCOVID()
        self.CheckSymptoms()
        if (self.symptoms == 'Yes') & (self.ltf != 'Yes'):
            self.CheckSymptomDatesAndStatus()
        self.CheckIllness_Duration()
        #self.CheckIsolation()
        if self.ltf != 'Yes':
            self.CheckPreExistingConditions()
        self.CheckImmPactQuery()
        self.CheckRecievedVax()
        if self.vax_recieved == 'Yes':
            self.CheckFullyVaccinated()
        self.CheckTestingPerformed()
        if self.testing_performed == 'Yes':
            self.CheckLabTable()
        # Check AOEs
        if self.ltf == 'Yes':
            self.AOEChecks()

    def OutbreakInvestigatorReview(self):
        """A method to perfrom check specific to investigations assigned to outbreak investigators. """
        self.ExposureChecks()
        # Check COVID Tab.
        self.GoToCOVID()
        self.CheckSymptoms()
        if self.symptoms == 'Yes':
            self.CheckSymptomDatesAndStatus()
        #self.CheckIsolation()
        self.CheckImmPactQuery()
        self.CheckRecievedVax()
        if self.vax_recieved == 'Yes':
            self.CheckFullyVaccinated()
        self.CheckTestingPerformed()
        if self.testing_performed == 'Yes':
            self.CheckLabTable()
        self.AOEChecks()

    def TriageReview(self):
        """A method to perfrom check specific to investigations open and closed without an investigator. """
        # Check COVID Tab.
        self.GoToCOVID()
        self.CheckSymptoms()
        self.CheckImmPactQuery()
        self.CheckRecievedVax()
        if self.vax_recieved == 'Yes':
            self.CheckFullyVaccinated()
        self.CheckTestingPerformed()
        # Check AOEs
        self.AOEChecks()

    def ReviewCase(self):
        """ Conduct review of a case in the notification queue. """
        self.SortApprovalQueue()
        self.CheckFirstCase()
        self.initial_name = self.patient_name
        if self.condition == '2019 Novel Coronavirus (2019-nCoV)':
            self.GoToFirstCaseInApprovalQueue()
            self.StandardChecks()
            if not self.investigator:
                self.TriageReview()
            elif self.investigator_name in self.outbreak_investigators:
                self.OutbreakInvestigatorReview()
            else:
                self.CaseInvestigatorReview()

            if not self.issues:
                self.ApproveNotification()
            self.ReturnApprovalQueue()
            self.SortApprovalQueue()
            self.CheckFirstCase()
            self.final_name = self.patient_name
            if (self.final_name == self.initial_name) & (len(self.issues) > 0):
                self.RejectNotification()
            elif (self.final_name != self.initial_name) & (len(self.issues) > 0):
                print('Case at top of queue changed. No action was taken on the reviewed case.')
                self.num_fail += 1
        else:
            print("No COVID-19 cases in notification queue.")
########### Vaccination Interperative Information Check Methods ################
    def CheckImmPactQuery(self):
        """ Ensure ImmPact was queried when age eligible. """
        self.immpact = self.ReadText('//*[@id="ME71100"]')
        try:
            age = int((self.collection_date - self.dob).days//365.25)
            if (self.immpact != 'Yes') & (age >= 5):
                self.issues.append('ImmPact has not been queried.')
        except TypeError:
            self.issues.append('Unable to compute age because of bad/missing collection date or DOB -> ImmPact check applied regardless of age.')
            if self.immpact != 'Yes':
                self.issues.append('ImmPact has not been queried.')

    def CheckRecievedVax(self):
        """ Ever recieved vaccine should only be no when case not LTFU. """
        self.vax_recieved = self.ReadText('//*[@id="VAC126"]')
        if (self.vax_recieved == 'No') & (self.ltf != 'No'):
            self.issues.append("If LTF == 'Yes' or blank, Vaccine Received must be blank or 'Yes'.")
        elif (self.ltf == 'No') & (not self.vax_recieved):
            self.issues.append('If the case is not lost to follow up then vaccine recieved must be answered.')
        elif self.vax_recieved == 'Yes':
            dose_number = self.ReadText('//*[@id="VAC140"]')
            if not dose_number:
                self.issues.append('Doses prior to onset cannot be blank if Vacinated is "Yes".')
            last_dose_date = self.ReadDate('//*[@id="VAC142"]')
            first_vax_date = datetime(2020, 12, 15).date()
            if (not last_dose_date) & (dose_number != '0'):
                self.issues.append('Last dose date is blank.')
            # elif (last_dose_date != None) & (last_dose_date < first_vax_date):
               # self.issues.append('Last dose date is prior to when vaccinations become available.')
            #elif (last_dose_date != None) & last_dose_date > self.now:
               # self.issues.append('Last dose date cannot be in the future.')

    def CheckFullyVaccinated(self):
        """ Validate fully vaccinated question"""
        fully_vaccinated = self.ReadText('//*[@id="ME70100"]')
        if (fully_vaccinated not in ['Yes', 'No']) & (self.ltf == 'No'):
            self.issues.append("Fully vaccinated cannot be blank or unknown when case is not lost to followup.")
        if (fully_vaccinated == 'Yes') & (self.vax_recieved == 'No'):
            self.issues.append("Fully vaccinated cannot be Yes is vaccine recieved is No.")

########################## COVID Testing Check Methods #########################
    def CheckTestingPerformed(self):
        """Ensure testing performed is Yes or No."""
        self.testing_performed = self.ReadText('//*[@id="INV740"]')
        if self.testing_performed not in ['Yes', 'No']:
            self.issues.append("Laboratory testing performed cannot be blank or unknown.")

    def CheckLabTable(self):
        """ Ensure that labs listed in investigation support case status. """
        inv_labs = self.ReadTableToDF('//*[@id="NBS_UI_GA21011"]/tbody/tr[1]/td/table')
        if len(inv_labs) == 0:
            self.issues.append('No labs listed in investigation.')
        if len(inv_labs.loc[inv_labs['Test Result'] != 'Positive']) > 0:
            self.issues.append('All labs list in investigation must be positive.')
        status_lab_pairs = {'C':'PCR', 'P':'Ag', 'S':'Ab'}
        if self.status in status_lab_pairs.keys():
            if len(inv_labs.loc[inv_labs['Test Type'].str.contains(status_lab_pairs[self.status])]) == 0:
                self.issues.append('Lab(s) listed in investigation do not support correct case status.')

######################### Symptom Check Methods ################################
    def CheckSymptoms(self):
        """" Check symptom status of case. """
        self.symptoms = self.ReadText('//*[@id="INV576"]')
        if (self.ltf != 'Yes') & (self.investigator):
            if not self.symptoms:
                self.issues.append("Symptom status is blank.")

    def CheckSymptomDatesAndStatus(self):
        """ Ensure date of symptom onset, resolution, and current symptom status
        are consistent."""
        symp_onset_date = self.ReadDate('//*[@id="INV137"]')
        symp_resolution_date = self.ReadDate('//*[@id="INV138"]')
        symp_status = self.ReadText('//*[@id="NBS555"]')

        if not symp_status:
            self.issues.append('Symptom status is blank.')
        elif symp_status == 'Still symptomatic':
            if not symp_onset_date:
                self.issues.append('Symptom onset date is blank.')
            elif symp_onset_date > self.now:
                self.issues.append('Symptom onset date cannot be in the future.')
            if symp_resolution_date:
                self.issues.append('Symptom resolution date should be blank if still symptomatic.')
        elif symp_status == 'Symptoms resolved':
            if not symp_onset_date:
                self.issues.append('Symptom onset date is blank.')
            elif symp_onset_date > self.now:
                self.issues.append('Symptom onset date cannot be in the future.')
            if not symp_resolution_date:
                self.issues.append('Symptom resolution date is blank. If date unknown choose "Symptoms resolved, unknown date" for symptom status.')
            elif symp_onset_date:
                if symp_resolution_date < symp_onset_date:
                    self.issues.append('Symptom resolution date cannot be prior to symptom onset date.')
            elif symp_resolution_date > self.now:
                self.issues.append('Symptom resolution date cannot be in the future.')
        elif symp_status == 'Symptoms resolved, unknown date':
            if not symp_onset_date:
                self.issues.append('Symptom onset date is blank.')
            if symp_resolution_date:
                self.issues.append('Symptom resolution date is not blank. If date known choose "Symptoms resolved" for symptom status.')
        elif symp_status == 'Unknown symptom status':
            self.issues.append('Symptom status cannot be "Unknown symptom status".')

    def CheckIllness_Duration(self):
        """ Ensure if there is a number for illness duration that there is also an illness duration units.  Added Sept 2022 to account for notifications that were failing.STILL NEED TO FIX!!!"""
        Illness_Duration = self.ReadText('//*[@id="INV139"]')
        if Illness_Duration == 'Yes':
            Illness_Duration_Units = self.ReadDate('//*[@id="INV140"]')
            if (not Illness_Duration_Units):
                self.issues.append("If ilness duration has a number then illness duration units must be specified.")

    ####################### Investigator Check Methods ############################
    '''def CheckInvestigator(self):
        """ Check if an investigator was assigned to the case. """
        investigator = self.ReadText('//*[@id="INV180"]')
        self.investigator_name = investigator
        if investigator:
            self.investigator = True
        else:
            self.investigator = False

    def CheckInvestigatorAssignDate(self):
        """ If an investigator was assinged then there should be an investigator
        assigned date. """
        if self.investigator:
            assigned_date = self.ReadText('//*[@id="INV110"]')
            if not assigned_date:
                self.issues.append('Missing investigator assigned date.')

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

    def RejectNotification(self):
        """ Reject notification on first case in notification queue.
        To be used when issues were encountered during review of the case."""
        reject_path = '//*[@id="parent"]/tbody/tr[1]/td[2]/img'
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
            self.num_rejected += 1'''

    # def SendManualReviewEmail(self):
    #     """ Send email containing NBS IDs that required manual review."""
    #     if (len(self.not_a_case_log) > 0) | (len(self.lab_data_issues_log) > 0):
    #         subject = 'Cases Requiring Manual Review'
    #         email_name = 'manual review email'
    #         body = "COVID Commander,\nThe case(s) listed below have been moved to the rejected notification queue and require manual review.\n\nNot a case:"
    #         for id in self.not_a_case_log:
    #             body = body + f'\n{id}'
    #         body = body + '\n\nAssociated lab issues:'
    #         for id in self.lab_data_issues_log:
    #             body = body + f'\n{id}'
    #         body = body + '\n\n-Nbsbot'
    #         #self.send_smtp_email(recipient, cc, subject, body)
    #         self.send_smtp_email(self.covid_commander, subject, body, email_name)
    #         self.not_a_case_log = []
    #         self.lab_data_issues_log = []