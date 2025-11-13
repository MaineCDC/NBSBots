from Base import NBSdriver
import configparser
import pyodbc
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from datetime import timedelta
from epiweeks import Week
from selenium.common.exceptions import ElementNotInteractableException,StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException,TimeoutException
from time import sleep
import dask.dataframe as dd

class Audrey(NBSdriver):
    """ A class inherits all basic NBS functionality from NBSdriver and adds
    methods for reviewing unassigned COVID labs."""

    def __init__(self, production=False):
        super().__init__(production)
        self.reset()
        self.get_main_window_handle()
        self.incomplete_address_log = []
        self.failed_immpact_query_log = []
        self.unambigous_races = ['American Indian or Alaska Native'
                                  ,'Asian'
                                  ,'Black or African American'
                                  ,'Native Hawaiian or Other Pacific Islander'
                                  ,'White']
        # The xpaths are set here because they are required by multiple methods. This creates one maintenance point in the event of future change.
        self.unambiguous_race_paths = ['//*[@id="NBS_UI_9"]/tbody/tr[2]/td[2]/input'
                                      ,'//*[@id="NBS_UI_9"]/tbody/tr[3]/td[2]/input'
                                      ,'//*[@id="NBS_UI_9"]/tbody/tr[4]/td[2]/input'
                                      ,'//*[@id="NBS_UI_9"]/tbody/tr[5]/td[2]/input'
                                      ,'//*[@id="NBS_UI_9"]/tbody/tr[6]/td[2]/input']
        self.ethnicity_path = '//*[@id="NBS_UI_9"]/tbody/tr[1]/td[2]/input'
        self.street_path = '//*[@id="DEM159"]'
        self.city_path = '//*[@id="DEM161"]'
        self.zip_path = '//*[@id="DEM163"]'
        self.county_path = '//*[@id="NBS_UI_15"]/tbody/tr[6]/td[2]/input'

    def reset(self):
        """ Clear values of attributes assigned during case investigation review.
        To be used on initialization and between case reviews. """

        self.now = datetime.now().date()
        self.now_str = today = self.now.strftime('%m/%d/%Y')
        self.address_complete = None
        self.existing_investigation_index = None
        self.vax_table = None
        self.covid_vaccinations = None
        self.fully_vaccinated = None
        self.num_doses_prior_to_onset = None
        self.last_dose_date = None
        self.current_collection_date = None
        self.street = None
        self.city = None
        self.county = None
        self.zip_code = None
        self.unambiguous_race = None
        self.ethnicity = None
        self.demo_address = None
        self.demo_race = None
        self.demo_ethnicity = None
        self.investigation_id = None
        self.patient_id = None 
        self.new_window_handle = None
        self.multiple_possible_patients_in_immpact = False

    def get_db_connection_info(self):
        """ Read information required to connect to the NBS database."""
        self.nbs_db_driver = self.config.get('NBSdb', 'driver')
        self.nbs_db_server = self.config.get('NBSdb', 'server')
        self.nbs_rdb_name = self.config.get('NBSdb', 'rdb')
        self.nbs_db_username = self.config.get('NBSdb', 'username')
        self.nbs_db_pwd = self.config.get('NBSdb', 'pwd')
        self.nbs_odse_name = self.config.get('NBSdb', 'odse')
        self.nbs_unassigned_covid_lab_table = self.config.get('NBSdb', 'unassigned_covid_lab_table')
        self.nbs_patient_list_view = self.config.get('NBSdb', 'patient_list_view')

    def get_patient_table(self):
        """ Execute a view in the nbs_odse database to return all patients in
        NBS including firt name, last name, birth date, and parent id. This data
        is then stored in a DataFrame for future use."""

        # Connect to database
        print(f'RETRIEVE NBS PATIENT LIST:\nConnecting to {self.nbs_odse_name} database...')
        connectionString = f"DRIVER={{{ self.nbs_db_driver }}}; SERVER={self.nbs_db_server}; DATABASE={self.nbs_odse_name}; UID={self.nbs_db_username}; PWD={self.nbs_db_pwd}; TrustServerCertificate=yes"
        print(f"cstring: {connectionString}")
        Connection = pyodbc.connect(connectionString)
        # "Driver={" + self.nbs_db_driver + "};"
        #                       f"Server={self.nbs_db_server};"
        #                       f"Database={self.nbs_odse_name};"
        #                       "Trusted_Connection=yes;"
        # Execute query and close connection
        print (f'Connected to {self.nbs_odse_name}. Executing query...')
        query = f"SELECT PERSON_PARENT_UID, UPPER(FIRST_NM) AS FIRST_NM, UPPER(LAST_NM) AS LAST_NM, BIRTH_DT FROM {self.nbs_patient_list_view} WHERE (FIRST_NM IS NOT NULL) AND (LAST_NM IS NOT NULL) AND (BIRTH_DT IS NOT NULL) AND (RECORD_STATUS_CD = 'ACTIVE')"
        self.patient_list = pd.read_sql_query(query, Connection)
        self.patient_list = self.patient_list.drop_duplicates(ignore_index=True)
        Connection.close()
        print ('Data recieved and database connection closed.')
        
        
    def write_general_comment(self, note):
        """Write a note in the general comments box of an investigation."""
        xpath = '//*[@id="INV167"]'
        self.find_element(By.XPATH, xpath).send_keys(note)

    def get_unassigned_covid_labs(self):
        """ Connect to the analyis NBS database and execute a query to return a
        list of all unassociated labs along with the data required to create
        investigations for them.
        """
        self.select_counties()
        self.select_min_delay()
        self.get_age_range()
        self.select_aoe_filters()
        self.get_db_connection_info()
        variables = ('Lab_Local_ID'
                        ,'CAST(Lab_Rpt_Received_By_PH_Dt AS DATE) AS Lab_Rpt_Received_By_PH_Dt'
                        ,'CAST(Specimen_Coll_DT AS DATE) AS Specimen_Coll_DT'
                        ,'Perform_Facility_Name'
                        ,'UPPER(First_Name) AS First_Name'
                        ,'UPPER(Middle_Name) AS Middle_Name'
                        ,'UPPER(Last_Name) AS Last_Name'
                        ,'Patient_Local_ID'
                        ,'Current_Sex_Cd'
                        ,'CAST(Birth_Dt AS DATE) AS Birth_Dt'
                        ,'Patient_Race_Calc'
                        ,"CASE WHEN Patient_Ethnicity = '2186-5' THEN 'Hispanic or Latino' "
                        "WHEN Patient_Ethnicity = '2135-2' THEN 'Not Hispanic or Latino' "
                        "ELSE 'Unknown' END AS Patient_Ethnicity"
                        ,'Patient_Death_Ind'
                        ,'Patient_Death_Date'
                        ,'Phone_Number'
                        ,'Address_One'
                        ,'Address_Two'
                        ,'City'
                        ,'State'
                        ,'County_Desc'
                        ,'Jurisdiction_Nm'
                        ,'EMPLOYED_IN_HEALTHCARE'
                        ,'HOSPITALIZED'
                        ,'PATIENT_AGE'
                        ,'PREGNANT'
                        ,'RESIDENT_CONGREGATE_SETTING'
                        ,'SYMPTOMATIC_FOR_DISEASE'
                        ,"CASE WHEN ILLNESS_ONSET_DATE LIKE '[0-9][0-9][/-][0-9][0-9][/-][0-9][0-9][0-9][0-9]' THEN CAST(ILLNESS_ONSET_DATE AS DATE) "
		                "WHEN ILLNESS_ONSET_DATE LIKE '[0-9][0-9][0-9][0-9][/-][0-9][0-9][/-][0-9][0-9]' THEN CAST(ILLNESS_ONSET_DATE AS DATE) "
		                "WHEN ILLNESS_ONSET_DATE LIKE '[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]' THEN CAST(ILLNESS_ONSET_DATE AS DATE) "
		                "ELSE NULL END AS ILLNESS_ONSET_DATE"
                        ,'FIRST_RESPONDER'
                        ,'TestType'
                        ,'DATEDIFF(DAY, CAST(Specimen_Coll_DT AS DATE), GETDATE()) AS review_delay'
                        )
        variables = ', '.join(variables)
        # If a lab is not positive an investigation should not be created for it.
        # All cases with AOEs indicating hospitalization, or death should be assigned out for investigation. These cases should not be opened and closed.
        where = "WHERE (Result_Category = 'Positive') AND (State = 'ME') AND (TestType IN ('PCR', 'Antigen')) AND (HOSPITALIZED IS NULL OR UPPER(HOSPITALIZED) NOT LIKE 'Y%') AND (ICU IS NULL OR UPPER(ICU) NOT LIKE 'Y%') AND (Patient_Death_Ind IS NULL OR UPPER(Patient_Death_Ind) NOT LIKE 'Y%')"
        if self.min_delay:
            where = where + f' AND (DATEDIFF(DAY, Specimen_Coll_DT ,GETDATE())) >= {self.min_delay}'
        where = where + f' AND (DATEDIFF(DAY, CAST(Birth_Dt AS DATE), CAST(Specimen_Coll_DT AS DATE))/365.25 > {self.min_age})'
        where = where + f' AND (DATEDIFF(DAY, CAST(Birth_Dt AS DATE), CAST(Specimen_Coll_DT AS DATE))/365.25 < {self.max_age})'
        if self.cong_aoe_lab == '1':
            where = where + " AND (RESIDENT_CONGREGATE_SETTING IS NULL OR UPPER(RESIDENT_CONGREGATE_SETTING) NOT LIKE 'Y%')"
        if self.hcw_aoe_lab == '1':
            where = where + " AND (EMPLOYED_IN_HEALTHCARE IS NULL OR UPPER(EMPLOYED_IN_HEALTHCARE) NOT LIKE 'Y%')"
        if self.responder_aoe_lab == '1':
            where = where + " AND (FIRST_RESPONDER IS NULL OR UPPER(FIRST_RESPONDER) NOT LIKE 'Y%')"
        if self.pregnant_aoe_lab == '1':
            where = where + " AND (PREGNANT IS NULL OR UPPER(PREGNANT) NOT LIKE 'Y%')"
        order_by = 'ORDER BY Specimen_Coll_DT'
        # Construct Query
        query = " ".join(['SELECT', variables, 'FROM', self.nbs_unassigned_covid_lab_table, where, order_by] )
        # Connect to database
        print(f'RETRIEVE UNASSOCIATED LAB LIST:\nConnecting to {self.nbs_rdb_name} database...')
        Connection = pyodbc.connect("Driver={" + self.nbs_db_driver + "};"
                              fr"Server={self.nbs_db_server};"
                              f"Database={self.nbs_rdb_name};"
                              "Trusted_Connection=yes;")
        # Execute query and close connection
        print (f'Connected to {self.nbs_rdb_name}. Executing query...')
        self.unassociated_labs = pd.read_sql_query(query, Connection)
        self.unassociated_labs.County_Desc = self.unassociated_labs.County_Desc.str.replace(' County', '')
        Connection.close()
        if self.counties:
            self.unassociated_labs = self.unassociated_labs[self.unassociated_labs.Jurisdiction_Nm.isin(self.counties)].reset_index(drop=True)
        self.unassociated_labs.Patient_Local_ID = self.unassociated_labs.Patient_Local_ID.apply(self.clean_patient_id)
        print ('Data recieved and database connection closed.')

    def select_counties(self):
        """A method to prompt the user to specify which counties unassociated labs should be review from."""
        maine_counties = ('Androscoggin'
                        ,'Aroostook'
                        ,'Cumberland'
                        ,'Franklin'
                        ,'Hancock'
                        ,'Kennebec'
                        ,'Knox'
                        ,'Lincoln'
                        ,'Oxford'
                        ,'Penobscot'
                        ,'Piscataquis'
                        ,'Sagadahoc'
                        ,'Somerset'
                        ,'Waldo'
                        ,'Washington'
                        ,'York')
        for idx, county in enumerate(maine_counties):
            print(f'{idx}: {county}')
        self.counties = input('COUNTY SLECTION:\n'
                                'Choose the counties from which to review unassocated labs.\n'
                                'Make your selection by entering the row numbers of the desired counties separated by commas.\n'
                                'For example, to select Cumberland and York counties enter "2,15".\n'
                                'Press enter to skip this step and review unassociated labs from all counties.\n'
                                '>>>')
        if self.counties:
            self.counties = self.counties.split(',')
            self.counties = [maine_counties[int(county)]for county in self.counties]

    def select_min_delay(self):
        """A method to prompt the user to specify the minimum delay in reviewing unassociated labs.
        If 3 is select then NBSbot will only review unassocated labs that were reported 3 or more days ago."""

        self.min_delay = input('\nSET MINIMUM REVIEW DELAY:\n'
                                'Enter the minimum integer number of days between the date a lab was collected and today that unassociated labs should be reviewed from.\n'
                                'Enter "0" or simply press enter to skip this step and review all unassociated labs regardless of review delay.\n'
                                '>>>')
        if not self.min_delay:
            self.min_delay = 0
        else:
            self.min_delay = int(self.min_delay)

    def get_age_range(self):
        """Prompt user to provide the minimum and maximum patient age of unassociated labs to be opened and closed."""
        default_min = '-5'
        default_max = '150'
        self.min_age = input('\nSET MINIMUM AGE:\n'
                             'Enter the minimum age in years that cases should be opened and closed for.\n'
                             f'If no age is specified the minimum value will be set to {default_min} years.\n'
                             '>>>')
        self.max_age = input('\nSET MAXIMUM AGE:\n'
                             'Enter the maximum age in years that cases should be opened and closed for.\n'
                             f'If no age is specified the maximum value will be set to {default_max} years.\n'
                             '>>>')
        if not self.min_age:
            self.min_age = default_min
        if not self.max_age:
            self.max_age = default_max

    def select_aoe_filters(self):
        """Prompt user to decide if they would like to filter out unassociated las on the basis of affirmative AOE respones."""
        self.cong_aoe_lab = input('\nSET CONGREGATE AOE FILTER:\n'
                             '0: Review unassociated labs with an affirmative congregate setting AOE response.\n'
                             '1: DO NOT review unassociated labs with an affirmative congregate setting AOE response.\n'
                             'To review labs with an affirmative congregte setting AOE response enter "0" or simply press enter.\n'
                             'If you would NOT like to review unassociated labs with an affirmative congregate setting AOE enter "1".\n'
                             '>>>')
        self.hcw_aoe_lab = input('\nSET HEALTHCARE WORKER AOE FILTER:\n'
                             '0: Review unassociated labs with an affirmative heathcare worker AOE response.\n'
                             '1: DO NOT review unassociated labs with an affirmative healthcare worker AOE response.\n'
                             'To review labs with an affirmative healthcare worker AOE response enter "0" or simply press enter.\n'
                             'If you would NOT like to review unassociated labs with an affirmative healthcare worker AOE enter "1".\n'
                             '>>>')
        self.responder_aoe_lab = input('\nSET FIRST RESPONDER AOE FILTER:\n'
                             '0: Review unassociated labs with an affirmative first responder AOE response.\n'
                             '1: DO NOT review unassociated labs with an affirmative frist responder AOE response.\n'
                             'To review labs with an affirmative first responder AOE response enter "0" or simply press enter.\n'
                             'If you would NOT like to review unassociated labs with an affirmative first responder AOE enter "1".\n'
                             '>>>')
        self.pregnant_aoe_lab = input('\nSET PREGNANT AOE FILTER:\n'
                             '0: Review unassociated labs with an affirmative congregate setting AOE response.\n'
                             '1: DO NOT  Review unassociated labs with an affirmative congregate setting AOE response.\n'
                             'To review labs with an affirmative congregte setting AOE response enter "0" or simply press enter.\n'
                             'If you would NOT like to review unassociated labs with an affirmative congregate setting AOE enter "1".\n'
                             '>>>')

    def check_for_possible_merges(self, fname, lname, dob):
        """ Given a patient's first name, last name, and dob search for possible
        matches amoung all patients in NBS."""
        matches = self.patient_list.loc[(self.patient_list.FIRST_NM.str[:2] == fname[:2]) & (self.patient_list.LAST_NM.str[:2] == lname[:2]) & (self.patient_list.BIRTH_DT == dob)]
        unique_profiles = matches.PERSON_PARENT_UID.unique()
        if len(unique_profiles) >= 2:
            possible_merges = True
        else:
            possible_merges = False
        return possible_merges

    def check_patient_hospitalization_status(self):
        """ Check Patient Status at Specimen Collection from inside a lab report.
        Occasionally there are cases that indicate a status of 'inpatient' without an AOE inidicating a hospitalization.
        In this case the bot will not open and closed a case, but instead leave the lab for human review."""
        patient_status_path = '//*[@id="NBS_LAB330"]'
        patient_status = self.ReadText(patient_status_path).upper()
        if patient_status in ['HOSPITALIZED', 'INPATIENT']:
            possible_hospitalization = True
        else:
            possible_hospitalization = False
        return possible_hospitalization

    def check_for_existing_investigation(self, collection_date):
        """ Review the Investigations table in the Events tab of a patient profile
        to determine if the case already has an existing investigation. """
        investigation_table = self.read_investigation_table()
        if type(investigation_table) == pd.core.frame.DataFrame:
            investigation_table['days_prior'] = investigation_table['Start Date'].apply(lambda x: (collection_date - x.date()).days)
            existing_investigations = investigation_table[(investigation_table.days_prior <= 90)
                                    & (investigation_table.days_prior >= -35)
                                    & (investigation_table.Condition == '2019 Novel Coronavirus (2019-nCoV)')]
            if len(existing_investigations) >= 1:
                self.existing_investigation_index = existing_investigations.index.tolist()[0]
                self.existing_investigation_index = int(self.existing_investigation_index) + 1
                inv_found = True
                if len(existing_investigations.loc[existing_investigations['Case Status'] == 'Not a Case']) > 0:
                    existing_not_a_case = True
                else:
                    existing_not_a_case = False
            else:
                self.existing_investigation_index = None
                inv_found = False
                existing_not_a_case = False
        else:
            inv_found = False
            existing_not_a_case = False
        return inv_found, existing_not_a_case

    def create_investigation(self):
        """Create a new investigation from within a lab report when one does not already exist ."""
        create_investigation_button_path = '//*[@id="doc3"]/div[2]/table/tbody/tr/td[2]/input[1]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, create_investigation_button_path)))
        self.find_element(By.XPATH, create_investigation_button_path).click()
        select_condition_field_path = '//*[@id="ccd_ac_table"]/tbody/tr[1]/td/input'
        condition = '2019 Novel Coronavirus (2019-nCoV)'
        WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, select_condition_field_path)))
        self.find_element(By.XPATH, select_condition_field_path).send_keys(condition)
        submit_button_path = '/html/body/table/tbody/tr/td/table/tbody/tr[3]/td/table/thead/tr[2]/td/div/table/tbody/tr/td/table/tbody/tr/td[4]/table[1]/tbody/tr[1]/td/input'
        WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, submit_button_path)))
        self.find_element(By.XPATH, submit_button_path).click()

    def associate_lab_with_investigation(self, lab_id):
        """Associate a lab with an existing investigation when one for the case has already been started."""
        lab_report_table_path = '//*[@id="events1"]'
        lab_report_table = self.ReadTableToDF(lab_report_table_path)
        if len(lab_report_table) > 1:
            lab_row_index = lab_report_table[lab_report_table['Event ID'] == lab_id].index.tolist()[0]
            lab_row_index = str(int(lab_row_index) + 1)
            lab_path = f'/html/body/div[2]/div/form/div/div/div/table[2]/tbody/tr/td/table/tbody/tr[{lab_row_index}]/td[1]/div/input'
        WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, lab_path)))
        self.find_element(By.XPATH,lab_path).click()

    def query_immpact(self):
        """ Click the query registry button, submit the query to immpact, and read the results into a DataFrame."""
        query_registry_button = '//*[@id="events3"]/tbody/tr/td/div/input[1]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.element_to_be_clickable((By.XPATH, query_registry_button)))
        self.find_element(By.XPATH, query_registry_button).click()
        self.switch_to_secondary_window()
        submit_query = '//*[@id="doc4"]/div[2]/input[1]'
        self.find_element(By.XPATH, submit_query).click()
        self.switch_to_secondary_window()
        results_table_path = '//*[@id="section1"]/div/table'
        results_table = self.ReadTableToDF(results_table_path)
        if (len(results_table) == 1) & (results_table['Patient Name'][0] != 'Nothing found to display.'):
            record_path = '//*[@id="parent"]/tbody/tr/td[1]/a'
            self.find_element(By.XPATH, record_path).click()
            self.switch_to_secondary_window()
            vax_table_path = '//*[@id="section1"]/div/table[2]'
            self.vax_table = self.ReadTableToDF(vax_table_path)
            good_query = True
        else:
            good_query = False
            print('Immpact returned more than one patient as a possible, or found no matching patients. Unable to proceed with the automated query.')
            cancel_path = '/html/body/form/div[2]/div/div[1]/input'
            self.find_element(By.XPATH, cancel_path).click()
            self.switch_to.alert.accept()
            if len(results_table) > 1:
                self.multiple_possible_patients_in_immpact = True
        return good_query

    def id_covid_vaccinations(self):
        """Identify COVID vaccines by their specific brand."""
        covid_vax_dict = {'Pfizer':'COVID-19, mRNA, LNP-S, PF, 30 mcg/0.3 mL dose'
                        ,'Moderna':'COVID-19, mRNA, LNP-S, PF, 100 mcg/ 0.5 mL dose'
                        ,'JJ':'COVID-19 vaccine, vector-nr, rS-Ad26, PF, 0.5 mL'
                        ,'Pfizer_5to12': 'Tris-sucrose formula, 10 mcg/0.2 mL for ages 5 yrs to < 12 yrs'}
        for key in covid_vax_dict.keys():
            self.vax_table[key] = self.vax_table['Vaccine Administered'].apply(lambda x: covid_vax_dict[key] in x)
        self.covid_vaccinations = self.vax_table.loc[self.vax_table.Pfizer | self.vax_table.Moderna | self.vax_table.JJ | self.vax_table.Pfizer_5to12]
        #self.covid_vaccinations['Date Administered'] = pd.to_datetime(self.covid_vaccinations['Date Administered'])
        #self.covid_vaccinations['Date Administered'] = self.covid_vaccinations['Date Administered'].dt.date
        self.covid_vaccinations.loc[self.covid_vaccinations['Date Administered'].notna(), 'Date Administered'] = pd.to_datetime(self.covid_vaccinations['Date Administered']).dt.date

    def import_covid_vaccinations(self):
        """ Select all COVID vaccinations in the list returned by Immpact and import them."""
        covid_vax_indexes = self.covid_vaccinations.index + 1
        num_covid_vaccinations = len(covid_vax_indexes)
        if num_covid_vaccinations > 0:
            if (len(self.vax_table) == 1) & (len(covid_vax_indexes) == 1):
                select_path = '/html/body/form/div[2]/div/div[4]/div/table[2]/tbody/tr/td/table/tbody/tr/td[1]/input'
                self.find_element(By.XPATH, select_path).click()
            else:
                for idx in covid_vax_indexes:
                    select_path = f'/html/body/form/div[2]/div/div[4]/div/table[2]/tbody/tr/td/table/tbody/tr[{idx}]/td[1]/input'
                    self.find_element(By.XPATH, select_path).click()
            import_path = '/html/body/form/div[2]/div/div[1]/input[1]'
            self.find_element(By.XPATH, import_path).click()
            self.switch_to.alert.accept()
            if len(self.window_handles) > 1:
                for handle in self.window_handles:
                    if handle != self.main_window_handle:
                        self.switch_to.window(handle)
                        self.close()
                self.switch_to.window(self.main_window_handle)
                self.failed_immpact_query_log.append(self.patient_id)
        else:
            cancel_path = '/html/body/form/div[2]/div/div[1]/input[2]'
            self.find_element(By.XPATH, cancel_path).click()
            self.switch_to.alert.accept()


    def determine_vaccination_status(self, collection_date):
        """ Determine vaccination status at time of illness and other required vaccination data points."""
        covid_vaccinations_prior_to_onset = self.covid_vaccinations.loc[self.covid_vaccinations['Date Administered'] < collection_date ]
        self.num_doses_prior_to_onset = len(covid_vaccinations_prior_to_onset)
        self.last_dose_date = covid_vaccinations_prior_to_onset['Date Administered'].max()
        complete_vaccinations = self.covid_vaccinations.loc[self.covid_vaccinations['Date Administered'] <= (collection_date - timedelta(days=14))]
        if len(complete_vaccinations.loc[complete_vaccinations.Pfizer]) >= 2:
            self.fully_vaccinated = True
        elif len(complete_vaccinations.loc[complete_vaccinations.Moderna]) >= 2:
            self.fully_vaccinated = True
        elif len(complete_vaccinations.loc[complete_vaccinations.JJ]) >= 1:
            self.fully_vaccinated = True
        elif len(complete_vaccinations.loc[complete_vaccinations.Pfizer_5to12]) >= 2:
            self.fully_vaccinated = True
        else:
            self.full_vaccinated = False

    def read_street(self):
        """ Read the current street address."""
        try:
            self.street = self.find_element(By.XPATH, self.street_path).get_attribute('value')
        except Exception as e:
            self.street = None

    def read_city(self):
        """Read the current city/town."""
        try:
            self.city = self.find_element(By.XPATH, self.city_path).get_attribute('value')
        except Exception as e:
            self.city = None

    def read_zip(self):
        """Read the current zip code. """
        try:
            self.zip_code = self.find_element(By.XPATH, self.zip_path).get_attribute('value')
        except Exception as e:
            self.zip_code = None

    def write_zip(self):
        """Write zip code. Intended for use after looking up a missing zip code with zip_code_lookup()."""
        try:
            self.find_element(By.XPATH, self.zip_path).send_keys(self.zip_code)
        except Exception as e:
            print("")

    def read_county(self):
        """Read the current county. """
        try:
            self.county = self.find_element(By.XPATH, self.county_path).get_attribute('value')
        except Exception as e:
            self.county = None

    def write_county(self):
        """Write county. Intended for use after looking up a missing missing count with county_lookup()."""
        try:
            self.find_element(By.XPATH, self.county_path).send_keys(self.county)
        except Exception as e:
            print("")

    def read_address(self):
        """ Read parts of the patient address except for state and country."""
        self.read_street()
        self.read_city()
        self.read_zip()
        self.read_county()

    def set_state(self, state):
        """Set state value in patient address."""
        path = '//*[@id="NBS_UI_15"]/tbody/tr[4]/td[2]/input'
        self.find_element(By.XPATH, path).send_keys(Keys.CONTROL+'a')
        self.find_element(By.XPATH, path).send_keys(state)

    def set_country(self, country):
        """Set country value in patient address."""
        path = '//*[@id="NBS_UI_15"]/tbody/tr[7]/td[2]/input'
        self.find_element(By.XPATH, path).send_keys(Keys.CONTROL+'a')
        self.find_element(By.XPATH, path).send_keys(country)

    def check_ethnicity(self):
        """ Check if ethnicity is completed and if not set the values to unknown."""
        self.ethnicity = self.find_element(By.XPATH, self.ethnicity_path).get_attribute('value')
        if not self.ethnicity:
            self.find_element(By.XPATH, self.ethnicity_path).send_keys('u')

    def clear_ambiguous_race_answers(self):
        """ Ensure all ambiguous race answers (refused to answer, not answered, and unknown) are not selected."""
        ambiguous_answer_paths = ['//*[@id="NBS_UI_9"]/tbody/tr[8]/td[2]/input'
                                 ,'//*[@id="NBS_UI_9"]/tbody/tr[9]/td[2]/input'
                                 ,'//*[@id="NBS_UI_9"]/tbody/tr[10]/td[2]/input']
        for path in ambiguous_answer_paths:
            self.unselect_checkbox(path)

    def check_race(self):
        """Review current race value. If any combination of non-ambiguous options
        are selection make sure all other choice are not selected. Accept "other"
        only when no unambigious answer is present. When race is not clearly
        defined or other set value to unknown."""
        other_race_path = '//*[@id="NBS_UI_9"]/tbody/tr[7]/td[2]/input'
        unknown_race_path = '//*[@id="NBS_UI_9"]/tbody/tr[10]/td[2]/input'
        for path in self.unambiguous_race_paths:
            if self.find_element(By.XPATH, path).is_selected():
                self.unambiguous_race = True
                break
            else:
                self.unambiguous_race = False
        self.clear_ambiguous_race_answers()
        if self.unambiguous_race:
            self.unselect_checkbox(other_race_path)
        elif self.find_element(By.XPATH, other_race_path).is_selected():
            self.select_checkbox(other_race_path)
        else:
            self.find_element(By.XPATH, unknown_race_path).click()

    def read_demographic_address(self, state=''):
        """ Read address table from the demographics tab of a patient profile and
        select the most recent address from within the last year that is consistent
        with all parts of the address reported in the current lab report."""
        address_table_path = '//*[@id="patSearch8"]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, address_table_path)))
        address_table = self.ReadTableToDF(address_table_path)
        if type(address_table) != pd.core.frame.DataFrame:
            sleep(1)
            address_table = self.ReadTableToDF(address_table_path)
        address_table = address_table[address_table['As of'] != '']
        address_table['As of'] = pd.to_datetime(address_table['As of'], format = "%m/%d/%Y")
        address_table = address_table.loc[address_table['As of'].dt.date >= (self.now - timedelta(days=365))].reset_index(drop=True)
        address_table.Zip = address_table.Zip.apply(lambda x: str(int(x)).zfill(5) if type(x) == float else x )
        if self.street:
            address_table = address_table.loc[address_table.Address.str.upper() == self.street.upper()].reset_index(drop=True)
        if self.city:
            address_table = address_table.loc[address_table.City.str.upper() == self.city.upper()]
        address_table = address_table.loc[address_table.State == 'Maine'].reset_index(drop=True)
        if self.zip_code:
            address_table = address_table.loc[address_table.Zip.map(str) == self.street].reset_index(drop=True)
        if len(address_table) > 0:
            self.demo_address = address_table.reset_index(drop=True).iloc[0]

    def write_demographic_address(self):
        """ After reading an address from the demographics tab, moving back into
        an investigation, and entering edit mode, write the data to the address
        fields."""
        self.find_element(By.XPATH, self.street_path).send_keys(self.demo_address.Address)
        self.find_element(By.XPATH, self.city_path).send_keys(self.demo_address.City)
        self.find_element(By.XPATH, self.zip_path).send_keys(str(self.demo_address.Zip))
        self.find_element(By.XPATH, self.county_path).send_keys(self.demo_address.Address)

    def read_demographic_race(self):
        """Read the race table in the demographics tab and select the most recent
        nonambigous value, if present."""
        race_table_path = '//*[@id="patSearch14"]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, race_table_path)))
        race_table = self.ReadTableToDF(race_table_path)
        if type(race_table) != pd.core.frame.DataFrame:
            sleep(1)
            race_table = self.ReadTableToDF(race_table_path)
        all_race_values = race_table.Race.tolist()
        unambiguous_race_values = [x for x in all_race_values if x in self.unambigous_races]
        if unambiguous_race_values:
            self.demo_race = unambiguous_race_values[0]

    def write_demographic_race(self):
        """ After reading a race from the demographics tab, moving back into an
        investigation, and entering edit mode, write the data to the race field."""
        for race, path in zip(self.unambigous_races, self.unambiguous_race_paths):
            if race in self.demo_race:
                self.select_checkbox(path)
        self.clear_ambiguous_race_answers()

    def read_demographic_ethnicity(self):
        """Read the ethnicity table in the demographics tab and select the most
        recent non-unknown value, if present."""
        ethnicity_path = '//*[@id="NBS108"]'
        WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, ethnicity_path)))
        ethnicity = self.ReadText(ethnicity_path)
        if ethnicity in ['Hispanic or Latino', 'Not Hispanic or Latino']:
            self.demo_ethnicity = ethnicity

    def write_demographic_ethnicity(self):
        """ After reading an ethnicity from the demographics tab, moving back into an
        investigation, and entering edit mode, write the data to the ethnicity field."""
        self.find_element(By.XPATH, self.ethnicity_path).send_keys(Keys.CONTROL+'a')
        self.find_element(By.XPATH, self.ethnicity_path).send_keys(self.demo_ethnicity)

    def set_investigation_start_date(self):
        """ Set investigation start date to today."""
        start_date_path = '//*[@id="INV147"]'
        self.find_element(By.XPATH, start_date_path).send_keys(self.now_str)

    def set_investigation_status_closed(self):
        """Set investigation status to closed."""
        try:
            investigation_status_down_arrow = '//*[@id="NBS_UI_19"]/tbody/tr[4]/td[2]/img'
            closed_option = '//*[@id="INV109"]/option[1]'
            self.find_element(By.XPATH, investigation_status_down_arrow).click()
            self.find_element(By.XPATH, closed_option).click()
        except ElementNotInteractableException:
            self.GoToCaseInfo()
            self.set_investigation_status_closed()

    def set_state_case_id(self):
        """ Set the State Case ID to the NBS patient ID."""
        try:
            state_case_id_path = '//*[@id="INV173"]'
            patient_id = self.ReadPatientID()
            self.find_element(By.XPATH, state_case_id_path).send_keys(patient_id)
        except ElementNotInteractableException:
            self.GoToCaseInfo()
            self.set_state_case_id()

    def read_investigation_id(self):
        """ From within an investigation read the investigation id."""
        investigation_id_path = '/html/body/div/div/form/div[2]/div[1]/table[3]/tbody/tr[2]/td[1]/span[2]'
        self.investigation_id = self.ReadText(investigation_id_path)

    def set_county_and_state_report_dates(self, report_to_ph_date):
        """ Set Earliest Date Reported to County and Earliest Date Reported to
        State based on Lab_Rpt_Received_By_PH_Dt. This method may be used when
        creating new investigations or when associating additional labs with an
        existing investigation. In the case where there is an existing report
        date in the existing invesitigation it will only be replaced when the
        provided report date is earlier."""
        try:
            report_date_paths = ['//*[@id="INV120"]', '//*[@id="INV121"]']
            report_to_ph_date_str = report_to_ph_date.strftime('%m/%d/%Y')
            for path in report_date_paths:
                current_report_date = self.ReadDate(path, 'value')
                if current_report_date:
                    if report_to_ph_date < current_report_date:
                        self.find_element(By.XPATH, path ).send_keys(Keys.CONTROL+'a')
                        self.find_element(By.XPATH, path).send_keys(report_to_ph_date_str)
                else:
                    self.find_element(By.XPATH, path).send_keys(report_to_ph_date_str)
        except ElementNotInteractableException:
            self.GoToCaseInfo()
            self.set_county_and_state_report_dates(report_to_ph_date)

    def update_report_date(self, report_to_ph_date):
        """When associating a lab with an existing investigation check to see if
        the new lab was reported prior to the report date currently assigned to
        the investigation. If so, replace it with the report date of the new lab.
        If not, do nothing."""
        try:
            report_date_path = '//*[@id="INV111"]'
            current_report_date = self.ReadDate(report_date_path, 'value')
            report_to_ph_date_str = report_to_ph_date.strftime('%m/%d/%Y')
            if current_report_date:
                if report_to_ph_date < current_report_date:
                    self.find_element(By.XPATH, report_date_path ).send_keys(Keys.CONTROL+'a')
                    self.find_element(By.XPATH, report_date_path ).send_keys(report_to_ph_date_str)
            else:
                report_to_ph_date = report_to_ph_date.strftime('%m/%d/%Y')
                self.find_element(By.XPATH, report_date_path ).send_keys(report_to_ph_date_str)
        except ElementNotInteractableException:
            self.GoToCaseInfo()
            self.update_report_date(report_to_ph_date)

    def set_performing_lab(self, performing_lab):
        """ Set performing laboratory name based on lab report."""
        try:
            if performing_lab:
                performing_lab_path = '//*[@id="ME6105"]'
                self.find_element(By.XPATH, performing_lab_path).send_keys(performing_lab)
        except ElementNotInteractableException:
            self.GoToCaseInfo()
            self.set_performing_lab(performing_lab)


    def set_earliest_positive_collection_date(self, lab_collection_date):
        """ Read the earliest positive speciment collection date field. If there
        is a date present and it is prior to the collection of the current lab do
        nothing. In the event that the field is blank or the collection of the
        current lab is prior to the current value of the field, set the value to
        the collection date of the current lab. This additional check allows this
        method to be used when creating investigations or associating labs with
        existing investigations."""
        try:
            collection_date_path = '//*[@id="NBS550"]'
            lab_collection_date_str = lab_collection_date.strftime('%m/%d/%Y')
            self.current_collection_date = self.ReadDate(collection_date_path, 'value')
            if not self.current_collection_date:
                self.current_collection_date = lab_collection_date
                self.find_element(By.XPATH, collection_date_path).send_keys(Keys.CONTROL+'a')
                self.find_element(By.XPATH, collection_date_path).send_keys(lab_collection_date_str)
            elif lab_collection_date <= self.current_collection_date:
                self.current_collection_date = lab_collection_date
                self.find_element(By.XPATH, collection_date_path).send_keys(Keys.CONTROL+'a')
                self.find_element(By.XPATH, collection_date_path).send_keys(lab_collection_date_str)
        except ElementNotInteractableException:
            self.GoToCaseInfo()
            self.set_earliest_positive_collection_date(lab_collection_date)

    def set_case_status(self, status):
        """ Set all three fields related to case status based on the provided status."""
        current_status_path = '//*[@id="NBS_UI_GA21015"]/tbody/tr[3]/td[2]/input'
        probable_reason_path = '//*[@id="NBS_UI_GA21015"]/tbody/tr[4]/td[2]/input'
        case_status_path = '//*[@id="NBS_UI_2"]/tbody/tr[5]/td[2]/input'
        if status == 'Confirmed':
            current_status = 'Laboratory-confirmed case'
            probable_reason = ''
        elif status == 'Probable':
            current_status = 'Probable Case'
            probable_reason = 'Meets Presump Lab and Clinical or Epi'
        self.find_element(By.XPATH, current_status_path).send_keys(Keys.CONTROL+'a')
        self.find_element(By.XPATH, current_status_path).send_keys(current_status)
        self.find_element(By.XPATH, probable_reason_path).send_keys(Keys.CONTROL+'a')
        self.find_element(By.XPATH, probable_reason_path).send_keys(probable_reason)
        self.find_element(By.XPATH, case_status_path).send_keys(Keys.CONTROL+'a')
        self.find_element(By.XPATH, case_status_path).send_keys(status)

    def review_case_status(self, lab_type):
        """ Review current case status and current lab type. Then set case status
        accordingly. This method can be used for creating investigations or
        associating additional labs with existing investigations."""
        try:
            case_status_path = '//*[@id="NBS_UI_2"]/tbody/tr[5]/td[2]/input'
            current_case_status = self.ReadText(case_status_path)
            if lab_type == 'PCR':
                self.set_case_status('Confirmed')
            elif lab_type == 'Antigen':
                self.set_case_status('Probable')
        except ElementNotInteractableException:
            self.GoToCaseInfo()
            self.review_case_status(lab_type)

    def update_aoe(self, aoe_path, lab_aoe):
        """ Update a specific AOE associated investigation field by considering
        its current value and the value in the current lab. An affirmative
        response in either the investigation or the lab takes precedence, followed
        by negative, unknown, and null responses respectively."""
        try:
            if lab_aoe:
                investigation_aoe = self.ReadText(aoe_path)
                self.find_element(By.XPATH, aoe_path).send_keys(Keys.CONTROL+'a')
                if (investigation_aoe == 'Yes') | (lab_aoe[0].upper() == 'Y'):
                    self.find_element(By.XPATH, aoe_path).send_keys('Yes')
                elif (investigation_aoe == 'No') | (lab_aoe[0].upper() == 'N'):
                    self.find_element(By.XPATH, aoe_path).send_keys('No')
                elif (investigation_aoe == 'Unknown') | (lab_aoe[0].upper() == 'U'):
                    self.find_element(By.XPATH, aoe_path).send_keys('Unknown')
        except ElementNotInteractableException:
            self.GoToCaseInfo()
            self.update_aoe(aoe_path, lab_aoe, 'case_info')

    def update_case_info_aoes(self, hosp_aoe, cong_aoe, responder_aoe, hcw_aoe):
        """ Update every AOE on the Case Info tabe using the update_aoe() method."""
        aoe_dictionary = {'//*[@id="NBS_UI_NBS_INV_GENV2_UI_3"]/tbody/tr[1]/td[2]/input' : hosp_aoe
                         ,'//*[@id="ME59136"]/tbody/tr[3]/td[2]/input' : cong_aoe
                         ,'//*[@id="ME59137"]/tbody/tr[1]/td[2]/input' : responder_aoe
                         ,'//*[@id="UI_ME59106"]/tbody/tr[1]/td[2]/input' : hcw_aoe}
        for aoe_path, aoe_value in aoe_dictionary.items():
            if aoe_value:
                self.update_aoe(aoe_path, aoe_value)

    def update_pregnant_aoe(self, pregnant_aoe):
        """ Update pregnancy status AOE on COVID tab."""
        lab_aoe = pregnant_aoe
        try:
            if lab_aoe:
                aoe_path = '//*[@id="ME58100"]/tbody/tr[1]/td[2]/input'
                investigation_aoe = self.ReadText(aoe_path)
                self.find_element(By.XPATH, aoe_path).send_keys(Keys.CONTROL+'a')
                if (investigation_aoe == 'Yes') | (lab_aoe[0].upper() == 'Y'):
                    self.find_element(By.XPATH, aoe_path).send_keys('Yes')
                elif (investigation_aoe == 'No') | (lab_aoe[0].upper() == 'N'):
                    self.find_element(By.XPATH, aoe_path).send_keys('No')
                elif (investigation_aoe == 'Unknown') | (lab_aoe[0].upper() == 'U'):
                    self.find_element(By.XPATH, aoe_path).send_keys('Unknown')
        except ElementNotInteractableException:
            pass

    def update_symptom_aoe(self, lab_symptom_aoe, lab_onset_date):
        """ Update symptom status based on values in an investigation and values
        reported in the current lab."""
        symptom_path = '//*[@id="NBS_UI_GA21003"]/tbody/tr[3]/td[2]/input'
        onset_date_path = '//*[@id="INV137"]'
        investigation_symptom_status = self.ReadText(symptom_path)
        if lab_onset_date:
            lab_symptom_aoe = 'Yes'
        if lab_symptom_aoe:
            self.find_element(By.XPATH, symptom_path).send_keys(Keys.CONTROL+'a')
            if (investigation_symptom_status == 'Yes') | (lab_symptom_aoe[0].upper() == 'Y'):
                self.find_element(By.XPATH, symptom_path).send_keys(Keys.CONTROL+'a')
            elif (investigation_symptom_status == 'No') | (lab_symptom_aoe[0].upper() == 'N'):
                self.find_element(By.XPATH, symptom_path).send_keys('No')
            elif (investigation_symptom_status == 'Unknown') | (lab_symptom_aoe[0].upper() == 'U'):
                self.find_element(By.XPATH, symptom_path).send_keys('Unknown')
            if investigation_symptom_status == 'Yes':
                investigation_onset_date = self.ReadDate(onset_date_path, 'value')
                if investigation_onset_date and lab_onset_date:
                    if lab_onset_date < investigation_onset_date:
                        lab_onset_date = lab_onset_date.strftime('%m/%d/%Y')
                        self.find_element(By.XPATH, onset_date_path).send_keys(Keys.CONTROL+'a')
                        self.find_element(By.XPATH, onset_date_path).send_keys(lab_onset_date)
                elif lab_onset_date:
                    lab_onset_date = lab_onset_date.strftime('%m/%d/%Y')
                    self.find_element(By.XPATH, onset_date_path).send_keys(lab_onset_date)

    def set_confirmation_date(self):
        """Set confirmation date to today when creating a new investigation."""
        confirmation_date_path = '//*[@id="INV162"]'
        self.find_element(By.XPATH, confirmation_date_path).send_keys(self.now_str)

    def set_closed_date(self):
        """Set investigation closed date to today when creating a new investigation."""
        closed_date_path = '//*[@id="ME11163"]'
        self.find_element(By.XPATH, closed_date_path).send_keys(self.now_str)

    def set_immpact_query_to_yes(self):
        """Set the answer to the "Was ImmPact Queried?" question to yes."""
        immpact_query_path = '//*[@id="ME10064101"]/tbody/tr[9]/td[2]/input'
        self.find_element(By.XPATH, immpact_query_path).send_keys('Yes')

    def set_vaccination_fields(self):
        """Fill in all vaccination specific fields on the COVID tab after querying
        Immpact when creating a new investigation."""
        try:
            vaccinated_path = '//*[@id="ME10064101"]/tbody/tr[1]/td[2]/input'
            num_dose_path = '//*[@id="VAC140"]'
            last_dose_path = '//*[@id="VAC142"]'
            fully_vax_path = '//*[@id="ME10064101"]/tbody/tr[4]/td[2]/input'

            if len(self.covid_vaccinations) > 0:
                self.find_element(By.XPATH, vaccinated_path).send_keys(Keys.CONTROL+'a')
                self.find_element(By.XPATH, vaccinated_path).send_keys('Yes')
                self.find_element(By.XPATH, vaccinated_path).send_keys(Keys.TAB)
                num_doses = str(self.num_doses_prior_to_onset)
                self.find_element(By.XPATH, num_dose_path).send_keys(num_doses)
                try:
                    last_dose_date = self.last_dose_date.strftime('%m/%d/%Y')
                    self.find_element(By.XPATH, last_dose_path).send_keys(last_dose_date)
                except AttributeError:
                    pass
                if self.fully_vaccinated:
                    self.find_element(By.XPATH, fully_vax_path).send_keys('Yes')
        except ElementNotInteractableException:
            self.GoToCOVID()
            self.set_vaccination_fields()

    def set_lab_testing_performed(self):
        """Set the laboratory testing performed question to 'Yes' when creating
        a new investigation."""
        lab_testing_path = '//*[@id="ME58101"]/tbody/tr/td[2]/input'
        self.find_element(By.XPATH, lab_testing_path).send_keys('Yes')

    def set_mmwr(self):
        """Set the values of the MMWR week and year correctly based on first
        positive speciment collection date."""
        week_path = '//*[@id="INV165"]'
        year_path = '//*[@id="INV166"]'
        mmwr_date = Week.fromdate(self.current_collection_date)
        week = str(mmwr_date.week)
        if len(week) == 1:
            week = '0' + week
        year = str(mmwr_date.year)
        self.find_element(By.XPATH, week_path).clear()
        self.find_element(By.XPATH, week_path).send_keys(week)
        self.find_element(By.XPATH, year_path).send_keys(Keys.CONTROL+'a')
        self.find_element(By.XPATH, year_path).send_keys(year)

    def check_jurisdiction(self):
        """ After completing an investigation check if the patient's county and
        jurisdiction match. If a county is available that does not match the
        jurisdication then update the jurisdiction accordingly."""
        county_path = '//*[@id="DEM165"]'
        jurisdiction_path = '//*[@id="INV107"]|//*[@id="NBS_UI_19"]/tbody/tr[1]/td[2]/input|//*[@id="NBS_UI_19"]/tbody/tr[1]/td[2]'
        transfer_ownership_path = '/html/body/div/div/form/div[2]/div[1]/table[2]/tbody/tr/td[1]/table/tbody/tr/td[3]/input'
        new_jurisdiction_path = '//*[@id="subsect_transferOwn"]/tbody/tr[2]/td[2]/input'
        submit_jurisdiction_path = '//*[@id="topButtId"]/input[1]'
        county = self.ReadText(county_path)
        if county and (not county.isnumeric()):
            self.GoToCaseInfo()
            jurisdiction = self.ReadText(jurisdiction_path)
            if not jurisdiction:
                jurisdiction = self.ReadText('//*[@id="NBS_UI_19"]/tbody/tr[1]/td[2]')
            if jurisdiction and jurisdiction not in county:
                self.find_element(By.XPATH, transfer_ownership_path).click()
                self.switch_to_secondary_window()
                self.find_element(By.XPATH, new_jurisdiction_path).send_keys(Keys.CONTROL+'a')
                self.find_element(By.XPATH, new_jurisdiction_path).send_keys(county[0:3])
                self.find_element(By.XPATH, submit_jurisdiction_path).click()
                self.switch_to.window(self.main_window_handle)
        elif county.isnumeric():
            self.incomplete_address_log.append(self.ReadPatientID())

    def create_notification(self):
        """After completing a case create notification for it."""
        for i in range(3):
            try:
                create_button_path = '//*[@id="createNoti"]'
                WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, create_button_path)))
                self.find_element(By.XPATH,create_button_path).click()
                self.switch_to_secondary_window()
                submit_button_path = '//*[@id="botcreatenotId"]/input[1]'
                WebDriverWait(self,self.wait_before_timeout).until(EC.presence_of_element_located((By.XPATH, submit_button_path)))
                self.find_element(By.XPATH, submit_button_path).click()
                self.switch_to.window(self.main_window_handle)
                break
            except TimeoutException:
                print(f"Timeout waiting for create_notification, retry_number: {i}")
            except StaleElementReferenceException:
                print(f"StaleElementReferenceException for create_notification, trying again... retry_number: {i}")
            except NoSuchElementException:
                print(f"No create_notification found, retry_number: {i}")
            except Exception as e:
                print(f"{e} has occured for create_notification, retry_number: {i}")

    def send_bad_address_email(self):
        """Email the COVID Admin the list of patients with incomplete addresses."""
        if self.incomplete_address_log:
            body = 'Hello COVID Admin Team,\n\nThe following cases have incomplete addresses:\n\n'
            for id in self.incomplete_address_log:
                body = body + id +'\n'
            body = body + '\n-NBSbot(COVID open/close) AKA Hoover'
            self.send_smtp_email(self.covid_admin_list, 'Incomplete addresses', body, 'incomplete address email')
        else:
            print('Incomplete address log is empty. No email sent.')

    def send_failed_query_email(self):
        """Email the COVID Admin the list of patients where the Immpact query failed."""
        if self.failed_immpact_query_log:
            body = 'Hello COVID Commander,\n\nThe Immpact query for following cases failed:\n\n'
            for id in self.failed_immpact_query_log:
                body = body + id +'\n'
            body = body + '\n-NBSbot(COVID open/close) AKA Hoover'
            self.send_smtp_email(self.covid_commander, 'Failed Immpact Queries', body, 'failed query email')
        else:
            print('Failed query log is empty. No email sent.')

    def pause_for_database(self):
        """ If the time is between midnight and 0200 pause until after 0200."""
        now = datetime.now()
        stop_time = now.replace(hour = 23, minute = 55, second = 0, microsecond = 0)
        if now >= stop_time:
            print('Sleeping untill 02:05...')
            sleep(3300)
            self.go_to_home()
            sleep(3300)
            self.go_to_home()
            sleep(1200)
            self.go_to_home()

if __name__ == "__main__":
    NBS = Audrey(production=True)