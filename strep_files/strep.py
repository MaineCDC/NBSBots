from base import NBSdriver
import pandas as pd
import smtplib, ssl
from email.message import EmailMessage
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, date
from bs4 import BeautifulSoup
import sys

class Strep(NBSdriver):
    """ A class to review COVID-19 cases in the notification queue.
    It inherits from NBSdriver."""
    
    def __init__(self, production=False):
        super().__init__(production)
        self.num_approved = 0
        self.num_rejected = 0
        self.num_fail = 0
        self.received_date = None

    def StandardChecks(self):
        """ A method to conduct checks that must be done on all cases regardless of investigator. """
        self.Reset()
        self.initial_name = self.patient_name
#########Check Patient Tab#######
        self.CheckFirstName()
        self.CheckLastName()
        self.CheckDOB()
        self.CheckAge()
        self.CheckCurrentSex()
        street_address = self.CheckForValue( '//*[@id="DEM159"]', 'Street address is blank.')
        if any(x in street_address for x in ["HOMELESS", "NO ADDRESS", "NO FIXED ADDRESS", "UNSHELTERED"]):
            self.CheckCounty()
            pass
        else: 
            self.CheckCity()
            self.CheckZip()
            self.CheckCounty()
        self.CheckState()
        self.CheckCountry()
        self.CheckEthnicity()
        self.CheckRaceAna()
########### supplemental info tab #############
        self.GoToSupplementalinfo()
        self.ReadAssociatedLabs()
        #self.AssignLabTypes()
        #self.DetermineCaseStatus()
        self.GetCollectionDate()
        #self.GetReceivedDate()
############ Check Case Info Tab#######
        self.GoToCaseInfo()
        self.CheckJurisdiction()
        self.CheckProgramArea()
        self.CheckInvestigationStartDate()
        self.CheckInvestigationStatus()
        self.CheckSharedIndicator()
        #self.CheckStateCaseID()
###########investigator info
        self.CheckInvestigator()
        self.CheckInvestigatorAssignDate()
        # reporting info
        self.CheckReportDate()
        self.CheckCountyStateReportDate()
        self.CheckReportingSourceType()
        self.CheckReportingOrganization()
        self.CheckPreformingLaboratory()    #laboratory name
        self.CheckDateSpecimen()            #date_specimen
        self.CheckSterileSite()             #sterile site
        #self.CheckPhysician()               #physician
        self.CheckDiagnosisDate()
        self.CheckSymptomDates()            #symptoms
        self.CheckTypeofinfection()         #type of infection
        self.CheckPregnancy()               #pregnancy status
        self.CheckUnderlyingConditions()    #underlying conditions
        self.CheckHealthcareAssociations()  #healthcare association  
        self.CheckHighRiskExposure()        #high risk exposure      
        self.CheckHypoTension()             #hypotension
        self.CheckDiseaseAcquisition()
        self.CheckDieFromIllness()
        self.CheckOutbreak()
        #if self.patient_die_from_illness == 'Yes':
            #self.CheckDeathDate()
        self.CheckPatientHospitalized()
        if self.hospitalization_indicator == 'Yes':
            self.CheckAdmissionDate()
            self.CheckDischargeDate()
        self.CheckCaseStatusNew()           #CaseStatusNew
    
    
    def CheckRaceAna(self):
        """ Must provide race and selection must make sense. """
        self.race = self.CheckForValue('//*[@id="patientRacesViewContainer"]','Race is blank.')
        #If white is selected, other should not be selected
        if "White" in self.race and "Unknown" in self.race:
            self.issues.append("White and Unknown race should not be selected at the same time.")
        if "Other" in self.race:
            self.CheckForValue('//*[@id="DEM196"]', "If Other race is selected there needs to be a comment.")
        # Race should only be unknown if no other options are selected.
        ambiguous_answers = ['Unknown', 'Other', 'Refused to answer', 'Not Asked']
        for answer in ambiguous_answers:
            if (answer in self.race) and (self.race != answer) and (self.race == 'Native Hawaiian or Other Pacific Islander'):
                self.issues.append('"'+ answer + '"' + ' selected in addition to other options for race.')
            
    def CheckProgramArea(self):
        """ Program area must be Airborne. """
        program_area = self.CheckForValue('//*[@id="INV108"]','Program Area is blank.')
        if program_area != 'Airborne and Direct Contact Diseases':
            self.issues.append('Program Area is not "Airborne and Direct Contact Diseases".')

#################### Hospital Check Methods ###################################
    def CheckPatientHospitalized(self):
        #check if patient is hospitalized for this illness
        self.hospital_name = self.ReadText('//*[@id="INV184"]')
        if self.current_case_status != 'Not a Case':
            if not self.hospitalization_indicator:
                self.issues.append('Hospitalized for this illness is blank.')
            elif self.hospitalization_indicator == 'Yes' and not self.hospital_name:
                self.issues.append('Hospitalized for this illness is yes but hospital name is blank.')
            
    def CheckAdmissionDate(self):
        #Check for hospital admission date.
        self.admission_date = self.ReadDate('//*[@id="INV132"]')
        if not self.admission_date:
            self.issues.append('Admission date is missing.')
        elif self.admission_date and self.admission_date > self.now:
            self.issues.append('Admission date cannot be in the future.')

    def CheckDischargeDate(self):
        """ Check for hospital discharge date."""
        if self.patient_die_from_illness == "Yes" and self.hospitalization_indicator == "Yes":
            if not self.discharge_date:                                                         #commented out
                self.issues.append('patient die from illness and patient hospitalized is yes, Discharge date is blank.')   #commented out
        if self.admission_date:
            if self.discharge_date and self.discharge_date < self.admission_date:
                self.issues.append('Discharge date must be after admission date.')
        elif self.discharge_date > self.now:
            self.issues.append('Discharge date cannot be in the future.')
    
    def CheckDeathDate(self):
        """ Death date must be present."""
        death_date = self.ReadDate('//*[@id="INV146"]')
        if not death_date:
            self.issues.append('Date of death is blank.')
        elif death_date > self.now:
            self.issues.append('Date of death date cannot be in the future')

    def CheckSharedIndicator(self):
        """ Ensure shared indicator is yes. """
        shared_indicator = self.ReadText('//*[@id="NBS_UI_19"]/tbody/tr[5]/td[2]')
        if shared_indicator != 'Yes':
            self.issues.append('Shared indicator not selected.')

########################### Parse and process labs ############################
    def GoToSupplementalinfo(self):
        """ Within a patient profile navigate to the Demographics tab."""
        supplemental_info_path = '//*[@id="tabs0head2"]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, supplemental_info_path)))
        self.find_element(By.XPATH,'//*[@id="tabs0head2"]').click()

    def ReadAssociatedLabs(self):
        """ Read table of associated labs."""
        self.labs = self.ReadTableToDF('//*[@id="viewSupplementalInformation1"]/tbody')
        self.name_match = False
        lab_reports = self.find_elements(By.XPATH, '//*[@id="eventLabReport"]/tbody/tr')
        tests = ['STREPTOCOCCUS GROUP A|Streptococcus pyogenes|MICROORGANISM IDENTIFIED: BETA-HEMOLYTIC STREPTOCOCCUS, GROUP A|Streptococci, beta hemolytic group A|Beta-hemolytic streptococcus|S pyogenes hsp60 Bld Pos Ql Probe']
        self.dna_dates = []
        for risk in lab_reports:
            cells = risk.find_elements(By.TAG_NAME, 'td')
            if not cells:
                continue
            try:
                date_collected = datetime.strptime(cells[2].text.strip(), "%m/%d/%Y").date()
            except ValueError:
                continue
            lab_test = cells[3].text.strip()
            if any(pd.Series(lab_test).str.contains(test, na=False, case=False).any() for test in tests):
                self.name_match = True
                self.dna_dates.append(date_collected)
    
        if not self.name_match:
            self.labs = pd.DataFrame()
            self.issues.append('Test results does not have strep A.')
        return self.dna_dates

    def GetReceivedDate(self):
        """Find earliest report date by reviewing associated labs"""
        #self.current_report_date = self.ReadDate('//*[@id="INV111"]')
        if not self.name_match:
            self.issues.append('No associated labs found,Cant determine Report date.')
        elif self.labs['Date Received'] == 'Nothing found to display.':
            self.received_date = datetime(1900, 1, 1).date()
        else:
            try:
                self.labs['Date Received'] = pd.to_datetime(self.labs['Date Received'],format = '%m/%d/%Y %I:%M %p').date()
            except Exception as e:
                self.labs['Date Received'] = pd.to_datetime(self.labs['Date Received'], errors='coerce').date()  #format = '%m/%d/%Y%I:%M %p',
            self.received_date = self.labs['Date Received']

    def GetCollectionDate(self):
        """Find earliest collection date by reviewing associated labs"""
        if not self.name_match:
            self.issues.append('No associated labs found,Cant determine collection date.')
        elif min(self.dna_dates) == 'No date':
            self.collection_date = datetime(1900, 1, 1).date()
        else:
            # Check for any associated labs missing collection date:
            # 1. Set collection date to 01/01/2100 to avoid type errors.
            # 2. Log patient id for manual review.
            no_col_dt_labs = True if min(self.dna_dates)  == 'No Date' else False
            #date_specimen = self.ReadDate('//*[@id="ME8117"]')
            if no_col_dt_labs:
                self.labs['Date Collected'] = '01/01/2100'
                self.issues.insert(0,'**SOME ASSOCIATED LABS MISSING COLLECTION DATE: CENTRAL EPI REVIEW REQUIRED**')
                self.lab_data_issues_log.append(self.ReadPatientID())   
            #self.labs['Date Collected'] = pd.to_datetime(self.labs['Date Collected'], format = '%m/%d/%Y').date()
            #self.collection_date = self.labs['Date Collected'].min()  
            self.collection_date = min(self.dna_dates) if self.dna_dates else None
            
    def CheckSterileSite(self):
        self.current_case_status = self.ReadText('//*[@id="INV163"]')
        sterile_site = self.ReadText('//*[@id="ME127000"]')
        self.non_sterile_site = self.ReadText('//*[@id="ME127002"]')
        if self.current_case_status == 'Not a Case' and not sterile_site:
            pass
        elif not sterile_site :
            self.issues.append('No sterile site is listed.')
        elif sterile_site.lower() == 'Other normally sterile site':
            other_sterile_site = self.CheckForValue('//*[@id="ME127001"]','Other sterile site is blank')  
            #non_sterile_site = self.CheckForValue('//*[@id="ME127002"]','Other sterile site is blank')  
            if not other_sterile_site:
                self.issues.append('Other normally sterile site(specify) is selected but is not specified.')

    def CheckPhysician(self):
        """ Ensure that physician is not empty. """
        saw_physician = self.CheckForValue('//*[@id="ME8169"]', 'blank')
        seen_by_pcp = self.ReadText('//*[@id="ME12104"]')
        pcp_name = self.ReadText('//*[@id="ME12105"]')
        date_of_pcp_visit = self.ReadDate('//*[@id="ME12106"]')
        date_of_physician_visit = self.ReadDate('//*[@id="ME12169"]')
        physician_name = self.ReadText('//*[@id="INV182"]')
        if not saw_physician:
            self.issues.append('Saw Physician is blank.')
        if saw_physician.lower() == "no" and physician_name:
            self.issues.append('Physician name should be blank.')
        if  not seen_by_pcp:
            self.issues.append('Seen by PCP is blank.')
            
            #check for no , yes or unknown- leave all others 
###############Condition#############
    def CheckDiagnosisDate(self):
        """ Check if diagnosis date is present and matches earliest date from
        associated labs. """
        diagnosis_date = self.ReadDate('//*[@id="INV136"]')
        if self.current_case_status != 'Not a Case':
            if not diagnosis_date:
                self.issues.append('Diagnosis date is missing.')
            else:
                if diagnosis_date > self.now:
                    self.issues.append('Diagnosis date cannot be in the future.')
                if diagnosis_date < self.onset_illness_date:
                    self.issues.append('Diagnosis date cannot be before onset illness date.')
                
    def CheckSymptomDates(self):
        """ Ensure date of symptom onset, resolution, and current symptom status
        are consistent."""
        self.illness_end_date = self.ReadDate('//*[@id="INV138"]')
        self.patient_die_from_illness =  self.ReadText('//*[@id="INV145"]')
        death_date = self.ReadDate('//*[@id="INV146"]')
        is_patient_deceased =self.ReadText('//*[@id="DEM127"]')
        if self.current_case_status != 'Not a Case':
            if not self.onset_illness_date:
                self.issues.append('Illness onset date is blank.')
        if self.patient_die_from_illness == 'Yes' and not self.illness_end_date:
            self.issues.append('patient died due to illness is yes but Illness end date is blank.')
        if self.illness_end_date and self.onset_illness_date and self.illness_end_date < self.onset_illness_date:
            self.issues.append('Illness end date cannot be before onset date.')
        
   
    def CheckDieFromIllness(self):
        """ Died from illness should be yes or no. """
        self.patient_die_from_illness =  self.ReadText('//*[@id="INV145"]')
        is_patient_deceased=self.ReadText('//*[@id="DEM127"]')
        patient_deceased_date = self.ReadDate('//*[@id="DEM128"]')
        death_date = self.ReadDate('//*[@id="INV146"]')
        self.discharge_date = self.ReadDate('//*[@id="NBS_INV_GENV2_UI_3"]/tbody/tr[4]/td[2]|//*[@id="INV133"]')
        self.hospitalization_indicator = self.ReadText('//*[@id="INV128"]')
        if self.current_case_status != 'Not a Case':
            '''if not self.patient_die_from_illness:
                self.issues.append('"Did the patient die from this illness" needs a response, yes, no or unknown.')'''
            if self.patient_die_from_illness.lower() == 'yes':
                if not is_patient_deceased:
                    self.issues.append('Patient died from illness is yes but patient deceased is blank.')
                if not death_date:
                    self.issues.append('Patient died from illness is yes but death date is blank.')
                elif is_patient_deceased.lower() == 'no':
                    self.issues.append('Patient died from illness is yes but patient deceased is no.')
                if not patient_deceased_date:
                    self.issues.append('Patient died from illness is yes but patient deceased date is blank.')
                if death_date and patient_deceased_date != death_date:
                    self.issues.append('Patient died from illness is yes, patient deceased date should be the same as death date.') 
                if patient_deceased_date and patient_deceased_date > self.now :
                    self.issues.append('Patient died from illness is yes but patient deceased date cannot be in the future.') 
                if death_date and self.illness_end_date and death_date != self.illness_end_date:
                    self.issues.append('Patient died from illness is yes, death date should be the same as illness end date.')   
            elif self.patient_die_from_illness.lower() == 'unknown':
                #if self.hospitalization_indicator.lower() == 'no':
                    #self.issues.append('Patient died from illness is unknown but patient hospitalized is no.')
                if self.hospitalization_indicator.lower() == 'yes' and self.discharge_date:
                    self.issues.append('Patient died from illness is unknown but patient hospitalized is yes and discharge date is not blank.')
                if self.illness_end_date:
                    self.issues.append('Patient died from illness is unknown but illness end date is not blank.')
            elif self.patient_die_from_illness.lower() == 'no':
                if self.hospitalization_indicator.lower() == 'yes' and not self.discharge_date:
                    self.issues.append('Patient died from illness is no, patient hospitalized is yes but discharge date is blank.')
    def CheckOutbreak(self):
        """ Check if part of an outbreak."""
        outbreak = self.ReadText('//*[@id="INV150"]')
        if self.current_case_status != 'Not a Case':
            if not outbreak:
                self.issues.append('Part of an outbreak is blank.')
                
    def CheckTypeofinfection(self):
        Type_of_infection = self.ReadText('//*[@id="ME128016"]')
        if not Type_of_infection  and self.current_case_status != 'Not a Case':
            self.issues.append("infection is not selected and casestatus is not not a case.")
        elif Type_of_infection.lower() == 'none' and self.current_case_status == 'Not a Case':
            self.issues.append("Type of infection is none and case status isn't not a case.")
        elif Type_of_infection == 'Other':
            other_type_infection = self.ReadText('//*[@id="ME128017"]')
            if not other_type_infection:
                self.issues.append('Other type of infection is blank.')
            elif other_type_infection.lower() in ["not invasive","non invasive","non-invasive","not sterile","non sterile","non-sterile"] and self.current_case_status != 'Not a Case':
                self.issues.append('other type of infection is {other_type_infection} but case status is not not a case.')
            elif other_type_infection:
                pass
  
    def CheckPregnancy(self):
        """ Check if patient is pregnant. """
        pregnant_status = self.ReadText('//*[@id="INV178"]')
        if self.current_case_status != 'Not a Case':
            if self.patient_sex and self.patient_sex == 'Female' and not pregnant_status:
                self.issues.append('When current sex is listed as female  prgnancy status should be yes, no, or unknown')
            
    def CheckUnderlyingConditions (self):
        """ Check if patient has underlying conditions. """
        did_underlying_condition = self.ReadText('//*[@id="INV235"]')
        underlying_condition_yes_explain = self.ReadText('//*[@id="ME15113"]')
        underlying_condition_gas_stss = self.ReadText('//*[@id="ME144040"]')
        if self.current_case_status != 'Not a Case':
            if not did_underlying_condition:
                self.issues.append('Underlying condition is blank.')        
            elif did_underlying_condition == 'Yes':
                if not underlying_condition_yes_explain:
                    self.issues.append('Underlying condition is yes but explanation is not filled.')
                if underlying_condition_gas_stss == 'None' or underlying_condition_gas_stss == 'Unknown':
                    self.issues.append(f'did underlying condition is {did_underlying_condition} but underlying condition is {underlying_condition_gas_stss}." .')
                if not underlying_condition_gas_stss :
                    self.issues.append('Did Underlying condition exist is yes but underlying condition  is blank.')
            elif did_underlying_condition.lower() == 'no':
                if underlying_condition_yes_explain and underlying_condition_yes_explain.lower() not in ['none', 'unknown']:
                    self.issues.append('Underlying conditions selection error.')
                if underlying_condition_gas_stss and underlying_condition_gas_stss.lower() not in ['none', 'unknown']:
                    self.issues.append(f'did_underlying_condition is {did_underlying_condition}, underlying condition GAS/STSS is {underlying_condition_gas_stss} selection error.')
                #elif underlying_condition_gas_stss:
                    #self.issues.append(f'Did Underlying condition is {did_underlying_condition} but underlying condition is not blank.')
                
            elif did_underlying_condition.lower() == 'unknown':
                if not underlying_condition_gas_stss:
                    self.issues.append(f'Did Underlying condition is {did_underlying_condition} but underlying condition is blank.')
                if underlying_condition_yes_explain and underlying_condition_yes_explain.lower() not in ['none', 'unknown']:
                    self.issues.append('Underlying conditions selection error.')
                if underlying_condition_gas_stss.lower() not in ['none', 'unknown']:
                        self.issues.append(f'did_underlying_condition is {did_underlying_condition}, underlying condition GAS/STSS is {underlying_condition_gas_stss} selection error.')
                

    #######################Healthcare Associations (in the 30 days prior to first positive)#########
    def CheckHealthcareAssociations(self):
        type_of_procedure = self.ReadText('//*[@id="ME120001"]')
        Name_of_facility = self.ReadText('//*[@id="ME128014"]')
        discharged_prior_surgery = self.ReadText('//*[@id="ME128019"]')  #1
        Location_post_surgical = self.ReadText('//*[@id="ME128020"]')
        self.invasive_procedure = self.ReadText('//*[@id="ME128025"]')
        self.Type_invasive_procedure = self.ReadText('//*[@id="ME128027"]')
        facilityname_procedure = self.ReadText('//*[@id="ME128027"]')
        discharge_prior_procedure = self.ReadText('//*[@id="ME128029"]')
        Type_of_healthcare = self.ReadText('//*[@id="ME128030"]')
        other_healthcare_setting = self.ReadText('//*[@id="ME128031"]')
        healthcare_discharge_date = self.ReadDate('//*[@id="ME124047"]')  
        Have_surgery = self.ReadText('//*[@id="ME128012"]')
        Delivered_baby = self.ReadText('//*[@id="ME128015"]/tbody/tr[8]/td[2]')
        Delivery_type = self.ReadText('//*[@id="ME128022"]')
        discharge_prior_delivery = self.ReadText('//*[@id="ME128023"]')
        if self.current_case_status != 'Not a Case' :
            if not Have_surgery:
                self.issues.append('Healthcare association is blank.')
            elif Have_surgery == 'Yes':
                if self.surgery_date and self.surgery_date > self.date_specimen:
                    self.issues.append('Surgery date cannot be after specimen collection date.')  
                if self.surgery_date and self.surgery_date > self.now:
                    self.issues.append('Surgery date cannot be in the future.')
                if not type_of_procedure or not Name_of_facility or not self.surgery_date or not discharged_prior_surgery or not Location_post_surgical:
                    self.issues.append('Surgery is yes, below fields are missing.')
            if self.patient_sex and self.patient_sex == 'Female':
                if not Delivered_baby:
                    self.issues.append('Delivered baby is blank.')
                elif Delivered_baby == 'Yes':
                    if self.Delivery_date and self.Delivery_date > self.now:
                        self.issues.append('Delivery date cannot be in the future.')
                    if not self.Delivery_date or not Delivery_type or not discharge_prior_delivery:
                        self.issues.append('Delivered baby is yes,below fields are missing.')
            if not self.invasive_procedure:
                self.issues.append('invasive procedure cannot be empty.')
            elif self.invasive_procedure == 'Yes':
                if not self.Date_invasive_procedure or not self.Type_invasive_procedure or not facilityname_procedure or not discharge_prior_procedure:
                    self.issues.append('invasive procedure is yes, below fields are missing.')  
            if Type_of_healthcare and Type_of_healthcare.lower() in ["inpatient", "outpatient","same day surgery"]:
                if  not self.healthcare_admissiondate :
                    self.issues.append(f'type of Healthcare exposure is {Type_of_healthcare}, admission date is missing .')
                if not healthcare_discharge_date:
                    if discharged_prior_surgery.lower() == 'yes' or discharge_prior_procedure.lower() == 'yes' or discharge_prior_delivery.lower() == 'yes':
                        self.issues.append(f'type of Healthcare exposure is {Type_of_healthcare}, discharge date is missing .')
            elif Type_of_healthcare and Type_of_healthcare.lower() in ["other"]:
                if  not other_healthcare_setting or not self.healthcare_admissiondate or not healthcare_discharge_date:
                    self.issues.append('type of Healthcare exposure is other,check for below fields: other type of healthcare or admission date or discharge date are missing .')

###########Epidemiologic####            
##########Exposure##############
    def CheckHighRiskExposure(self):
        """ Check if high risk exposure is indicated. """ 
        exposure = self.ReadTableToDF('//*[@id="ME128032"]/tbody/tr[1]/td/table')
        if self.current_case_status != 'Not a Case':
            if not exposure.empty:
                high_risk_exposure = exposure.loc[0, "High Risk Exposure"]
                any_igas_cases = exposure.at[0, "Any iGAS cases?"]
                if pd.Series(high_risk_exposure).astype(str).str.contains("Daycare|LTC facility|School").any():
                    if not exposure.at[0, "Facility Name"]:
                        self.issues.append('High risk exposure is indicated but facility name is blank.')
                    if not exposure.at[0, "Any iGAS cases?"]:
                        self.issues.append('High risk exposure is indicated but any igas cases is blank.')
                    elif pd.Series(any_igas_cases).astype(str).str.contains("Yes").any():
                        if not exposure.at[0, "iGAS Case Number"]:
                            self.issues.append('High risk exposure is indicated but iGAS case number is blank.')
            
    def CheckHypoTension(self):
        hypotension = self.ReadText('//*[@id="ME128033"]')
        if self.current_case_status != 'Not a Case':
            if not hypotension:
                self.issues.append('Hypotension is blank.')
        
#########Disease Acquisition##########
    def CheckDiseaseAcquisition(self):
        """ Check if disease acquisition is indicated. """
        disease_acquisition = self.ReadText('//*[@id="INV152"]')
        #country_of_usual_residence = self.ReadText('//*[@id="INV501"]')
        if self.current_case_status != 'Not a Case':
            if not disease_acquisition:
                self.issues.append('Disease acquisition is blank.')
            
    def CheckCaseStatusNew(self):
        """ Transmission mode should blank or airborne"""
        transmission_mode =  self.ReadText('//*[@id="INV157"]')
        detection_method = self.ReadText('//*[@id="INV159"]')
        confirmation_method = self.ReadText('//*[@id="INV161"]')
        confirmation_date = self.ReadDate('//*[@id="INV162"]')
        if self.current_case_status != 'Not a Case':
            if not transmission_mode:
                self.issues.append('Transmission mode is blank.')
            if not detection_method:
                self.issues.append('Detection method is blank.')
            if not confirmation_method:
                self.issues.append('Confirmation method is blank.')
                
            if not confirmation_date:
                self.issues.append('Confirmation date is blank.')
            elif self.investigation_start_date and confirmation_date < self.investigation_start_date:
                self.issues.append('Confirmation date cannot be prior to investigation start date.')
            elif confirmation_date > self.now:
                self.issues.append('Confirmation date cannot be in the future.')
        
        """ Case status must be consistent with associated labs. """
        self.current_case_status = self.ReadText('//*[@id="INV163"]')
        self.sterile_site = self.ReadText('//*[@id="ME127000"]')
        id = self.ReadPatientID()
        if not self.current_case_status or self.current_case_status in ['Unknown', 'Suspect', 'Probable']:
            self.issues.append(' Review Case status.')
        if self.current_case_status == "Not a Case":
            if self.state != 'Maine':
                if id not in self.not_a_case_log:
                    self.not_a_case_log.append(id)
                self.issues.append('State is not Maine and current_case_status is not "Not a Case".')
            else:
                if self.jurisdiction == 'Out of State':
                    if id not in self.not_a_case_log:
                        self.not_a_case_log.append(id)
                    self.issues.append('State is Maine and current_case_status is "Not a Case" and jurisdiction is Out of State .')
                    #if not self.collection_date or not self.date_specimen or self.date_specimen != self.collection_date:
                        #self.issues.append('State is Maine and current_case_status is "Not a Case" and collection date or specimen date is not filled or does not match.')
                    if not self.sterile_site and self.non_sterile_site:
                        self.issues.append('State is Maine and current_case_status is "Not a Case" and sterile site and non sterile site is not filled.')
                
        if self.state == 'Maine' and self.current_case_status == 'Not a Case':
            if self.sterile_site and len(self.issues) > 0:
                self.issues.append('State is Maine and current_case_status is "Not a Case" and has issues so it needs manual review.')
            
        if self.current_case_status == 'Not a Case' and self.state == 'Maine' and self.jurisdiction != 'Out of State':
            if not self.collection_date and not self.date_specimen and not self.non_sterile_site:
                if not self.sterile_site:
                    self.issues = []
            elif self.non_sterile_site:
                if not self.sterile_site:
                    self.issues = []
            
   
######################### Symptom Check Methods ################################
    def CheckDateSpecimen(self):
        """ Check if date specimen is present and matches earliest date from
        associated labs. """
        #date of surgery
        self.surgery_date = self.ReadDate('//*[@id="ME128013"]')
        self.Delivery_date = self.ReadDate('//*[@id="ME116004"]')
        self.Date_invasive_procedure = self.ReadDate('//*[@id="ME128026"]')
        self.healthcare_admissiondate = self.ReadDate('//*[@id="ME124046"]')
        self.onset_illness_date = self.ReadDate('//*[@id="INV137"]') # 	03/26/2025
        self.date_specimen = self.ReadDate('//*[@id="ME8117"]')
        if not self.date_specimen:
            self.issues.append('Date specimen is missing.')
        elif self.date_specimen > self.now:
            self.issues.append('Date specimen cannot be in the future.')
        elif self.onset_illness_date and self.date_specimen < self.onset_illness_date:
            self.issues.append('Date specimen cannot be before onset illness date.')
        elif self.collection_date and self.date_specimen != self.collection_date:
            self.issues.append('Date specimen does not match collection date.')
        if self.Delivery_date and self.Delivery_date > self.date_specimen:
            self.issues.append('Delivery date cannot be after specimen collection date.')
        if self.Date_invasive_procedure and self.Date_invasive_procedure > self.date_specimen:
            self.issues.append('Invasive procedure date cannot be after specimen collection date.')
        if self.healthcare_admissiondate and self.healthcare_admissiondate > self.date_specimen:
            self.issues.append('Healthcare admission date cannot be after specimen collection date.')
            
                      

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
    

    def SendStrepEmail(self, body, inv_id, email=None):
        message = EmailMessage()
        message.set_content(body)
        message['Subject'] = f'Strep Bot {inv_id}'
        message['From'] = self.nbsbot_email
        if email:
            message['To'] = ', '.join(["disease.reporting@maine.gov", email])
        else:
            message['To'] = ', '.join(["disease.reporting@maine.gov"])
        smtpObj = smtplib.SMTP(self.smtp_server)
        smtpObj.send_message(message)
        print('sent email', inv_id)
