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



class Anaplasma(NBSdriver):
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
        
        self.CheckFirstName()
        self.CheckLastName()
        self.CheckDOB()
        
        self.CheckAgeType()
        self.CheckCurrentSex()#removed Ana
        self.CheckMortality()
        #self.CheckStAddr()
        street_address = self.ReadText( '//*[@id="DEM159"]') #, 'Street address is blank.'
        if any(x in street_address for x in ["HOMELESS", "NO ADDRESS", "NO FIXED ADDRESS", "UNSHELTERED"]):
            pass
        else: 
            self.CheckCity()
            self.CheckZip()
            self.CheckCounty()
            #self.CheckCityCountyMatch()
        self.CheckStateANA()
        self.CheckCountry()
        self.CheckPhone()
        self.CheckEthnicity()
        self.CheckRaceAna()
        # self.CheckDeceased()
        self.GoToSupplemental()
        self.CheckLabReports()
        if self.returned_by_link:
            self.GoToTickBorne()
        self.CheckEPI()
        self.CheckJurisdiction()              #new code
        self.CheckInvestigationStartDate()#removed Ana
        self.CheckDateClosed()
        self.CheckAge()
        self.CheckReportDate()
        self.CheckCountyStateReportDate()
        self.CheckInvestigationStatus()
        self.CheckInvestigatorAna()
        self.CheckInvestigatorAssignDateAna()
        self.CheckCulture()
        # self.CheckMmwrWeekAna()
        self.CheckMmwrYearAna()
        self.CheckReportingSourceType()
        self.CheckReportingOrganization()
        self.CheckConfirmationDate()
        # self.CheckAdmissionDate() #new code to get admission date and compare to discharge
        self.CheckDischargeDate()                                   #new code, added this from covidcase review. modified method logic
        self.CheckDiagnosisDate()
        self.CheckIllnessDurationUnits()
        self.CheckHospitalization()
        # self.CheckPregnancyStatus()
        ###Anaplasma Specific Checks###
        self.CheckImmunosupressed()
        #Check lab name, spelling is wrong but that is how it is defined in the legacy code
        self.CheckPerformingLaboratory()
        # self.CheckTickBite()
        self.CheckPhysicianVisit()                                   #new code
        self.CheckOtherDiagnosticTest()                                 #new code
        self.CheckDateSpecimenCollected()
        self.CheckSerology()
        if self.pcr_positive == "Yes" or (self.titer_value and self.titer_value > 64) or (not self.titer_value and self.reporting_organization == "MDLAB"):
            self.CheckDeath()                         #removed '77' after parenthesis
            self.CheckLifeThreatening()
        # if self.reporting_organization != 'MDLAB' and self.titer_value and self.titer_value > 64:
        #     self.CheckDeath()                         #removed '77' after parenthesis
        #     self.CheckLifeThreatening()
        self.CheckFourFoldChange()                                   #new code
        self.CheckOutbreak()
        self.CheckSymptoms()#removed Ana
        self.CheckTravelInfo()
        self.CheckWhereDisease() 
        self.CheckClinicallyCompatible()
        self.CheckIllnessLength()
        self.CheckAcuteOrConvalscent()                              #new code
        #self.CheckDetectionMethod() #new code                           #new code reject if not detectionmethod
        self.CheckConfirmationMethod() #removed Ana
        self.CheckLTF()
        # if self.serology_test_type and str(self.serology_test_type).endswith("IgM"):
        #     self.issues.append('IgM lab info entered into serology section, but should not be')
        #     print("Issues with serology test type of IgM")
        # else:
        self.CheckCaseAna()

    ####################### Patient Demographics Check Methods ############################
    def CheckAge(self):
        """ Must provide age. """
        self.age = self.ReadText('//*[@id="INV2001"]')
        if not self.age:
            self.issues.append('Age is blank.')
            print(f"age: {self.age}")
        else:
            current = datetime.now().date()
            assumed_age = current.year  - self.dob.year - ((current.month, current.day) < (self.dob.month, self.dob.day)) #returns 1 or 0
            age_difference = abs(assumed_age - int(self.age))
            if age_difference == 0:
                return
            else:
                birthday_this_year = self.dob.replace(year=self.investigation_start_date.year)
                
                if birthday_this_year >= self.investigation_start_date and birthday_this_year <= self.date_closed and age_difference == 1:
                    return
                if birthday_this_year > self.investigation_start_date and birthday_this_year > self.date_closed and age_difference == 1:
                    return
                self.issues.append(f"Reported age incorrect. Reported Age: {self.age} Assumed Age: {assumed_age}") 
        
    def CheckAgeType(self):
        """ Must age type must be one of Days, Months, Years. """
        self.age_type = self.ReadText('//*[@id="INV2002"]')
        if not self.age_type:
            self.issues.append('Age Type is blank.')
            print(f"age_type: {self.age_type}")
        elif self.age_type != "Days" and self.age_type != "Months" and self.age_type != "Years":
            self.issues.append('Age Type is not one of Days, Months, or Years.')
            print(f"age_type: {self.age_type}")
        
    def CheckRaceAna(self):
        """ Must provide race and selection must make sense. """
        self.race = self.ReadText('//*[@id="patientRacesViewContainer"]') #,'Race is blank.'
        if self.ethnicity == 'Unknown' or not self.ethnicity and self.race:
            self.issues.append('Ethnicity is unknown but race is filled out')
            print(f"race: {self.race}; ethnic: {self.ethnicity}")
        if "White" in self.race and "Unknown" in self.race:
            self.issues.append("White and Unknown race should not be selected at the same time.")
            print(f"race: {self.race}")
        #If white is selected, other should not be selected
        if "White" in self.race and "Other" in self.race:
            self.issues.append("White and Other race should not be selected at the same time.")
            print(f"race: {self.race}")
        definitive_races = ['White', 'Black or African American', 'Asian', 'American Indian or Alaska Native', 'Native Hawaiian or Other Pacific Islander']  #New code
        if any(race in self.race for race in definitive_races) and 'Other' in self.race:                                                  #New code
            self.issues.append('Case rejected: Definitive race and Other race should not be selected together.')                            #New code
            print(f"race: {self.race}")
        if "Other" in self.race:
            self.ReadText('//*[@id="DEM196"]') #, "If Other race is selected there needs to be a comment."
        # Race should only be unknown if no other options are selected.
        ambiguous_answers = ['Unknown', 'Other', 'Refused to answer', 'Not Asked']
        for answer in ambiguous_answers:
            if (answer in self.race) and (self.race != answer) and (self.race == 'Native Hawaiian or Other Pacific Islander'):
                self.issues.append('"'+ answer + '"' + ' selected in addition to other options for race.')
                print(f"race: {self.race}")
    
    def CheckDeceased(self):
        self.is_deceased = self.ReadText('//*[@id="DEM127"]')

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
        
    # def read_city(self):
    #     """Read the current city/town."""
    #     self.city_path = '//*[@id="DEM161"]'
    #     self.city = self.find_element(By.XPATH, self.city_path).text
        
    # def CheckCityCountyMatch(self):
    #     """Look up the county using the city and check to see if matches the listed county. """
    #     self.read_city()
    #     if self.county_lookup(self.city, 'Maine') != '':
    #         if (self.county_lookup(self.city, 'Maine') + " County") != self.county:
    #             self.issues.append('City and County do not match.')

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
        mortality_as_of_date = self.ReadText('//*[@id="NBS097"]')
        self.is_deceased = self.ReadText('//*[@id="DEM127"]')

        # if not mortality_as_of_date and not self.is_deceased: 
        #     self.issues.append("Answers to mortality questions missing.")
        
    ####################### Investigator Check Methods ############################
    
    def GoToTickBorne(self):
        Tickborne_path = '//*[@id="tabs0head1"]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, Tickborne_path)))
        self.find_element(By.XPATH, Tickborne_path).click()
    
    def GoToSupplemental(self):
        supplemental_path = '//*[@id="tabs0head2"]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, supplemental_path)))
        self.find_element(By.XPATH, supplemental_path).click()

    def CheckReportingProvider(self):
        """ Check if the reporting provider is empty"""
        self.reporting_provider = self.ReadText('//*[@id="INV181"]')

    #Needs to be around lab date, can be after if immediately notifiable
    def CheckInvestigationStartDate(self):
        """ Verify investigation start date is on or after report date. """
        self.investigation_start_date = self.ReadDate('//*[@id="INV147"]')
        self.report_date = self.ReadDate('//*[@id="INV111"]')
        if not self.investigation_start_date:
            self.issues.append('Investigation start date is blank.')
            print(f"investigation_start_date: {self.investigation_start_date}")
        elif self.investigation_start_date < (self.report_date - relativedelta(weeks=1)):
            self.issues.append('Investigation start date must be within one week before report date or after report date.')
            print(f"investigation_start_date: {self.investigation_start_date}")
        elif self.investigation_start_date > self.now:
            self.issues.append('Investigation start date cannot be in the future.')
            print(f"investigation_start_date: {self.investigation_start_date}")
        

    def CheckInvestigatorAna(self):
        """ Check if an investigator was assigned to the case. """
        investigator = self.ReadText('//*[@id="INV180"]')
        if not self.investigator_name:
            self.investigator_name = investigator
        if not investigator:
            self.issues.append('Investigator is blank.')
            print(f"investigator: {investigator}")
            

    def CheckInvestigatorAssignDateAna(self):
        """ If an investigator was assigned then there should be an investigator
        assigned date. """
        if self.investigator_name:
            self.assigned_date = self.ReadDate('//*[@id="INV110"]')
            if not self.assigned_date:
                self.issues.append('Missing investigator assigned date.')
                print(f"investigator_assigned_date: {self.assigned_date}")
            elif self.lab_report_date and self.assigned_date < self.lab_report_date:
                self.issues.append("Date assigned to investigation is before lab report date.")
            
            # if self.investigation_start_date and self.assigned_date and self.assigned_date < self.investigation_start_date:
            #     self.issues.append("Date assigned to investigation is before investigator start date.")

            # elif self.assigned_date and self.investigation_start_date:
            #     if self.assigned_date < self.investigation_start_date:
            #         self.issues.append('Investigator assigned date is before investigation start date.')
            #         print(f"investigator_assigned_date: {self.assigned_date}")
    def CheckDateClosed(self):
        self.date_closed = self.ReadDate('//*[@id="ME11163"]')
        if self.date_closed and self.investigation_start_date and self.date_closed < self.investigation_start_date:
            self.issues.append("Date closed cannot be before investigation start date.")

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
            if self.is_deceased != "Yes":
                self.issues.append("Patient died from illness but 'is the patient deceased' is not 'Yes'")

            if not death_date:
                self.issues.append('Date of death is blank when "Did the patient die from this illness?" is yes.')
                print(f"death: {self.death_indicator}")
            elif death_date > self.now:
                self.issues.append('Date of death date cannot be in the future.')
                print(f"death: {self.death_indicator}")
        # elif self.death_indicator not in ['Yes', 'No', 'Unknown']:
        #     self.issues.append('Death indicator cannot be blank')
        #     print(f"death: {self.death_indicator}")
        
        # if self.hospitalization_indicator == "Yes" and not self.discharge_date and (self.death_indicator and self.death_indicator != "Unknown"):
        #     self.issues.append('"Did the patient die from this illness?" should be Unknown when Hospitalized is Yes and Discharge Date is blank.')

    def CheckCulture(self):
        self.culture_done = self.ReadText('//*[@id="ME24178"]')
        self.culture_positive = self.ReadText('//*[@id="ME22119"]')
        if self.culture_positive == "Yes":
            self.issues.append("Culture positive is marked as Yes.")

    def CheckHospitalization(self):
        """ Read hospitalization status. If yes need date and hospital """
        self.hospitalization_indicator = self.ReadText('//*[@id="INV128"]')
        if self.hospitalization_indicator == "Yes":
            hospital_name = self.ReadText('//*[@id="INV184"]')
            if not hospital_name:
                self.issues.append('Hospital name missing.')
                print(f"hospitalization, hospital_name: {hospital_name}")
            self.admission_date = self.ReadDate('//*[@id="INV132"]')
            # if not self.admission_date:
            #     self.issues.append('Admission date is missing.')
            #     print(f"hospitalization, admission_date: {self.admission_date}")
            if self.admission_date and self.admission_date > self.now:
                self.issues.append('Admission date cannot be in the future.')
                print(f"hospitalization, admission_date: {self.admission_date}")
        # elif self.hospitalization_indicator not in ['Yes', 'No']: 
        #     self.issues.append("Patient hospitalization status not indicated.")
            
    def CheckIllnessDurationUnits(self):
        """ Read Illness duration units, should be either Day, Month, or Year """
        self.IllnessDurationUnits = self.ReadText('//*[@id="INV140"]')
        if self.IllnessDurationUnits != "":
            if self.IllnessDurationUnits != "Day" and self.IllnessDurationUnits != "Month" and self.IllnessDurationUnits != "Year":
                self.issues.append('Illness Duration is not in Days, Months, or Years.')
                print(f"illness_duration_units: {self.IllnessDurationUnits}")
    
    def CheckPregnancyStatus(self):
        """ Check that pregnancy status isn't blank."""
        pregnant_status = self.ReadText('//*[@id="INV178"]')
        if pregnant_status not in ['Yes', 'No', 'Unknown'] and self.patient_sex != "Male":
            self.issues.append('Pregnant status is blank.')

    ################# Anaplasma Specific Check Methods ###############################
    def CheckTickBite(self):
        """ If Tick bite is yes, need details """
        self.TickBiteIndicator = self.ReadText('//*[@id="ME23117"]')
        #if not self.TickBiteIndicator:                                           #code commented. not necessary to have tickbite history
            #self.issues.append('Missing tick bite history.')                    #code commented. not necessary
        if self.TickBiteIndicator == "Yes":
            self.TickBiteNote = self.ReadText('//*[@id="ME23119"]')
            if not self.TickBiteNote:
                self.issues.append('History of tick bite, but no details.')
                print(f"tick_bite: {self.TickBiteIndicator}")

    def CheckOutbreak(self):
        """ Outbreak should not be yes """
        self.OutbreakIndicator = self.ReadText('//*[@id="INV150"]')
        if self.OutbreakIndicator == "Yes":
            self.issues.append('Outbreak should not be yes.')
            print(f"out_break: {self.OutbreakIndicator}")

    def CheckImmunosupressed(self):
        """ If patient is immunosupressed, need condition info """
        self.ImmunosupressedIndicator = self.ReadText('//*[@id="ME24123"]')
        if self.ImmunosupressedIndicator == "Yes":
            self.ImmunosupressedNote = self.ReadText('//*[@id="ME15113"]')
            if not self.ImmunosupressedNote:
                self.issues.append('Patient is immunosurpressed, but the condition is not listed.')
                print(f"Immunosuppressed: {self.ImmunosupressedIndicator}")

    def CheckLifeThreatening(self):
        """ If patient has a life threatening condition, need condition info """
        self.LifeThreateningIndicator = self.ReadText('//*[@id="ME24117"]')
        if self.LifeThreateningIndicator == "Other":
            self.LifeThreateningNote = self.ReadText('//*[@id="ME24124"]')
            if not self.LifeThreateningNote:
                self.issues.append('Patient has other life-threatening condition, but the condition is not listed.')
                print(f"life_threatening: {self.LifeThreateningIndicator}")
        # elif not self.LifeThreateningIndicator:
        #     self.issues.append('Life-Threatening complications indicator missing.')
        #     print(f"life_threatening: {self.LifeThreateningIndicator}")

    def CheckPhysicianVisit(self):                                                                                   #new method defined here. -JH
        """If patient saw physician, but there is no visit date, then reject case"""
        saw_physician = self.ReadText('//*[@id="ME8169"]')
        physician_visit_date = self.ReadDate('//*[@id="ME12169"]')
        physician = self.ReadText('//*[@id="INV182"]')
        if saw_physician == 'No':
            if not physician_visit_date and self.reporting_provider:
                self.issues.append("Case rejected: No physician visit date documented.")
                print(f"physician_visit_date: {physician_visit_date}")
        elif saw_physician == 'Yes':
            if not physician:
                self.issues.append("Missing physician name despite seeing physician.")
                print(f"physician_name: {physician}")

            if not physician_visit_date:
                self.issues.append(f"Case rejected: Physician visit date is missing despite seeing physician. {physician_visit_date}")
                print(f"physician_visit_date: {physician_visit_date}")
    
    def CheckAcuteOrConvalscent(self):
        serologyTestIs = self.ReadText('//*[@id="ME13102"]')
        if str(self.serology_test_type).endswith('IgG') and self.IllnessOnset != '':
            end_date = pd.to_datetime(self.Sero_table["Serology Collection Date"].values[0])
            print("ddd", end_date, self.IllnessOnset)
            week_diff = (end_date.date() - self.IllnessOnset).days
            if not str(self.Sero_table["Acute or Convalescent"].values[0]):
                self.issues.append("Acute or Convalescent is blank.")
            else:
                if week_diff > 14 and str(self.Sero_table["Acute or Convalescent"].values[0]) != "Convalescent":
                    self.issues.append('convalescent, not acute.')
                elif week_diff <= 14 and str(self.Sero_table["Acute or Convalescent"].values[0]) != "Acute":
                    self.issues.append('acute, not convalescent.')
            
            # month_diff = (end_date.dt.year.values[0] - self.IllnessOnset.year) * 12 + (end_date.dt.month.values[0] - self.IllnessOnset.month)
            # if month_diff > 5 and str(self.Sero_table["Acute or Convalescent"].values[0]) != "Convalescent":
            #     self.issues.append('convalescent, not acute.')
            # elif month_diff < 5 and str(self.Sero_table["Acute or Convalescent"].values[0]) != "Acute":
            #     self.issues.append('acute, not convalescent.')
    
    def CheckFourFoldChange(self):
        self.fourFoldChange = self.ReadText('//*[@id="ME24115"]')
        print("ffchange: ", self.fourFoldChange)
        if len(self.Sero_table) < 2:
            if self.fourFoldChange and self.fourFoldChange not in ["Unknown", "No"]:
                self.issues.append('“ Fourfold change in antibody titer” field should be "No/Unknown" if only one IgG test.')
        else:
            if self.fourFoldChange in ["Yes", "No"] and not self.follow_up_tests:
                self.issues.append('Fourfold change in antibody titer should be blank if no follow-up test.')

    def CheckCaseAna(self):
        def parse_titer_value(x):
            if ":" in str(x):
                return float(x.split(":")[1])
            return float(str(x).replace("<", "").replace(">", ""))
        
        self.CaseStatus = self.ReadText('//*[@id="INV163"]')
        print("cstat", self.CaseStatus)
        # self.ConfirmationMethod = self.ReadText('//*[@id="INV161"]')
        def condition_set(item):
            return item == "Yes"

        def atleast2(condition, sympts):
            count = 0
            for symp in sympts:
                if condition(symp):
                    count =+1
            
            return True if count >=2 else False

        has_any_symptom = any(symptom in ['Yes', 'High'] for symptom in self.symptoms_list)
        # has_no_symptom = all(symptom != 'Yes' for symptom in self.symptoms_list)
        exclude_sweat_chills_fever = [
            self.Headache, self.Myalgia, self.FatigueMalaise, self.Anemia, 
            self.Leukopenia, self.Thrombocytopenia, self.ElevatedHepaticTransaminase, self.ElevatedCRP]
        # exclude_fever = [self.Anemia, self.Leukopenia, self.Thrombocytopenia, self.ElevatedHepaticTransaminase, self.ElevatedCRP]
        # [self.Headache, self.Myalgia, self.FatigueMalaise]

        two_symptoms = sum(1 for symptom in exclude_sweat_chills_fever if symptom in ['Yes', 'High'])
        # self.Fever == "No" and 
        symptom_test = (self.Fever == "Yes" and two_symptoms >= 2) or (self.Chills == "Yes" and two_symptoms >= 2)

        titer_values = self.Sero_table["Titer Value"].apply(parse_titer_value)
        serologic_tests = str(self.serology_test_type).endswith("IgG") and any(titer_values >= 128) and any(self.Sero_table["Serology Positive?"] == "Yes")
        
        # if all(titer_values < 128): 
        #     if self.CaseStatus != "Not a Case":
        #         self.issues.append("Does not meet the case definition, but does not have Not a Case status. less titer")
        #         self.CorrectCaseStatus = "Not a Case"
        #         print(f"case_status: {self.CaseStatus}")
        if self.negative_lab_result and self.CaseStatus != "Not a Case":
            self.issues.append(f"Does not meet the case definition, but does not have Not a Case status.")
            self.CorrectCaseStatus = "Not a Case"
            print(f"case_status: {self.CaseStatus}: {self.ClinicCompIndicator}:{self.CaseStatus}")
            return
        if self.CheckClinicallyCompatible == "No" and has_any_symptom:
            self.issues.append("Symptom marked as yes, but clinically compatible illness was marked as no")

        if self.titer_value and self.titer_value < 128 and self.CaseStatus != "Not a Case" and self.lab_is_serology: 
            self.issues.append(f"Titer value is less than 128, but does not have Not a Case status. no match {self.titer_value}.")
            self.CorrectCaseStatus = "Not a Case"

        elif self.ClinicCompIndicator == "Yes":
            if (self.fourFoldChange == "Yes" or self.other_diagnostic_test == "Yes") and has_any_symptom and ("Laboratory confirmed" in self.confirmation_method or self.pcr_positive == "Yes"):
                # if "Laboratory confirmed" not in self.confirmation_method:
                #     self.issues.append("Confirmation method should be 'Laboratory Confirmed'.")

                if self.CaseStatus != "Confirmed":
                    self.issues.append("Meets case definition for a confirmed case but is not a confirmed case.")
                    self.CorrectCaseStatus = "Confirmed"
                    print(f"case_status: {self.CaseStatus}")
            elif symptom_test and (serologic_tests or self.morulae_visualization_done == "Yes") and "Laboratory confirmed" not in self.confirmation_method:
                # symptom_test and (serologic_tests or self.morulae_visualization_done == "Yes") and "Laboratory confirmed" not in self.confirmation_method
                if self.CaseStatus != "Probable":
                    self.issues.append("Meets case definition for a probable case but is not a probable case.")
                    self.CorrectCaseStatus = "Probable"
                    print(f"case_status: {self.CaseStatus}")
            elif self.Fever != "Yes" and self.Chills != "Yes" and self.CaseStatus != "Not a Case":
                self.issues.append("Does not meet the case definition, but does not have Not a Case status. no match.")
                self.CorrectCaseStatus = "Not a Case"
                print(f"case_status: {self.CaseStatus}")
            elif not self.CorrectCaseStatus:
                if self.CaseStatus == "Confirmed":
                    self.issues.append("Incorrect case status!. Match not found.")
        elif self.ClinicCompIndicator == "Unknown":
            if (serologic_tests or self.fourFoldChange == "Yes" or self.other_diagnostic_test == "Yes") and "Laboratory confirmed" not in self.confirmation_method:
                if self.CaseStatus != 'Suspect': 
                    self.issues.append(f"'{self.CaseStatus}'Does not meet the case definition, but does not have Suspect status.")
                    self.CorrectCaseStatus = "Suspect"
                    print(f"case_status: '{self.CaseStatus}' {self.CorrectCaseStatus == self.CaseStatus}")
            # elif self.CaseStatus != "Not a Case": 
            #     self.issues.append("Does not meet the case definition, but does not have Not a Case status.")
            #     self.CorrectCaseStatus = "Not a Case"
            #     print(f"case_status: {self.CaseStatus}")
        elif self.CaseStatus != "Not a Case":
            self.issues.append(f"Does not meet the case definition, but does not have Not a Case status.")
            self.CorrectCaseStatus = "Not a Case"
            print(f"case_status: {self.CaseStatus}: {self.ClinicCompIndicator}:{self.CaseStatus}")
        elif self.CaseStatus == "Not a Case" or self.ClinicCompIndicator == "No" or self.negative_lab_result:
            self.issues.clear()
            
    def CheckDateSpecimenCollected(self):
        """ Check for follow-up tests """
        date_specimen_collected = self.ReadDate('//*[@id="ME8117"]')
        # if not date_specimen_collected and self.case_status == "Confirmed":
        #     self.issues.append("date specimen collected cannot be blank when Case status is confirmed.")
        # else:
        if self.lab_specimen_collection_date and date_specimen_collected and self.lab_specimen_collection_date != date_specimen_collected:
            self.issues.append(f"Specimen collection dates {self.lab_specimen_collection_date} do not match dates on lab report {date_specimen_collected}.")
        print(f"{self.lab_specimen_collection_date} date specimen collected: {date_specimen_collected}")

    def CheckSerology(self):
        """ If patient has reported positive serology the serology section needs to be filled out. """
        #Serology info is only displayed if you click on the button next to the lab report. There could be more than one.
        html = self.find_element(By.XPATH, '//*[@id="ME24112"]/tbody/tr[1]/td/table/tbody/tr/td[2]/table').get_attribute('outerHTML')
        soup = BeautifulSoup(html, 'html.parser')
        self.Sero_table = pd.read_html(StringIO(str(soup)))[0]
        
        if len(self.Sero_table) > 0 and self.pcr_positive != "Yes":
            first = self.Sero_table["Serology Test Type"].values[0]
            row = 1 if first and str(first).endswith("IgM") else 0
            self.serology_test_type = self.Sero_table["Serology Test Type"].values[row]
            if any(pd.isnull(self.Sero_table["Serology Collection Date"].values)):
                self.issues.append('Patient has a reported serology test, but the collection date is not listed.')
                print(f"serology_collection_date: {self.Sero_table["Serology Collection Date"].values}")
            else:
                collectionDate = self.Sero_table["Serology Collection Date"].values[0] if self.Sero_table["Serology Collection Date"].values[0] != "No Date" else self.Sero_table["Serology Collection Date"].values[1]
                self.serology_collection_date = pd.to_datetime(collectionDate).date() or None
                if self.collection_date and self.collection_date != "No Date" and self.collection_date != self.serology_collection_date:
                    self.issues.append(f"lab collection date {self.collection_date} doesn't match serology collection date{self.serology_collection_date}")
            if any(pd.isnull(self.Sero_table["Serology Test Type"].values)):
                self.issues.append('Patient has a reported serology test, but the test type is not listed.')
                print(f"serology_test_type: {self.Sero_table["Serology Test Type"].values}")
            if any(pd.isnull(self.Sero_table["Serology Positive?"].values)): #possible issue
                self.issues.append('Patient has a reported serology test, but the result is not listed as positive or negative.')
                print(f"serology_positive: {self.Sero_table["Serology Positive?"].values}")
            # if len(self.Sero_table) < 2:
            seroTiter = self.Sero_table["Titer Value"].apply(lambda x: float(x.split(":")[1]) if ":" in str(x) else float(str(x).replace("<", "").replace(">", "")))
            print("titer_values", self.titer_value, seroTiter.values[row])
            # compareTiter = int(self.titer_value) if (self.titer_value).is_integer() else self.titer_value
            if self.titer_value and all(seroTiter != float(self.titer_value)):
                self.issues.append(f'IgG titer value ({self.Sero_table["Titer Value"].values[row]}) does not match lab report ({self.titer_value}).')
                print(f"Titer values: {self.Sero_table["Titer Value"].values[row]} - {self.titer_value}")
                if seroTiter.values[row]:
                    self.titer_value = seroTiter.values[row]
                    # self.lab_is_serology = True
                
            elif not self.titer_value and self.Sero_table["Titer Value"].values[row]:
                self.titer_value = seroTiter.values[row]
                if self.reporting_organization != 'MDLAB':
                    self.issues.append("Titer value in lab report is missing but, Serology test isn't.")

            if re.search(r"[<:]+", str(self.Sero_table["Titer Value"].values[row])):
                self.issues.append("Serology titer value should only have actual titer value, not ratio.")
        elif (self.pcr_positive == "Yes" or self.pcr_done == "Yes") and self.lab_is_serology and len(self.Sero_table) < 1:
            self.issues.append("Investigation says PCR but lab is serology.")

        elif self.lab_is_serology and len(self.Sero_table) < 1:
            self.issues.append("serology information not entered in investigation.")

    def CheckOtherDiagnosticTest(self):
        """ Check for follow-up tests """
        self.other_diagnostic_test = self.ReadText('//*[@id="ME24148"]')
        print(f"Other diagnostic test: {self.other_diagnostic_test}")
        self.pcr_done = self.ReadText('//*[@id="ME24175"]')
        self.pcr_positive = self.ReadText('//*[@id="ME24149"]')
        self.morulae_visualization_done = self.ReadText('//*[@id="ME24176"]')
        immunostain_done = self.ReadText('//*[@id="ME24177"]')
        culture_done = self.ReadText('//*[@id="ME24178"]')
        tests = [self.pcr_done, self.morulae_visualization_done, immunostain_done, culture_done]

        if self.other_diagnostic_test not in ["Yes", "No"] and any(test == "Yes" for test in tests):
            self.issues.append("“Other Diagnostic Test” field blank – should be Yes or No.")
        if self.other_diagnostic_test == "Yes" and not any(test == "Yes" for test in tests):
            self.issues.append('Other diagnostic test is answered Yes, but there is no other diagnostic test associated with the investigation.')
            print(f"Other diagnostic test: {self.other_diagnostic_test}")
        else:
            self.follow_up_tests = True

    def CheckLabReports(self):
        """ Pull lab reports from supplemental tab. """
        #Lab report info is only displayed if you click on the button after tick-borne. There could be more than one.
        html = self.find_element(By.XPATH, '//*[@id="eventLabReport"]').get_attribute('outerHTML')
        soup = BeautifulSoup(html, 'html.parser')
        self.Lab_report_table = pd.read_html(StringIO(str(soup)))[0]
        if len(self.Lab_report_table) > 0 and self.Lab_report_table.iloc[0, 0] != "Nothing found to display.":
            self.Lab_report_table = self.Lab_report_table[self.Lab_report_table["Test Results"].str.contains("IgG")]
            self.pcr_table = self.Lab_report_table[self.Lab_report_table["Test Results"].str.contains("DNA")]
            self.negative_lab_result = self.Lab_report_table["Test Results"].str.contains("Negative", na=False).any()
            if len(self.Lab_report_table) > 0:
                self.lab_is_serology = True

            if len(self.Lab_report_table) > 0:
                self.earliest_date_received = pd.to_datetime(self.Lab_report_table["Date Received"], format="%m/%d/%Y %I:%M %p").min().date()
                self.latest_date_received = pd.to_datetime(self.Lab_report_table["Date Received"], format="%m/%d/%Y %I:%M %p").max().date()
                
                # Filter out "No Date" entries and find the earliest specimen collection date
                valid_dates = self.Lab_report_table[self.Lab_report_table["Date Collected"] != "No Date"]["Date Collected"]
                if len(valid_dates) > 0:
                    self.collection_date = pd.to_datetime(valid_dates).min().date()
                else:
                    self.collection_date = None
                
                if not self.collection_date or self.collection_date == "No Date":
                    self.issues.append("Missing collection date.")
                    
                    if any("No Date" in str(date) and "2025" in str(date) for date in self.Lab_report_table["Date Collected"].values):
                        self.issues.append()
                
                # print("value", self.Lab_report_table["Test Results"].values[0])
                # initial_value = re.findall(r"\d+", self.Lab_report_table["Test Results"].values[0])
                # first_match = next(
                #     (re.findall(r"\d+", str(v))[0] for v in self.Lab_report_table["Test Results"] if re.findall(r"\d+", str(v))),
                #     None
                # )
                for value in self.Lab_report_table["Test Results"]:
                    matches = re.findall(r"\d+", str(value))
                    if matches:
                        self.titer_value = float(matches[1] if len(matches) > 1 else matches[0])
                        break
                else:
                    self.titer_value = None
                print("initial", self.titer_value)
            # if first_match:
            #     self.titer_value = int(first_match[1] if len(first_match) > 1 else first_match[0]).__round__()
            # else:
            #     self.titer_value = None
            self.find_element(By.XPATH, '//*[@id="eventLabReport"]/tbody/tr[1]/td[1]/a').click()
            self.lab_specimen_collection_date = self.ReadDate('//*[@id="LAB163"]')
            self.lab_report_date = self.ReadDate('//*[@id="NBS_LAB197"]')
            print(f"lab specimen collection date {self.lab_specimen_collection_date} report date {self.lab_report_date}")
            self.find_element(By.XPATH, '(//div[contains(@class, "returnToPageLink")]//a)[1]').click()
            self.returned_by_link = True
        else:
            self.issues.append('Put serology as positive - no values in lab report')

    def CheckMmwrWeekAna(self):
        """ MMWR week must be provided."""
        mmwr_week = self.CheckForValue( '//*[@id="INV165"]', "MMWR Week is blank.")
        if self.collection_date and mmwr_week and mmwr_week != f'{self.collection_date.isocalendar().week:02}':
            self.issues.append(f'“MMWR Week” field should be “{self.collection_date.isocalendar().week:02}” based on collection date of {self.collection_date}.')

    def CheckMmwrYearAna(self):
        """ MMWR year must be provided."""
        mmwr_year = self.CheckForValue( '//*[@id="INV166"]', "MMWR Year is blank.")
        if self.collection_date and mmwr_year and mmwr_year != f'{self.collection_date.isocalendar().year}':
            self.issues.append(f'“MMWR Year” field should be “{self.collection_date.isocalendar().year}” based on collection date of {self.collection_date}.')

    def CheckDiagnosisDate(self):
        diagnosis_date = self.ReadText('//*[@id="INV136"]')

        # if not diagnosis_date:
        #     self.issues.append('Diagnosis date should be same as collection date.')
        # print('date', diagnosis_date, self.collection_date)
        # if diagnosis_date and datetime.strptime(diagnosis_date, "%m/%d/%Y").date() != self.earliest_date_received:
        #     print("report date", self.earliest_date_received)
        #     self.issues.append(f'Diagnosis date {diagnosis_date} should be same as date received {self.earliest_date_received},')
        #     print("report date", self.earliest_date_received)

    def CheckClinicallyCompatible(self):
        """ Check if a patient is clinically compatible and make sure they have the correct case status. """
        self.ClinicCompIndicator = self.ReadText('//*[@id="ME12174"]')
        # self.CaseStatus = self.ReadText('//*[@id="INV163"]')
        # if self.CaseStatus == "Confirmed" and (self.ClinicCompIndicator != "Yes" or self.ConfirmationMethod != "Laboratory confirmed"):
        #     self.issues.append('Patient has a confirmed case status, but is not clinically compatible or does not have a confirmatory lab.')
        # elif self.CaseStatus == "Probable" and (self.ClinicCompIndicator != "Yes" or self.ConfirmationMethod != "Laboratory report"):
        #     self.issues.append('Patient has a probable case status, but is not clinically compatible or does not only have a serology lab.')
        # elif self.CaseStatus == "Suspect" and self.ClinicCompIndicator != "Unknown":
        #     self.issues.append('Patient has a suspected case status, but does not have unknown clinically compatiblity.')
        # if not self.ConfirmationMethod:                         #new code, but may not need since function defined in covidcasereview
        #     self.issues.append('Confirmation Method is Missing')                                                     #new code
            
    def CheckIllnessLength(self):
        """ Check if a patient has an illness onset date. """
        self.IllnessOnset = self.ReadDate('//*[@id="INV137"]')
        self.IllnessEnd = self.ReadDate('//*[@id="INV138"]')
        print(f"Illness_length: {self.IllnessOnset}")
        if self.IllnessOnset and self.IllnessEnd  and self.IllnessEnd < self.IllnessOnset:
            self.issues.append('Illness end date cannot precede illness onset date.')
            print(f"Illness_length: {self.IllnessOnset}")

        if any(symptom in ['Yes', 'Unknown'] for symptom in self.symptoms_list) or self.ClinicCompIndicator in ['Unknown', 'Yes']:
            if not self.IllnessOnset and self.CaseStatus != "Suspect" and self.ClinicCompIndicator != "Unknown":
                self.issues.append('“Illness onset date” should not be blank.')
                print(f"Illness_onset: {self.IllnessOnset}")
        
        # if not self.IllnessEnd and self.discharge_date:
        #     self.issues.append("Discharge date present but no Illness end date.")

    def CheckTravelInfo(self):
        travel_outside_us = self.ReadText('//*[@id="TRAVEL10"]')
        travel_outside_maine_but_usa = self.ReadText('//*[@id="ME10116"]')
        travel_outside_county_but_maine = self.ReadText('//*[@id="ME10117"]')
        self.travel_outside_home = [travel_outside_county_but_maine, travel_outside_us, travel_outside_maine_but_usa]
        travel_location_international = self.ReadText('//*[@id="ME12107"]')
        travel_location_domestic = self.ReadText('//*[@id="ME12108"]')
        travel_county = self.ReadText('//*[@id="ME24128"]')
        self.travel_info = [travel_outside_county_but_maine, travel_outside_us, travel_outside_maine_but_usa, travel_location_domestic, travel_location_international, travel_county]
        if all(info not in ["Yes", "No", "Unknown"] for info in self.travel_info):
            self.issues.append("Missing travel information.")

    def CheckSymptoms(self):
        """ Check patient symptoms, Patient needs one if they have a DNA test or two if there have an antibody test. """
        self.ClinicCompIndicator = self.ReadText('//*[@id="ME12174"]')
        # if self.ClinicCompIndicator == 'Unknown':                                                                    #new code, this exits early without performing symptom checks if the indicator is unknown
        #     return                                                                                                      #new code
        self.Fever = self.ReadText('//*[@id="ME14101"]') #,'Fever should not be left blank.'
        #self.Rash = self.ReadText('//*[@id="ME23100"]')
        self.Headache = self.ReadText('//*[@id="ME23101"]') #,'Headache should not be left blank.'
        self.Myalgia = self.ReadText('//*[@id="ME23102"]') #,'Myalgia should not be left blank.'
        self.Anemia = self.ReadText('//*[@id="ME24118"]') #,'Anemia should not be left blank.'
        self.Leukopenia = self.ReadText('//*[@id="ME24119"]') #,'Leukopenia should not be left blank.'
        self.Thrombocytopenia = self.ReadText('//*[@id="ME24120"]') #,'Thrombocytopenia should not be left blank.'
        self.ElevatedHepaticTransaminase =  self.ReadText('//*[@id="ME24121"]') #,'Elevated Heaptic Transaminases should not be left blank.'
        #self.Eschar = self.ReadText('//*[@id="ME24125"]') #,'Eschar should not be left blank.'
        self.Chills =  self.ReadText('//*[@id="ME24126"]') #,'Sweats/Chills should not be left blank.'
        #self.Sweats = self.ReadText('//*[@id="ME24127"]')
        self.FatigueMalaise = self.ReadText('//*[@id="ME18116"]') #,'Fatigue/Malaise should not be left blank.'
        #self.ElevatedCRP = self.ReadText('//*[@id="NBS729"]') #,'CRP Interpretation should not be left blank.'
        self.ElevatedCRP = self.ReadText('//*[@id="NBS729"]')
        self.symptoms_list = [self.Fever, self.Chills, self.Headache, self.Myalgia, self.FatigueMalaise, self.Anemia, self.Leukopenia, self.Thrombocytopenia, self.ElevatedHepaticTransaminase, self.ElevatedCRP]
        if self.ClinicCompIndicator == "Yes" and all(symptom != 'Yes' and symptom != "High" for symptom in self.symptoms_list):
            self.issues.append("Clinically compatible illness is 'Yes' but no symptom is 'Yes'.")
            print(f"symptoms__clinically_compatible: {self.ClinicCompIndicator}")
        elif self.ClinicCompIndicator not in ["Yes", "No", "Unknown"] and all(symptom not in ['Yes', 'No', 'Uknown', 'High'] for symptom in self.symptoms_list):
            self.issues.append("Clinically compatible illness is blank and all symptoms are blank")
            print(f"symptoms__clinically_compatible: {self.ClinicCompIndicator}")
            

    def CheckCaseIGM(self):
        """ Check if a patient's case status matches the case definition using test type and symptoms. """
        self.CaseStatus = self.ReadText('//*[@id="INV163"]')
        self.DNATest = self.ReadText('//*[@id="ME24175"]')
        self.DNAResult = self.ReadText('//*[@id="ME24149"]')
        self.AntibodyTest = self.ReadText('//*[@id="ME24115"]')
        has_any_symptom = any(symptom in ['Yes', 'High'] for symptom in self.symptoms_list)
        has_no_symptom = all(symptom not in ['Yes', 'High'] for symptom in self.symptoms_list)
        
        titer_value = None
        # if re.search(r"NaN", str(self.Sero_table["Titer Value"])):
        #     print(f"titer: {str(self.Sero_table["Titer Value"])}")
        #     titer_value = 0
        try:
            if re.search(r":", str(self.Sero_table["Titer Value"])):
                print(f"titer1: {self.Sero_table["Titer Value"]} {self.Sero_table["Titer Value"].first()} {self.Sero_table["Titer Value"].values}")
                val = str(self.Sero_table["Titer Value"]).split("    ")[1].split(":")
                print(f"titer2: {val}")
                titer_value = Fraction(int(val[0].replace("\nName", "")), int(val[1].replace("\nName", "")))
                print(f"titer3: {titer_value}")
            else:
                titer_value = int(self.Sero_table["Titer Value"])
        except Exception as e:
            print(f"error titer_value: {str(self.Sero_table["Titer Value"])}: {str(e)}")
            titer_value = None

        if titer_value and float(titer_value) < 128:
            if self.CaseStatus != "Not a Case":
                self.issues.append("Does not meet the 'Not a Case' definition, but does not have Not a Case status.")
                self.CorrectCaseStatus = "Not a Case"
                print(f"case_status: {self.CaseStatus}")
            
        # elif self.CaseStatus == "Not a Case":
        #     print(f"case_status: {self.CaseStatus}")
        #     return
        
        elif has_any_symptom and self.CaseStatus != "Confirmed":
            self.issues.append("Meets case definition for a confirmed case but is not a confirmed case.")
            self.CorrectCaseStatus = "Confirmed"
            print(f"case_status: {self.CaseStatus}")
        
        elif self.ClinicCompIndicator == 'unknown' and self.CaseStatus != 'probable':
            self.issues.append("Clinically compatible is unknown but case status isn't probable")
            self.CorrectCaseStatus = "Probable"
            print(f"case_status: {self.CaseStatus}")

        elif (self.Fever == "Yes" and self.Headache == "Yes") or self.Myalgia == "Yes" or self.FatigueMalaise == "Yes" or self.Anemia == "Yes" or self.Leukopenia == "Yes" or self.Thrombocytopenia == "Yes" or self.ElevatedHepaticTransaminase == "Yes" or self.ElevatedCRP == "Yes":
            if self.CaseStatus != "Probable":
                self.issues.append("Meets case definition for a probable case but is not a probable case.")
                self.CorrectCaseStatus = "Probable"
                print(f"case_status: {self.CaseStatus}")
      
        elif self.DNAResult == "Yes" and self.DNATest == "Yes":
            if has_any_symptom and self.CaseStatus != "Confirmed":
                self.issues.append("Meets case definition for a confirmed case but is not a confirmed case.")
                self.CorrectCaseStatus = "Confirmed"
                print(f"case_status: {self.CaseStatus}")

            elif has_no_symptom and self.CaseStatus != "Not a Case" and self.CaseStatus != "Suspect":                                                                             #new code. changed from 'or' to 'and' statement
                self.issues.append("Does not meet the case definition, but does not have Not a Case or Suspect status.")
                self.CorrectCaseStatus = "Not a Case or  Suspect"
                print(f"case_status: {self.CaseStatus}")
                
        elif any(self.Sero_table["Serology Positive?"] == "Yes"):
            if has_no_symptom and self.CaseStatus != "Suspect":
                    self.issues.append("Does not meet the case definition, but does not have Suspect status.")
                    self.CorrectCaseStatus = "Suspect"
                    print(f"case_status: {self.CaseStatus}")
            elif self.Fever == "Yes":
                #fever should be no when seorlogy is positive ?
                if has_any_symptom and self.CaseStatus != "Probable":
                        self.issues.append("Meets case definition for a probable case but is not a probable case.")
                        self.CorrectCaseStatus = "Probable"
                        print(f"case_status: {self.CaseStatus}")
                elif has_no_symptom and self.CaseStatus != "Not a Case":
                        self.issues.append("Does not meet the case definition, but does not have Not a Case status.")
                        self.CorrectCaseStatus = "Not a Case"
                        print(f"case_status: {self.CaseStatus}")
            else:
                if self.Chills == "Yes":
                    if has_any_symptom and self.CaseStatus != "Probable":
                            self.issues.append("Meets case definition for a probable case but is not a probable case.")
                            self.CorrectCaseStatus = "Probable"
                            print(f"case_status: {self.CaseStatus}")
                    else:
                        if (self.Headache == "Yes" and self.Myalgia == "Yes") or (self.Headache == "Yes" and self.FatigueMalaise == "Yes") or (self.FatigueMalaise == "Yes" and self.Myalgia == "Yes"):
                            if self.CaseStatus != "Probable":
                                self.issues.append("Meets case definition for a probable case but is not a probable case.")
                                self.CorrectCaseStatus = "Probable"
                                print(f"case_status: {self.CaseStatus}")
                        else:
                            if self.CaseStatus != "Not a Case":
                                self.issues.append("Does not meet the case definition, but does not have Not a Case status.")
                                self.CorrectCaseStatus = "Not a Case"
                                print(f"case_status: {self.CaseStatus}")
                elif self.Chills != "Yes":
                    if self.CaseStatus != "Not a Case":
                        self.issues.append("Does not meet the case definition, but does not have Not a Case status.")
                        self.CorrectCaseStatus = "Not a Case"
                        print(f"case_status: {self.CaseStatus}")
        else:
            if self.CaseStatus != "Not a Case":
                self.issues.append("Does not meet the case definition, but does not have Not a Case status.")
                self.CorrectCaseStatus = "Not a Case"

    def CheckCaseIGG(self):
        """ Check if a patient's case status matches the case definition using test type and symptoms. """
        self.CaseStatus = self.ReadText('//*[@id="INV163"]')
        self.DNATest = self.ReadText('//*[@id="ME24175"]')
        self.DNAResult = self.ReadText('//*[@id="ME24149"]')
        self.AntibodyTest = self.ReadText('//*[@id="ME24115"]')
        has_any_symptom = any(symptom in ['Yes', 'High'] for symptom in self.symptoms_list)
        has_no_symptom = all(symptom not in ['Yes', 'High'] for symptom in self.symptoms_list)
        
        titer_value = None
        # if re.search(r"NaN", str(self.Sero_table["Titer Value"])):
        #     print(f"titer: {str(self.Sero_table["Titer Value"])}")
        #     titer_value = 0
        # try:
        #     if re.search(r":", str(self.Sero_table["Titer Value"])):
        #         print(f"titer1: {self.Sero_table["Titer Value"]} {self.Sero_table["Titer Value"].first()} {self.Sero_table["Titer Value"].values}")
        #         val = str(self.Sero_table["Titer Value"]).split("    ")[1].split(":")
        #         print(f"titer2: {val}")
        #         titer_value = Fraction(int(val[0].replace("\nName", "")), int(val[1].replace("\nName", "")))
        #         print(f"titer3: {titer_value}")
        #     else:
        #         titer_value = int(self.Sero_table["Titer Value"])
        # except Exception as e:
        #     print(f"error titer_value: {str(self.Sero_table["Titer Value"])}: {str(e)}")
        #     titer_value = None
        # if re.search(r":", str(self.Sero_table["Titer Value"])):

        if any(self.Sero_table["Titer Value"].apply(lambda x: float(x.split(":")[1]) if ":" in str(x) else float(str(x).replace("<", "").replace(">", ""))) < 128): 
        # any(self.Sero_table["Titer Value"].astype(float) < 128):
            if self.CaseStatus != "Not a Case":
                self.issues.append("Does not meet the case definition, but does not have Not a Case status.")
                self.CorrectCaseStatus = "Not a Case"
                print(f"case_status: {self.CaseStatus}")
            
        # elif self.CaseStatus == "Not a Case":
        #     print(f"case_status: {self.CaseStatus}")
        #     return
        
        elif has_any_symptom and self.CaseStatus != "Probable":
            self.issues.append("Meets case definition for a probable case but is not a probable case.")
            self.CorrectCaseStatus = "Probable"
            print(f"case_status: {self.CaseStatus}")
        
        elif self.ClinicCompIndicator == 'unknown' and self.CaseStatus != 'probable':
            self.issues.append("Clinically compatible is unknown but case status isn't probable")
            self.CorrectCaseStatus = "Probable"
            print(f"case_status: {self.CaseStatus}")

        elif (self.Fever == "Yes" and self.Headache == "Yes") or self.Myalgia == "Yes" or self.FatigueMalaise == "Yes" or self.Anemia == "Yes" or self.Leukopenia == "Yes" or self.Thrombocytopenia == "Yes" or self.ElevatedHepaticTransaminase == "Yes" or self.ElevatedCRP == "Yes":
            if self.CaseStatus != "Confirmed":
                self.issues.append("Meets case definition for a confirmed case but is not a confirmed case.")
                self.CorrectCaseStatus = "Confirmed"
                print(f"case_status: {self.CaseStatus}")
      
        elif self.DNAResult == "Yes" and self.DNATest == "Yes":
            if has_any_symptom and self.CaseStatus != "Probable":
                self.issues.append("Meets case definition for a probable case but is not a probable case.")
                self.CorrectCaseStatus = "Probable"
                print(f"case_status: {self.CaseStatus}")

            elif has_no_symptom and self.CaseStatus != "Not a Case" and self.CaseStatus != "Suspect":                                                                             #new code. changed from 'or' to 'and' statement
                self.issues.append("Does not meet the case definition, but does not have Not a Case or Suspect status.")
                self.CorrectCaseStatus = "Not a Case or  Suspect"
                print(f"case_status: {self.CaseStatus}")
                
        elif any(self.Sero_table["Serology Positive?"] == "Yes"):
            if has_no_symptom and self.CaseStatus != "Suspect":
                    self.issues.append("Does not meet the case definition, but does not have Suspect status.")
                    self.CorrectCaseStatus = "Suspect"
                    print(f"case_status: {self.CaseStatus}")
            elif self.Fever == "Yes":
                if has_any_symptom and self.CaseStatus != "Confirmed":
                        self.issues.append("Meets case definition for a confirmed case but is not a confirmed case.")
                        self.CorrectCaseStatus = "Confirmed"
                        print(f"case_status: {self.CaseStatus}")
                elif has_no_symptom and self.CaseStatus != "Not a Case":
                        self.issues.append("Does not meet the case definition, but does not have Not a Case status.")
                        self.CorrectCaseStatus = "Not a Case"
                        print(f"case_status: {self.CaseStatus} ??")
            else:
                if self.Chills == "Yes":
                    if has_any_symptom and self.CaseStatus != "Confirmed":
                            self.issues.append("Meets case definition for a confirmed case but is not a confirmed case.")
                            self.CorrectCaseStatus = "Confirmed"
                            print(f"case_status: {self.CaseStatus}")
                    else:
                        if (self.Headache == "Yes" and self.Myalgia == "Yes") or (self.Headache == "Yes" and self.FatigueMalaise == "Yes") or (self.FatigueMalaise == "Yes" and self.Myalgia == "Yes"):
                            if self.CaseStatus != "Confirmed":
                                self.issues.append("Meets case definition for a confirmed case but is not a confirmed case.")
                                self.CorrectCaseStatus = "Confirmed"
                                print(f"case_status: {self.CaseStatus}")
                        else:
                            if self.CaseStatus != "Not a Case":
                                self.issues.append("Does not meet the case definition, but does not have Not a Case status.")
                                self.CorrectCaseStatus = "Not a Case"
                                print(f"case_status: {self.CaseStatus}")
                elif self.Chills != "Yes":
                    if self.CaseStatus != "Not a Case":
                        self.issues.append("Does not meet the case definition, but does not have Not a Case status.")
                        self.CorrectCaseStatus = "Not a Case"
                        print(f"case_status: {self.CaseStatus}")
        else:
            if self.CaseStatus != "Not a Case":
                self.issues.append("Does not meet the case definition, but does not have Not a Case status.")
                self.CorrectCaseStatus = "Not a Case"

    def CheckLTF(self):
        patient_ltf = self.ReadText('//*[@id="ME64100"]')
        if patient_ltf == "No" and any(info is None for info in self.travel_info ):
            self.issues.append(" Pt not interviewed, Travel question shouldn't be blank")
            # else:
            #     self.issues.append(" Pt not interviewed.")
        
        if patient_ltf == "Unknown":
            self.issues.append("Patient lost to follow up is 'unknown'.")

        if patient_ltf == "Unknown" and self.CaseStatus in ["Confirmed", "Probable", "Not a Case", "Suspect"]:
            self.issues.append(f"LTF is unknown when case status is {self.CaseStatus}.")


    # def RejectNotification(self, n=1):
    #     """ Reject notification on first case in notification queue.
    #     To be used when issues were encountered during review of the case."""
    #     print("issues seen in reject:", self.issues)
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
    
    def SendAnaplasmaEmail(self, body, inv_id, email=None):
        message = EmailMessage()
        message.set_content(body)
        message['Subject'] = f'AnA Bot {inv_id}'
        message['From'] = self.nbsbot_email
        if email:
            message['To'] = ', '.join(["disease.reporting@maine.gov", email])
        else:
            message['To'] = ', '.join(["disease.reporting@maine.gov"])
        smtpObj = smtplib.SMTP(self.smtp_server)
        smtpObj.send_message(message)
        print('sent email', inv_id)

    def CheckJurisdiction(self):
        """Override base CheckJurisdiction to add anaplasma-specific logic for out of state cases."""
        # Call the parent class method first
        super().CheckJurisdiction()
        
        # Anaplasma-specific logic: Out of state cases should always be "Not a Case"
        if self.jurisdiction == "Out of State":
            if self.CaseStatus != "Not a Case":
                self.issues.append("Out of state cases should always be 'Not a Case' for Anaplasma.")
                self.CorrectCaseStatus = "Not a Case"
                print(f"case_status: {self.CaseStatus} - Out of State jurisdiction")

    def CheckEPI(self):
        self.investigator_name = self.ReadText('//*[@id="headerCurrentInvestigator"]')
    #     self.epi = self.ReadText('(//tr[contains(@class, "cellColor")][2]/td[3]/span[2])')
        # '(/tr[contains(@class, "cellColor")][2]/td[2]/span[1])'
