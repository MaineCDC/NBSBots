from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import (
    TimeoutException,
    ElementNotInteractableException,
    NoSuchElementException,
    ElementClickInterceptedException,
    NoAlertPresentException,
    StaleElementReferenceException,
)

from webdriver_manager.chrome import ChromeDriverManager

from datetime import datetime
from fractions import Fraction
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup

import pandas as pd
import os, sys, re, time, json, configparser, smtplib, getpass

from email.message import EmailMessage
from pathlib import Path
from shutil import rmtree

import win32com.client as win32
from geopy.geocoders import Nominatim
from usps import USPSApi, Address
from io import StringIO


class NBSdriver(webdriver.Chrome):
    """A class to provide basic functionality in NBS via Selenium."""

    def __init__(self, production: bool = False, chrome_path: str | None = None):

        self.production = production
        self.read_config()
        self.get_email_info()
        self.get_usps_user_id()

        if self.production:
            self.site = "https://nbs.iphis.maine.gov/"
        else:
            # New NBS test site (migrated off the retired nbstest.state.me.us).
            # Hitting HomePage.do redirects to the InductiveHealth/Keycloak login
            # when there is no session; login is handled by _log_in_inductive.
            self.site = "https://menbstest.inductivehealth.com/nbs/HomePage.do?method=loadHomePage"

        # Core flags / queues
        self.not_a_case_log: list[str] = []
        self.lab_data_issues_log: list[str] = []
        self.issues: list[str] = []
        self.reviewed_ids: list[str] = []
        self.what_do: list[str] = []
        self.reason: list[str] = []

        self.HepB_notification_bot = False
        self.iGAS_notification_bot = False

        self.num_attempts = 3
        self.queue_loaded: bool | None = None
        # Number of target-condition options SortQueue matched in the queue filter;
        # 0 means the disease has no cases in the queue. None until SortQueue runs.
        self.condition_filter_matches: int | None = None
        self.wait_before_timeout = 30
        self.sleep_duration = 3300  # adjust if needed
        

        # Build driver (inherit from Chrome)
        options = webdriver.ChromeOptions()
        options.add_argument("log-level=3")
        options.add_argument("--ignore-ssl-errors=yes")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument('--hide-crash-restore-bubble')
        options.add_argument('--disable-session-crashed-bubble')
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9223")
        prefs = {
            'NewTabPage.FooterVisible': False,
            "credentials_enable_service": False,
            'profile': {
                'password_manager_enabled': False
            },
            # "profile.password_manager_enabled": False,
            # 2. Prevent Restore Window Pop-up
            "profile.exit_type": "Normal",
            "profile.default_content_setting_values.automatic_downloads": 1,
            # "profile.exit_type": "None",
            "profile.exited_cleanly": True
        }
        
        options.add_experimental_option("prefs", prefs)
        # options.add_argument("--headless")

        if chrome_path:
            service = Service(chrome_path)
            super().__init__(service=service, options=options)
        else:
            driver_path = ChromeDriverManager().install()
            service = Service(driver_path)
            super().__init__(service=service, options=options)

        handles = self.window_handles
        print("current-handle-title: ", self.title)
        for handle in handles:
            self.switch_to.window(handle) 
            print(f"Handle ID: {handle} | Title: {self.title} | URL: {self.current_url}")
            if self.title == "New Tab" or self.title == "RSA SecurID PASSCODE":
                break
        print("handles:", handles)
        # if len(handles) > 1:
        #     self.switch_to.window(handles[0])

        self.Reset()
        self.GetObInvNames()

    def GetObInvNames(self):
        """Read list of congregate setting outbreak investigators from config.cfg."""
        self.outbreak_investigators = self.config.get(
            "OutbreakInvestigators", "Investigators"
        ).split(", ")

    def Reset(self):
        """
        Clear values of attributes assigned during case investigation review.
        Use the union of attributes from both branches to avoid AttributeError.
        """
        self.issues = []

        # Time markers
        self.now = datetime.now().date()
        self.collection_date = None
        self.serology_collection_date = None
        self.received_date = None
        self.current_report_date = None
        self.investigation_start_date = None
        self.date_closed = None
        self.earliest_date_received = None
        self.latest_date_received = None

        # Demographics / identity
        self.dob = None
        self.age = None
        self.age_units = None
        self.age_type = None
        self.patient_sex = None
        self.initial_name = None
        self.final_name = None

        # Address / geography
        self.city = None
        self.state = None
        self.county = None
        self.country = None
        self.zipcode = None
        self.jurisdiction = None

        # Disease / status
        self.CaseStatus = None
        self.CorrectCaseStatus = None
        self.current_status = None
        self.status = None
        self.death_indicator = None
        self.is_deceased = None
        self.patient_die_from_illness = None

        # Hospitalization
        self.hospitalization_indicator = None
        self.hosp_aoe = None
        self.admission_date = None
        self.discharge_date = None
        self.icu_indicator = None
        self.icu_aoe = None

        # Symptoms / exposure / epi
        self.symp_aoe = None
        self.symptoms = None
        self.symptoms_list: list[str] = []
        self.cong_aoe = None
        self.cong_setting_indicator = None
        self.first_responder = None
        self.fr_aoe = None
        self.healthcare_worker = None
        self.hcw_aoe = None
        self.preg_aoe = None
        self.epi = None
        self.travel_outside_home = None

        # Labs
        self.labs = None
        self.lab_specimen_source = None
        self.lab_specimen_collection_date = None
        self.lab_report_date = None
        self.lab_is_serology = False
        self.culture_done = None
        self.culture_positive = None
        self.negative_lab_result = False
        self.missing_lab_report = False
        self.serology_test_type = None
        self.titer_value = None

        # Reporting / investigation
        self.investigator = None
        self.investigator_name = None
        self.immpact = None
        self.ltf = None
        self.report_date = None
        self.reporting_organization = None
        self.reporting_provider = None
        self.returned_by_link = False
        self.missing_tab = False
        self.confirmation_method = None

        # Vaccination
        self.vax_recieved = None

        # Sleep tracking
        self.slept = 0

    ########################### NBS Navigation Methods ############################

    def get_credentials(self):
        """Prompt user to provide a valid username and RSA token to log in to NBS."""
        self.username = input('Enter your SOM username ("first_name.last_name"):')
        self.passcode = input("Enter your RSA passcode:")

    def set_credentials(self, username, passcode):
        """Set username and RSA token for NBS login."""
        self.username = username
        self.passcode = passcode

    def _submit_login_form(self):
        """Fill the RSA SecurID login form and click Log In.

        The form lives inside 'contentFrame', whose inner document reloads a
        moment after the frame first appears (anti-framing JS blanks/reloads the
        body). A blind 100s sleep used to hide this race. Instead we fill-and-
        verify: type the username and confirm it actually stuck; if a reload
        wiped it, retry. Only once the value persists is the form stable, at
        which point we enter the passcode and submit. Returns True if submitted.
        """
        login_load_timeout = 120
        login_button_xpath = "//input[@value='Log In']"
        for attempt in range(6):
            try:
                self.switch_to.default_content()
                WebDriverWait(self, login_load_timeout).until(
                    EC.frame_to_be_available_and_switch_to_it("contentFrame")
                )
                WebDriverWait(self, login_load_timeout).until(
                    EC.element_to_be_clickable((By.XPATH, login_button_xpath))
                )
                user_field = self.find_element(By.ID, "username")
                user_field.clear()
                user_field.send_keys(self.username)
                time.sleep(1)  # let any pending frame reload fire
                if self.find_element(By.ID, "username").get_attribute("value") != self.username:
                    print(f"Login form reloaded and cleared the username, retry {attempt}...")
                    time.sleep(2)
                    continue
                # Form is stable now -- enter passcode and submit immediately.
                self.find_element(By.ID, "passcode").send_keys(self.passcode)
                self.find_element(By.XPATH, login_button_xpath).click()
                self.switch_to.default_content()
                return True
            except (StaleElementReferenceException, TimeoutException) as e:
                print(f"Login form not stable yet, retry {attempt}: {e}")
                time.sleep(2)
        self.switch_to.default_content()
        return False

    def _on_nbs_dashboard(self, timeout=10):
        """Return True if the NBS home dashboard has loaded (logged in).

        The dashboard's patient-search Last Name field (id DEM102) is unique to
        the home page, so its presence is a reliable 'we are authenticated' signal
        that works on both the old and new (InductiveHealth) sites.
        """
        try:
            WebDriverWait(self, timeout).until(
                EC.presence_of_element_located((By.ID, "DEM102"))
            )
            return True
        except TimeoutException:
            return False

    def _log_in_inductive(self, is_logged_in=False):
        """Log in to the new InductiveHealth NBS test site via Maine DHHS SSO.

        Flow: open the site. If a session is already warm we land straight on the
        dashboard. Otherwise we land on the InductiveHealth/Keycloak sign-in page;
        clicking 'Maine DHHS Users' (#social-mesaml) hands off to the State of
        Maine SSO, which authenticates silently over the user's VPN session and
        bounces back to the dashboard. If that silent SSO does not complete (no
        VPN / expired session surfacing a real credential prompt), we pause and
        let the user finish the login by hand, then continue once the dashboard
        appears. If it never appears, raise so the caller can report login failed.
        """
        self.get(self.site)

        # Warm session: already on the dashboard, nothing to do.
        if self._on_nbs_dashboard(timeout=12):
            print("Already authenticated on NBS test site.")
            return

        # Otherwise we expect the Keycloak sign-in page. Choose Maine DHHS SSO.
        try:
            WebDriverWait(self, 20).until(
                EC.element_to_be_clickable((By.ID, "social-mesaml"))
            )
            print("Clicking 'Maine DHHS Users' for SSO login...")
            self.find_element(By.ID, "social-mesaml").click()
        except TimeoutException:
            print("Did not find the 'Maine DHHS Users' SSO option on the login page.")

        # Silent VPN/SSO round-trip should land us on the dashboard quickly.
        if self._on_nbs_dashboard(timeout=45):
            print("Logged in to NBS test site via Maine DHHS SSO.")
            return

        # Fallback: a real credential page is up (no VPN / expired session).
        # Give the user a window to complete it manually, then continue.
        print(
            "\n*** LOGIN NEEDS ATTENTION ***\n"
            "The Maine DHHS SSO did not log in automatically. Please complete the\n"
            "login in the Chrome window now. Waiting up to 5 minutes for the NBS\n"
            "dashboard to appear...\n"
        )
        if self._on_nbs_dashboard(timeout=300):
            print("Manual login completed; continuing.")
            return

        raise Exception(
            "Login to NBS test site failed: dashboard never loaded. "
            "Check the VPN/SSO session and the Chrome window."
        )

    def log_in(self, is_logged_in=False):
        """Log in to NBS."""
        # The test site migrated to InductiveHealth/Keycloak with Maine DHHS SSO,
        # a different login flow from the production RSA SecurID form below.
        if not self.production:
            return self._log_in_inductive(is_logged_in)

        portal_link_xpath = '//*[@id="bea-portal-window-content-4"]/tr/td/h2[4]/font/a'
        self.get(self.site)

        if not is_logged_in:
            print("logging in...")
            # Submit the login form, then give authentication a short window to
            # land on the portal page. If the submit does not authenticate within
            # auth_wait_seconds (failed/late passcode, a broken form load, etc.)
            # reload the login page, re-enter the credentials, and try the whole
            # thing again rather than giving up. Capped to limit RSA lockout risk
            # from repeated bad submissions.
            max_login_attempts = 3
            auth_wait_seconds = 5
            for login_attempt in range(max_login_attempts):
                # _submit_login_form re-enters username + passcode each pass, so
                # after a reload below the credentials are typed in fresh.
                self._submit_login_form()
                try:
                    # Short wait: a successful auth surfaces the portal link almost
                    # immediately. Don't block the full timeout here so a failed
                    # submit reloads and re-enters credentials quickly.
                    WebDriverWait(self, auth_wait_seconds).until(
                        EC.element_to_be_clickable((By.XPATH, portal_link_xpath))
                    )
                    self.find_element(By.XPATH, portal_link_xpath).click()
                    return  # logged in and portal reached
                except TimeoutException:
                    print(
                        f"Authentication did not complete within {auth_wait_seconds}s "
                        f"(attempt {login_attempt + 1}/{max_login_attempts}); reloading "
                        f"login page and re-entering credentials..."
                    )
                    self.get(self.site)
                    time.sleep(2)  # let the reloaded login page settle before re-entry
            print("WARNING: login failed after reload retries; portal page not reached.")
            return

        # Already authenticated (session reuse): just open the portal link.
        WebDriverWait(self, self.wait_before_timeout).until(
            EC.element_to_be_clickable((By.XPATH, portal_link_xpath))
        )
        self.find_element(By.XPATH, portal_link_xpath).click()
    
    def log_in_v2(self):
        """Log in to MENBS."""
        self.get(self.site)
        print("passed")
        partial_link = "Maine NBS Only, ESSENCE use above sign-in"
        # WebDriverWait(self, self.wait_before_timeout).until(
        #     EC.element_to_be_clickable((By.ID, "social-mesaml"))
        # )
        # self.find_element(By.ID, "social-mesaml").click()
        WebDriverWait(self, self.wait_before_timeout).until(
            EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, partial_link))
        )
        print('found')
        self.find_element(By.PARTIAL_LINK_TEXT, partial_link).click()
        print(self.page_source)
        time.sleep(3)

    def go_to_tab_one(self):
        path = '//*[@id="tabs0head0"]'
        WebDriverWait(self, self.wait_before_timeout).until(
            EC.element_to_be_clickable((By.XPATH, path))
        )
        self.find_element(By.XPATH, path).click()

    def go_to_tab_two(self):
        missing_tab = False
        try:
            path = '//*[@id="tabs0head1"]'
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.element_to_be_clickable((By.XPATH, path))
            )
            self.find_element(By.XPATH, path).click()
            return missing_tab
        except (TimeoutException, NoSuchElementException) as e:
           print(f"can't find element 2tab, {str(e)}")
           missing_tab = True
           return missing_tab

    def go_to_tab_three(self):
        path = '//*[@id="tabs0head2"]'
        WebDriverWait(self, self.wait_before_timeout).until(
            EC.element_to_be_clickable((By.XPATH, path))
        )
        self.find_element(By.XPATH, path).click()

    def go_to_tab_five(self):
        missing_tab = False
        try: 
            path = '//*[@id="tabs0head4"]'
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.element_to_be_clickable((By.XPATH, path))
            )
            self.find_element(By.XPATH, path).click()
            return missing_tab
        except (TimeoutException, NoSuchElementException) as e:
            print(f"[INFO] Lab tab (5tab) not found, skipping lab checks. Details: {str(e)}")
            missing_tab = True
            return missing_tab

    ################### Name Details check methods####################

    def CheckFirstName(self):
        """Must provide first name."""
        self.CheckForValue('//*[@id="DEM104"]', "First name is blank.")

    def CheckLastName(self):
        """Must provide last name."""
        self.CheckForValue('//*[@id="DEM102"]', "Last name is blank.")

    ################ Check Phone Methods #####################

    def CheckPhone(self):
        """If a phone number is provided make sure it is ten digits."""
        home_phone = self.ReadText('//*[@id="DEM177"]')
        work_phone = self.ReadText('//*[@id="NBS002"]')
        cell_phone = self.ReadText('//*[@id="NBS006"]')

        def _check(phone_value):
            if phone_value and len(re.findall(r"\d", str(phone_value))) != 10:
                self.issues.append("Phone number is not ten digits.")

        if home_phone:
            _check(home_phone)
        elif work_phone:
            _check(work_phone)
        elif cell_phone:
            _check(cell_phone)

    ############ Demographic/Address Check Methods #####################

    def CheckStAddr(self):
        """Must provide street address."""
        street_address = self.ReadText('//*[@id="DEM159"]')
        if not street_address:
            self.issues.append("Street address is blank.")

    def CheckCity(self):
        """Must provide city."""
        self.city = self.ReadText('//*[@id="DEM161"]')
        if not self.city:
            self.issues.append("City is blank.")

    def CheckState(self):
        """Must provide state and if it is not Maine case should be not a case."""
        state = self.ReadText('//*[@id="DEM162"]')
        if not state:
            self.issues.append("State is blank.")
        elif state != "Maine":
            self.issues.append("State is not Maine.")
            print(f"state: {state}")
        self.state = state

    def CheckStateANA(self):
        """Record state for ANA logic."""
        self.state = self.CheckForValue('//*[@id="DEM162"]', "State is blank.")

    def CheckZip(self):
        """Must provide zip code."""
        self.zipcode = self.CheckForValue('//*[@id="DEM163"]', "Zip code is blank.")

    def CheckCounty(self):
        """Must provide county unless the jurisdiction is 'Out of State'."""
        self.county = self.CheckForValue('//*[@id="DEM165"]', "County is blank.")

    def CheckCountry(self):
        """Must provide country."""
        self.country = self.CheckForValue('//*[@id="DEM167"]', "Country is blank.")
        if self.country and self.country != "UNITED STATES":
            self.issues.append("Out of State")

    ################### Personal Details check methods ####################

    def CheckDOB(self):
        """Must provide DOB."""
        self.dob = self.ReadDate('//*[@id="DEM115"]')
        if not self.dob:
            self.issues.append("DOB is blank.")
        elif self.dob > self.now:
            self.issues.append("DOB cannot be in the future.")

    def CheckAge(self):
        """Must provide age and ensure age matches DOB and investigation start date."""
        self.age = self.ReadText('//*[@id="INV2001"]')
        self.age_units = self.ReadText('//*[@id="INV2002"]')
        self.current_report_date = self.ReadDate('//*[@id="INV111"]')
        self.investigation_start_date = self.ReadDate('//*[@id="INV147"]')
        if not self.age:
            self.issues.append("Correct Age is blank.")
            return

        if not self.dob or not self.investigation_start_date:
            return

        days_diff = (self.investigation_start_date - self.dob).days
        if self.age_units == "Years":
            if int(days_diff / 365.25) != int(self.age):
                self.issues.append("Age mismatch.")
        elif self.age_units == "Months":
            if int(days_diff / 30) != int(self.age):
                self.issues.append("Age mismatch.")

    def CheckAgeType(self):
        """Age type must be one of Days, Months, Years."""
        self.age_type = self.ReadText('//*[@id="INV2002"]')
        if not self.age_type:
            self.issues.append("Age Type is blank.")
        elif self.age_type not in ("Days", "Months", "Years"):
            self.issues.append("Age Type is not one of Days, Months, or Years.")

    def CheckCurrentSex(self):
        """Ensure patient current sex is not blank."""
        self.patient_sex = self.ReadText('//*[@id="DEM113"]')
        if not self.patient_sex:
            self.issues.append("Patient sex is blank.")
        elif self.patient_sex == "Unknown":
            comment = self.ReadText('//*[@id="DEM196"]')
            if not comment:
                self.issues.append("Patient sex is Unknown without a note.")

    ############ Ethnicity and Race Information Check Methods #####################

    def CheckEthnicity(self):
        """Must provide ethnicity."""
        self.ethnicity = self.CheckForValue('//*[@id="DEM155"]', "Ethnicity is blank.")

    def CheckRace(self):
        """Must provide race and selection must make sense."""
        self.race = self.CheckForValue(
            '//*[@id="patientRacesViewContainer"]', "Race is blank."
        )
        ambiguous_answers = ["Unknown", "Other", "Refused to answer", "Not Asked"]
        for answer in ambiguous_answers:
            if (
                answer in self.race
                and self.race != answer
                and self.race == "Native Hawaiian or Other Pacific Islander"
            ):
                self.issues.append(
                    '"' + answer + '"' + " selected in addition to other options for race."
                )

    def CheckRaceAna(self):
        """Race check variant with additional ANA logic."""
        self.race = self.CheckForValue(
            '//*[@id="patientRacesViewContainer"]', "Race is blank."
        )
        if "White" in self.race and "Unknown" in self.race:
            self.issues.append(
                "White and Unknown race should not be selected at the same time."
            )
        if "Other" in self.race:
            self.CheckForValue(
                '//*[@id="DEM196"]',
                "If Other race is selected there needs to be a comment.",
            )
        ambiguous_answers = ["Unknown", "Other", "Refused to answer", "Not Asked"]
        for answer in ambiguous_answers:
            if (
                answer in self.race
                and self.race != answer
                and self.race == "Native Hawaiian or Other Pacific Islander"
            ):
                self.issues.append(
                    '"' + answer + '"' + " selected in addition to other options for race."
                )

    def go_to_id(self, id):
        """Navigate to specific patient by NBS ID from Home."""
        self.find_element(By.XPATH, '//*[@id="DEM229"]').send_keys(id)
        self.find_element(
            By.XPATH,
            '//*[@id="patientSearchByDetails"]/table[2]/tbody/tr[8]/td[2]/input[1]',
        ).click()
        search_result_path = '//*[@id="searchResultsTable"]/tbody/tr/td[1]/a'
        WebDriverWait(self, self.wait_before_timeout).until(
            EC.presence_of_element_located((By.XPATH, search_result_path))
        )
        self.find_element(By.XPATH, search_result_path).click()

    def clean_patient_id(self, patient_id):
        """Clean local patient ids to leave an id searchable through NBS front end."""
        if patient_id[0:4] == "PSN1":
            patient_id = patient_id[4 : len(patient_id) - 4]
        elif patient_id[0:4] == "PSN2":
            patient_id = "1" + patient_id[4 : len(patient_id) - 4]
        return patient_id

    def go_to_summary(self):
        """Within a patient profile navigate to the Summary tab."""
        self.find_element(By.XPATH, '//*[@id="tabs0head0"]').click()

    def go_to_events(self):
        """Within patient profile navigate to the Events tab."""
        events_path = '//*[@id="tabs0head1"]'
        try:
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.presence_of_element_located((By.XPATH, events_path))
            )
            self.find_element(By.XPATH, events_path).click()
            error_encountered = False
        except TimeoutException:
            error_encountered = True
        return error_encountered

    def go_to_demographics(self):
        """Within a patient profile navigate to the Demographics tab."""
        demographics_path = '//*[@id="tabs0head2"]'
        WebDriverWait(self, self.wait_before_timeout).until(
            EC.presence_of_element_located((By.XPATH, demographics_path))
        )
        self.find_element(By.XPATH, demographics_path).click()

    def go_to_home(self):
        """Go to NBS Home page."""
        partial_link = "Home"
        for i in range(3):
            try:
                timeout = self.wait_before_timeout + i * 10
                WebDriverWait(self, timeout).until(
                    EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, partial_link))
                )
                self.find_element(By.PARTIAL_LINK_TEXT, partial_link).click()
                self.home_loaded = True
                break
            except StaleElementReferenceException:
                print("StaleElementReferenceException encountered, retrying...")
                self.home_loaded = False
            except TimeoutException:
                self.home_loaded = False
        if not self.home_loaded:
            sys.exit(
                print(
                    f"Made {i} unsuccessful attempts to load Home page. A persistent issue with NBS was encountered."
                )
            )

    def GoToApprovalQueue(self):
        """Navigate to approval queue from Home page."""
        # On the new test site the home-page worklist link's click is intercepted
        # by a JS handler and never navigates, so go straight to the worklist URL.
        # Production keeps the original click-the-link behavior.
        if not self.production:
            base = self.site.split("HomePage.do")[0]
            self.get(base + "MyTaskList1.do?ContextAction=NNDApproval&initLoad=true")
            try:
                WebDriverWait(self, self.wait_before_timeout).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="removeFilters"]'))
                )
            except TimeoutException:
                self.HandleBadQueueReturn()
            return

        partial_link = "Approval Queue for Initial Notifications"
        try:
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, partial_link))
            )
            self.find_element(By.PARTIAL_LINK_TEXT, partial_link).click()
        except TimeoutException:
            self.HandleBadQueueReturn()

    def ReturnApprovalQueue(self):
        """Return to Approval Queue from an investigation initially accessed from the queue."""
        xpath = '//*[@id="bd"]/div[1]/a'
        try:
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            self.find_element(By.XPATH, xpath).click()
        except TimeoutException:
            self.HandleBadQueueReturn()

    def SortQueue(self, paths: dict):
        """Sort review queue so that only specified investigations are listed."""
        try:
            # Clear all filters
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.element_to_be_clickable((By.XPATH, paths["clear_filter_path"]))
            )
            self.find_element(By.XPATH, paths["clear_filter_path"]).click()
            time.sleep(5)

            # Open condition dropdown menu
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.presence_of_element_located((By.XPATH, paths["description_path"]))
            )
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.element_to_be_clickable((By.XPATH, paths["description_path"]))
            )
            self.find_element(By.XPATH, paths["description_path"]).click()
            time.sleep(1)

            # Clear checkboxes
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.element_to_be_clickable((By.XPATH, paths["clear_checkbox_path"]))
            )
            self.find_element(By.XPATH, paths["clear_checkbox_path"]).click()
            time.sleep(1)

            # Select all tests. The Condition filter lists only the conditions
            # actually present in the queue, so if none of the target tests have a
            # matching option there are zero such cases. Track how many we matched
            # so disease_case_count can report 0 instead of falling back to the
            # unfiltered queue size (selecting nothing makes NBS show everything).
            self.condition_filter_matches = 0
            for test in paths["tests"]:
                try:
                    results = self.find_elements(
                        By.XPATH, f"//label[contains(text(),'{test}')]"
                    )
                    for result in results:
                        result.click()
                        self.condition_filter_matches += 1
                except (NoSuchElementException, ElementNotInteractableException):
                    pass
            time.sleep(1)

            # Click ok
            try:
                WebDriverWait(self, self.wait_before_timeout).until(
                    EC.element_to_be_clickable((By.XPATH, paths["click_ok_path"]))
                )
                self.find_element(By.XPATH, paths["click_ok_path"]).click()
            except (NoSuchElementException, TimeoutException):
                WebDriverWait(self, self.wait_before_timeout).until(
                    EC.element_to_be_clickable((By.XPATH, paths["click_cancel_path"]))
                )
                self.find_element(By.XPATH, paths["click_cancel_path"]).click()
                time.sleep(3)
                self.Sleep()

            time.sleep(1)
            print(f"sleep count {self.slept}")

            # Sort chronologically, oldest first
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.element_to_be_clickable((By.XPATH, paths["submit_date_path"]))
            )
            self.find_element(By.XPATH, paths["submit_date_path"]).click()
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.element_to_be_clickable((By.XPATH, paths["submit_date_path"]))
            )
            self.find_element(By.XPATH, paths["submit_date_path"]).click()
        except (TimeoutException, ElementClickInterceptedException):
            self.HandleBadQueueReturn()

    def SortApprovalQueue(self):
        """
        Sort approval queue so that cases are listed chronologically by
        notification creation date and in reverse alpha order.
        (Strep-focused version from newer file.)
        """
        clear_filter_path = '//*[@id="removeFilters"]/a/font'
        submit_date_path = '//*[@id="parent"]/thead/tr/th[3]/a'
        condition_path = '//*[@id="parent"]/thead/tr/th[8]/a'
        description_path = (
            "//html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/img"
        )
        clear_checkbox_path = "/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[2]/input"
        try:
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.element_to_be_clickable((By.XPATH, clear_filter_path))
            )
            self.find_element(By.XPATH, clear_filter_path).click()

            time.sleep(3)
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.element_to_be_clickable((By.XPATH, description_path))
            )
            self.find_element(By.XPATH, description_path).click()

            WebDriverWait(self, self.wait_before_timeout).until(
                EC.element_to_be_clickable((By.XPATH, clear_checkbox_path))
            )
            self.find_element(By.XPATH, clear_checkbox_path).click()
            try:
                # Group A Streptococcus logic (newer)
                self.find_element(
                    By.XPATH, "//label[contains(text(),'Group A Streptococcus, invasive')]/input"
                ).click()
                try:
                    self.find_element(
                        By.XPATH, "//label[contains(text(),'STREPTOCOCCUS PYOGENES')]/input"
                    ).click()
                except Exception as e:
                    print(f"Error encountered: {e}")

                self.find_element(
                    By.XPATH,
                    "/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[1]/input[1]",
                ).click()
            except NoSuchElementException:
                self.find_element(
                    By.XPATH,
                    "/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/thead/tr/th[8]/div/label[1]/input[2]",
                ).click()
            except Exception as e:
                print(f"Error encountered: {e}")

            # Double click submit date
            for i in range(3):
                try:
                    WebDriverWait(self, self.wait_before_timeout).until(
                        EC.element_to_be_clickable((By.XPATH, submit_date_path))
                    )
                    self.find_element(By.XPATH, submit_date_path).click()
                    WebDriverWait(self, self.wait_before_timeout).until(
                        EC.element_to_be_clickable((By.XPATH, submit_date_path))
                    )
                    self.find_element(By.XPATH, submit_date_path).click()
                    break
                except StaleElementReferenceException:
                    print(
                        f"StaleElementReferenceException for submit_date_path, trying again... retry_number: {i}"
                    )
                except TimeoutException:
                    print(
                        f"TimeoutException for submit_date_path, trying again... retry_number: {i}"
                    )

            # Double click condition for reverse alpha order
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.element_to_be_clickable((By.XPATH, condition_path))
            )
            self.find_element(By.XPATH, condition_path).click()
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.element_to_be_clickable((By.XPATH, condition_path))
            )
            self.find_element(By.XPATH, condition_path).click()
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.element_to_be_clickable((By.XPATH, condition_path))
            )
        except (TimeoutException, ElementClickInterceptedException):
            self.HandleBadQueueReturn()

    def HandleBadQueueReturn(self):
        """
        When a request is sent to NBS to load or filter the approval queue
        and "Nothing found to display", or anything other than the populated
        queue is returned, navigate back to the home page and request the queue again.
        """
        for _ in range(self.num_attempts):
            try:
                self.go_to_home()
                self.GoToApprovalQueue()
                self.queue_loaded = True
                break
            except TimeoutException:
                self.queue_loaded = False
        if not self.queue_loaded:
            print(
                f"Made {self.num_attempts} unsuccessful attempts to load approval queue. Either the queue is truly empty, or a persistent issue with NBS was encountered."
            )

    def GoToNPage(self, n):
        """Navigate to page n of the queue."""
        if n >= 2:
            next_page_path = f'//*[@title="Go to page {n}"]'
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.element_to_be_clickable((By.XPATH, next_page_path))
            )
            self.find_element(By.XPATH, next_page_path).click()
        print(f"Moved to page {n}")

    def CheckFirstCase(self, n: int = 1):
        """Ensure that case at row n is set and save case's name for later use."""
        try:
            time.sleep(4)
            self.condition = self.find_element(
                By.XPATH, f'//*[@id="parent"]/tbody/tr[{n}]/td[8]/a'
            ).get_attribute("innerText")
            self.patient_name = self.find_element(
                By.XPATH, f'//*[@id="parent"]/tbody/tr[{n}]/td[7]/a'
            ).get_attribute("innerText")
        except NoSuchElementException:
            self.condition = None
            self.patient_name = None
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            self.condition = None
            self.patient_name = None

    def GoToFirstCaseInApprovalQueue(self):
        """Navigate to first case in the approval queue."""
        xpath_to_case = '//*[@id="parent"]/tbody/tr[1]/td[8]/a'
        xpath_to_first_name = '//*[@id="DEM104"]'
        try:
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath_to_case))
            )
            self.find_element(By.XPATH, xpath_to_case).click()
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath_to_first_name))
            )
        except TimeoutException:
            self.HandleBadQueueReturn()

    def GoToNCaseInApprovalQueue(self, n: int = 1):
        """Navigate to nth case in the approval queue."""
        xpath_to_case = f'//*[@id="parent"]/tbody/tr[{n}]/td[8]/a'
        xpath_to_first_name = '//*[@id="DEM104"]'
        try:
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath_to_case))
            )
            self.find_element(By.XPATH, xpath_to_case).click()
            WebDriverWait(self, self.wait_before_timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath_to_first_name))
            )
        except TimeoutException:
            self.HandleBadQueueReturn()

    def GoToCaseInfo(self):
        """Within an investigation navigate to the Case Info tab."""
        case_info_tab_path = '//*[@id="tabs0head1"]'
        WebDriverWait(self, self.wait_before_timeout).until(
            EC.presence_of_element_located((By.XPATH, case_info_tab_path))
        )
        self.find_element(By.XPATH, case_info_tab_path).click()

    def GoToCOVID(self):
        """Within an investigation navigate to the condition-specific tab (COVID or other)."""
        covid_tab_path = '//*[@id="tabs0head2"]'
        WebDriverWait(self, self.wait_before_timeout).until(
            EC.presence_of_element_located((By.XPATH, covid_tab_path))
        )
        self.find_element(By.XPATH, covid_tab_path).click()

    def go_to_lab(self, lab_id):
        """Navigate to a lab from a patient profile."""
        lab_report_table_path = '//*[@id="lab1"]'
        lab_report_table = self.ReadTableToDF(lab_report_table_path)
        if isinstance(lab_report_table, pd.DataFrame) and len(lab_report_table) > 1:
            lab_row_index = lab_report_table[
                lab_report_table["Event ID"] == lab_id
            ].index.tolist()[0]
            lab_row_index = str(int(lab_row_index) + 1)
            lab_path = f"/html/body/div[2]/form/div/table[4]/tbody/tr[2]/td/div[2]/table/tbody/tr/td/div[1]/div[5]/div/table/tbody/tr/td/table/tbody/tr[{lab_row_index}]/td[1]/a"
        else:
            lab_path = "/html/body/div[2]/form/div/table[4]/tbody/tr[2]/td/div[2]/table/tbody/tr/td/div[1]/div[5]/div/table/tbody/tr/td/table/tbody/tr/td[1]/a"
        self.find_element(By.XPATH, lab_path).click()

    # adding code to read investigation table
    def read_investigation_table(self):
        """Read the investigations table in the Events tab of a patient profile."""
        investigation_table_path = '//*[@id="inv1"]'
        investigation_table = self.ReadTableToDF(investigation_table_path)
        if isinstance(investigation_table, pd.DataFrame):
            investigation_table["Start Date"] = pd.to_datetime(
                investigation_table["Start Date"]
            )
        return investigation_table

    def go_to_investigation_by_index(self, index):
        """Navigate to an existing investigation based on its position in the table."""
        if index > 1:
            existing_investigation_path = f"/html/body/div[2]/form/div/table[4]/tbody/tr[2]/td/div[2]/table/tbody/tr/td/div[1]/div[3]/div/table/tbody/tr[2]/td/table/tbody/tr[{str(index)}]/td[1]/a"
        else:
            existing_investigation_path = "/html/body/div[2]/form/div/table[4]/tbody/tr[2]/td/div[2]/table/tbody/tr/td/div[1]/div[3]/div/table/tbody/tr[2]/td/table/tbody/tr/td[1]/a"
        self.find_element(By.XPATH, existing_investigation_path).click()

    def go_to_investigation_by_id(self, inv_id):
        """Navigate to an investigation with a given id from a patient profile."""
        inv_table = self.read_investigation_table()
        inv_row = inv_table[inv_table["Investigation ID"] == inv_id]
        inv_index = int(inv_row.index.to_list()[0]) + 1
        self.go_to_investigation_by_index(inv_index)

    def return_to_patient_profile_from_inv(self):
        """Go back to the patient profile from within an investigation."""
        return_to_file_path = '//*[@id="bd"]/div[1]/a'
        self.find_element(By.XPATH, return_to_file_path).click()

    def return_to_patient_profile_from_lab(self):
        """Go back to the patient profile from within a lab report."""
        return_to_file_path = '//*[@id="doc3"]/div[1]/a'
        self.find_element(By.XPATH, return_to_file_path).click()

    def click_submit(self):
        """Click submit button to save changes."""
        submit_button_path = (
            "/html/body/div/div/form/div[2]/div[1]/table[2]/tbody/tr/td[2]/table/tbody/"
            "tr/td[1]/input"
        )
        for i in range(3):
            try:
                timeout = self.wait_before_timeout + i * 10
                element = WebDriverWait(self, timeout).until(
                    EC.element_to_be_clickable((By.XPATH, submit_button_path))
                )
                element.click()
                break
            except TimeoutException:
                print(
                    f"TimeoutException for submit_button_path, trying again... retry_number: {i}"
                )
            except StaleElementReferenceException:
                print(
                    f"StaleElementReferenceException for submit_button_path, trying again... retry_number: {i}"
                )
            except NoSuchElementException:
                print(
                    f"No submit_button_path found, trying again... retry_number: {i}"
                )
                time.sleep(1)
            except Exception as e:
                print(
                    f"{e} has occured for submit_button_path, retry_number: {i}"
                )

    def click_manage_associations_submit(self):
        """Click submit button in the Manage Associations window."""
        submit_button_path = "/html/body/div[2]/div/table[2]/tbody/tr/td/table/tbody/tr/td[2]/input"
        self.find_element(By.XPATH, submit_button_path).click()

    def enter_edit_mode(self):
        """From within an investigation click the edit button to enter edit mode."""
        edit_button_path = (
            "/html/body/div/div/form/div[2]/div[1]/table[2]/tbody/tr/td[2]/table/tbody/"
            "tr/td[1]/input"
        )
        self.find_element(By.XPATH, edit_button_path).click()
        try:
            self.switch_to.alert.accept()
        except NoAlertPresentException:
            pass

    def click_cancel(self):
        """Click cancel."""
        cancel_path = '//*[@id="Cancel"]'
        self.find_element(By.XPATH, cancel_path).click()
        self.switch_to.alert.accept()

    def go_to_manage_associations(self):
        """Click button to navigate to the Manage Associations page from an investigation."""
        manage_associations_path = '//*[@id="manageAssociations"]'
        self.find_element(By.XPATH, manage_associations_path).click()
        try:
            self.switch_to.alert.accept()
        except NoAlertPresentException:
            pass

    ################# Investigation Status / Investigator ########################

    def CheckInvestigationStatus(self):
        """Only accept closed investigations for review."""
        inv_status = self.ReadText('//*[@id="INV109"]')
        if not inv_status:
            self.issues.append("Investigation status is blank.")
        elif inv_status.lower() == "open":
            self.issues.append("Investigation status is open.")

    def CheckInvestigatorAssignDate(self):
        """If an investigator was assigned then there should be a date."""
        if self.investigator:
            assigned_date = self.ReadText('//*[@id="INV110"]')
            if not assigned_date:
                self.issues.append("Missing investigator assigned date.")

    def CheckInvestigator(self):
        """Check if an investigator was assigned to the case."""
        investigator = self.ReadText('//*[@id="INV180"]')
        self.investigator_name = investigator
        if not investigator:
            self.issues.append("Investigator is blank.")

    ################# Key Report Dates Check Methods ###############################

    def CheckReportDate(self):
        """Check report date consistency vs investigation and lab dates."""
        self.current_report_date = self.ReadDate('//*[@id="INV111"]')
        if not self.current_report_date:
            self.issues.append("Missing report date.")
        elif (
            self.investigation_start_date
            and self.current_report_date > self.investigation_start_date
        ):
            self.issues.append("Report date cannot be after investigation start date.")
        elif self.report_date and self.report_date != self.current_report_date:
            self.issues.append("Report date mismatch.")

        if (self.earliest_date_received or self.latest_date_received) and (
            self.report_date
            and self.report_date != self.earliest_date_received
            and self.report_date != self.latest_date_received
        ):
            self.issues.append(
                "Report date does not match any recieved date."
            )

    def CheckCountyStateReportDate(self):
        """
        Check if county report date and state report date are consistent with
        earliest received date, investigation start date, and report date.
        """
        current_county_date = self.ReadDate('//*[@id="INV120"]')
        current_state_date = self.ReadDate('//*[@id="INV121"]')

        if current_county_date:
            if (
                self.earliest_date_received
                and (
                    current_county_date > self.earliest_date_received
                    or current_county_date < self.earliest_date_received
                )
            ):
                self.issues.append(
                    f"Earliest county report date should be {self.earliest_date_received}"
                )

            if (
                self.current_report_date
                and current_county_date < self.current_report_date
            ):
                self.issues.append(
                    "Earliest report to county cannot be prior to inital report date."
                )
            elif (
                self.investigation_start_date
                and current_county_date > self.investigation_start_date
            ):
                self.issues.append(
                    "Earliest report to county date cannot be after investigation start date"
                )
        else:
            self.issues.append("Report to county date missing.")

        if current_state_date:
            if (
                self.earliest_date_received
                and (
                    current_state_date > self.earliest_date_received
                    or current_state_date < self.earliest_date_received
                )
            ):
                self.issues.append(
                    f"Earliest state report date should be {self.earliest_date_received}"
                )

            if self.current_report_date and current_state_date < self.current_report_date:
                self.issues.append(
                    "Earliest report to state cannot be prior to inital report date."
                )
            elif (
                self.investigation_start_date
                and current_state_date > self.investigation_start_date
            ):
                self.issues.append(
                    "Earliest report to state date cannot be after investigation start date."
                )
        else:
            self.issues.append("Report to state date missing.")

        if current_county_date and current_state_date:
            if current_county_date != current_state_date:
                self.issues.append(
                    "Earliest dates reported to county and state do not match."
                )

    ################# Check Jurisdiction ####################

    def CheckJurisdiction(self):
        """Jurisdiction and county must match, with Out of State logic."""
        self.jurisdiction = self.ReadText('//*[@id="INV107"]')
        if not self.jurisdiction:
            self.issues.append("Jurisdiction is blank.")
            return

        if self.jurisdiction == "Out of State" and self.CaseStatus != "Not a Case":
            self.issues.append("Out of state - should be Not a Case.")

        if (
            self.jurisdiction
            and self.county
            and self.jurisdiction != "Out of State"
            and self.jurisdiction.lower().replace(" county", "")
            not in self.county.lower().replace(" county", "")
        ):
            self.issues.append("County and jurisdiction mismatch.")
        print(f"jurisdiction: {self.jurisdiction}")

    ################### Investigation Details Check Methods ########################

    def CheckInvestigationStartDate(self):
        """Verify investigation start date is on or after report date."""
        self.investigation_start_date = self.ReadDate('//*[@id="INV147"]')
        if not self.investigation_start_date:
            self.issues.append("Investigation start date is blank.")
        elif self.investigation_start_date > self.now:
            self.issues.append("Investigation start date cannot be in the future.")

    def CheckStateCaseID(self):
        """State Case ID must be provided."""
        case_id = self.ReadText('//*[@id="INV173"]')
        if not case_id:
            self.issues.append("State Case ID is blank.")

    def CheckSharedIndicator(self, blank=False):
        """Ensure shared indicator is yes or not blank."""
        if blank:
            shared_indicator = self.CheckForValue('//*[@id="NBS_UI_19"]/tbody/tr[5]/td[2]', 'Shared Indicator is blank')    
        else:
            shared_indicator = self.ReadText('//*[@id="NBS_UI_19"]/tbody/tr[5]/td[2]')
            if shared_indicator != "Yes":
                self.issues.append("Shared indicator not selected.")

    ################### Reporting Organization Check Methods #######################

    def CheckReportingSourceType(self):
        """Ensure that reporting source type is not empty."""
        reporting_source_type = self.ReadText('//*[@id="INV112"]')
        if not reporting_source_type:
            self.issues.append("Reporting source type is blank.")
        elif reporting_source_type == "Other":
            reporting_source_type_other = self.ReadText('//*[@id="INV183"]')
            if not reporting_source_type_other:
                self.issues.append(
                    "Reporting source type is Other but no other type provided."
                )

    def CheckReportingOrganization(self):
        """Ensure that reporting organization is not empty."""
        self.reporting_organization = self.ReadText('//*[@id="INV183"]')
        if not self.reporting_organization:
            self.issues.append("Reporting organization is blank.")

    def CheckReportingProvider(self):
        """Ensure that reporting provider is not empty."""
        self.reporting_provider = self.ReadText('//*[@id="INV181"]')
        if not self.reporting_provider:
            self.issues.append("Reporting Provider is blank.")

    def CheckReportingCounty(self):
        """Ensure that reporting county is not empty."""
        reporting_county = self.ReadText('//*[@id="NOT113"]')
        if not reporting_county:
            self.issues.append("Reporting county is blank.")

    ######################### Case Status / Transmission / Detection ###############

    def CheckTransmissionMode(self):
        """Transmission mode should be blank or airborne."""
        transmission_method = self.ReadText('//*[@id="INV157"]')
        if transmission_method not in ("", "Airborne"):
            self.issues.append("Transmission mode should be blank or airborne.")

    def CheckConfirmationMethodAna(self):
        """Confirmation Method must be blank or consistent with correct case status."""
        self.confirmation_method = self.ReadText('//*[@id="INV161"]')
        # if self.confirmation_method:
        #     if (self.status == "C") and ("Laboratory confirmed" not in self.confirmation_method):
        #         self.issues.append(
        #             'Since correct case status is confirmed confirmation method should include "Laboratory confirmed".'
        #         )
        #     elif (self.status == "P") and ("Laboratory report" not in self.confirmation_method):
        #         self.issues.append(
        #             'Since correct case status is probable confirmation method should include "Laboratory report".'
        #         )
        #     elif (self.status == "S") and (
        #         "Clinical diagnosis (non-laboratory confirmed)" not in self.confirmation_method
        #     ):
        #         self.issues.append(
        #             'Since correct case status is suspect confirmation method should include "Clinical diagnosis (non-laboratory confirmed)".'
        #         )
        # else:
        #     self.issues.append("Confirmation method is missing")
        #     print(f"confirmation_method: {self.confirmation_method}")

    def CheckConfirmationMethod(self):
        """Confirmation Method must be blank or consistent with correct case status."""
        self.confirmation_method = self.ReadText('//*[@id="INV161"]')
        if self.confirmation_method:
            if (self.status == "C") and ("Laboratory confirmed" not in self.confirmation_method):
                self.issues.append(
                    'Since correct case status is confirmed confirmation method should include "Laboratory confirmed".'
                )
            elif (self.status == "P") and ("Laboratory report" not in self.confirmation_method):
                self.issues.append(
                    'Since correct case status is probable confirmation method should include "Laboratory report".'
                )
            elif (self.status == "S") and (
                "Clinical diagnosis (non-laboratory confirmed)" not in self.confirmation_method
            ):
                self.issues.append(
                    'Since correct case status is suspect confirmation method should include "Clinical diagnosis (non-laboratory confirmed)".'
                )
        else:
            self.issues.append("Confirmation method is missing")
            print(f"confirmation_method: {self.confirmation_method}")

    def CheckDetectionMethod(self):
        """Ensure Detection Method is not blank."""
        detection_method = self.CheckForValue(
            '//*[@id="INV159"]', "Detection method is blank."
        )
        if not detection_method:
            self.issues.append("Detection method is missing")
            print(f"detection_method: {detection_method}")

    def CheckConfirmationDate(self):
        """Confirmation date must be on or after report/received/investigation date."""
        confirmation_date = self.ReadDate('//*[@id="INV162"]')
        if not confirmation_date:
            self.issues.append("Confirmation date is blank.")
            print(f"confirmation_date: {confirmation_date}")
        else:
            if self.received_date and confirmation_date < self.received_date:
                self.issues.append("Confirmation date cannot be prior to report date.")
                print(f"confirmation_date: {confirmation_date}")
            if self.report_date and confirmation_date < self.report_date:
                self.issues.append("Confirmation date cannot be prior to report date.")
                print(f"confirmation_date: {confirmation_date}")
            if (
                self.investigation_start_date
                and confirmation_date < self.investigation_start_date
            ):
                self.issues.append(
                    "Confirmation date cannot be before investigation start date."
                )
                print(f"confirmation_date: {confirmation_date}")
            if confirmation_date > self.now:
                self.issues.append("Confirmation date cannot be in the future.")
                print(f"confirmation_date: {confirmation_date}")
        return confirmation_date

    def CheckWhereDisease(self):
        """Where disease acquired check (from older ANA logic)."""
        where_was_disease_acquired = self.ReadText('//*[@id="INV152"]')

        if where_was_disease_acquired == "Indigenous":
            if self.travel_outside_home and "Yes" in self.travel_outside_home:
                self.issues.append(
                    "Disease acquired should not be “indigenous” if any travel outside home county."
                )
            elif self.travel_outside_home and any(
                option != "No" for option in self.travel_outside_home
            ):
                self.issues.append(
                    "Cannot be indigenous without travel questions all being no."
                )

            if (self.culture_done and self.culture_done not in ["No", "Unknown"]) or (
                self.culture_positive and self.culture_positive not in ["No", "Unknown"]
            ):
                self.issues.append(
                    "Culture done and Culture positive should be blank or unknown, "
                    "Where disease was acquired says Indigenous but travel history is unknown"
                )
        else:
            if self.travel_outside_home and all(
                option == "No" for option in self.travel_outside_home
            ):
                self.issues.append(
                    "If all 3 travel questions are no, where was disease acquired should be indigenous."
                )

    ####################### Patient Status Check Methods ############################

    def CheckDeath(self):
        """If died from illness is yes or no, need a death date."""
        self.patient_die_from_illness = self.CheckForValue(
            '//*[@id="INV145"]',
            "Died from illness must be yes or no.",
        )
        if self.patient_die_from_illness == "Yes":
            death_date = self.ReadDate('//*[@id="INV146"]')
            if not death_date:
                self.issues.append("Date of death is blank.")
            elif death_date > self.now:
                self.issues.append("Date of death cannot be in the future")

    def CheckHospitalization(self):
        """Read hospitalization status. If yes need date and hospital."""
        self.hospitalization_indicator = self.ReadText('//*[@id="INV128"]')
        if self.hospitalization_indicator == "Yes":
            hospital_name = self.ReadText('//*[@id="INV184"]')
            if not hospital_name:
                self.issues.append("Hospital name missing.")
                print(f"hospitalization, hospital_name: {hospital_name}")
            self.admission_date = self.ReadDate('//*[@id="INV132"]')
            if not self.admission_date:
                self.issues.append("Admission date is blank.")
                print(f"hospitalization, admission_date: {self.admission_date}")
            elif self.admission_date > self.now:
                self.issues.append("Admission date cannot be in the future.")
                print(f"hospitalization, admission_date: {self.admission_date}")
        elif self.hospitalization_indicator not in ["Yes", "No"]:
            self.issues.append("Patient hospitalization status not indicated.")

    def CheckAdmissionDate(self):
        """Check for hospital admission date."""
        self.admission_date = self.ReadDate('//*[@id="INV132"]')
        if not self.admission_date:
            self.issues.append("Admission date is missing.")
            print(f"admission_date: {self.admission_date}")
        elif self.admission_date > self.now:
            self.issues.append("Admission date cannot be in the future.")
            print(f"admission_date: {self.admission_date}")

    def CheckDischargeDate(self):
        """Check for hospital discharge date."""
        discharge_date = self.ReadDate('//*[@id="INV133"]')
        if (
            self.patient_die_from_illness == "Yes"
            and self.hospitalization_indicator == "Yes"
            and not discharge_date
        ):
            self.issues.append("Discharge date is blank.")
        if discharge_date:
            if self.admission_date and discharge_date < self.admission_date:
                self.issues.append("Discharge date must be after admission date.")
                print(f"discharge_date: {discharge_date}")
            elif discharge_date > self.now:
                self.issues.append("Discharge date cannot be in the future.")
                print(f"discharge_date: {discharge_date}")

    def CheckIllnessDurationUnits(self):
        """Read Illness duration units, should be either Day, Month, or Year."""
        self.IllnessDurationUnits = self.ReadText('//*[@id="INV140"]')
        if self.IllnessDurationUnits:
            if self.IllnessDurationUnits not in ("Day", "Month", "Year"):
                self.issues.append(
                    "Illness Duration is not in Days, Months, or Years."
                )
                print(f"illness_duration_units: {self.IllnessDurationUnits}")

    ############MMWR check should not be blank####################

    def CheckMmwrWeek(self):
        """MMWR week must be provided."""
        mmwr_week = self.ReadText('//*[@id="INV165"]')
        if not mmwr_week:
            self.issues.append("MMWR Week is blank.")

    def CheckMmwrYear(self):
        """MMWR year must be provided and match specimen collection ISO week year (handles 53-week years)."""
        mmwr_year = self.ReadText('//*[@id="INV166"]')
        if not mmwr_year:
            self.issues.append("MMWR Year is blank.")
        elif self.collection_date and int(mmwr_year) != self.collection_date.isocalendar().year:
            self.issues.append(
                f"MMWR Year does not match specimen collection ISO week year ({self.collection_date.isocalendar().year})."
            )
            print(f"mmwr_year: {mmwr_year}, collection_date: {self.collection_date}, isocalendar_year: {self.collection_date.isocalendar().year}")

    ############### Performing Lab Check Methods ##################################

    def CheckPerformingLaboratory(self):
        """Ensure that performing laboratory is not empty."""
        reporting_organization = self.ReadText('//*[@id="ME6105"]')
        if not reporting_organization:
            self.issues.append("Performing laboratory is blank.")

    ############################# Data Reading/Validation Methods ##################################

    def CheckForValue(self, xpath, blank_message):
        """If value is blank add appropriate message to list of issues."""
        value = self.find_element(By.XPATH, xpath).get_attribute("innerText")
        value = value.replace("\n", "")
        if not value:
            self.issues.append(blank_message)
        return value

    def check_for_value_bool(self, path):
        """Return boolean value based on whether a value is present."""
        value = self.ReadText(path)
        return bool(value)

    def ReadDate(self, xpath, attribute="innerText"):
        """Read date from NBS and return a datetime.date object."""
        date = self.find_element(By.XPATH, xpath).get_attribute(attribute)
        try:
            date_pattern = r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+$"
            if re.match(date_pattern, date.strip()):
                date = datetime.strptime(date.strip(), "%Y-%m-%d %H:%M:%S.%f").date()
            else:
                date = datetime.strptime(date.strip(), "%m/%d/%Y").date()
        except ValueError:
            date = ""
        return date

    def CheckIfField(self, parent_xpath, child_xpath, value, message):
        """If parent field is value ensure that child field is not blank."""
        parent = self.find_element(By.XPATH, parent_xpath).get_attribute("innerText")
        parent = parent.replace("\n", "")
        if parent == value:
            child = self.find_element(By.XPATH, child_xpath).get_attribute("innerText")
            child = child.replace("\n", "")
            if not child:
                self.issues.append(message)

    def ReadText(self, xpath):
        """
        Read the text of any web element identified by an Xpath
        and remove leading and trailing carriage returns.
        Includes retry logic.
        """
        from time import sleep

        for i in range(self.num_attempts):
            try:
                value = self.find_element(By.XPATH, xpath).get_attribute("innerText")
                value = value.replace("\n", "")
                return value
            except NoSuchElementException:
                sleep((i + 1) * 10)
                print(f"no value ReadText for xpath: {xpath}, retry_number:{i}")
            except TimeoutException:
                print(
                    f"Timeout waiting for ReadText for xpath: {xpath}, retry_number: {i}"
                )
            except StaleElementReferenceException:
                sleep((i + 1) * 10)
                print(
                    f"StaleElementReferenceException for ReadText for xpath: {xpath}, trying again... retry_number: {i}"
                )
            except Exception as e:
                print(
                    f"{e} has occured for ReadText for xpath: {xpath}, retry_number: {i}"
                )

    def ReadElement(self, xpath):
        """Read the web element identified by an Xpath."""
        try:
            element = self.find_element(By.XPATH, xpath)
            return element
        except Exception as e:
            print(f"Error reading element for xpath: {xpath}, {e}")
            return None

    def ReadTableToDF(self, xpath):
        """Read tables into pandas Data Frames for easy manipulation."""
        try:
            html = self.find_element(By.XPATH, xpath).get_attribute("innerHTML")
            soup = BeautifulSoup(html, "html.parser")
            table = pd.read_html(StringIO(str(soup)))[0]
            table.fillna("", inplace=True)
        except ValueError:
            table = None
        return table

    def ReadPatientID(self):
        """Read patient ID from within patient profile."""
        patient_id = self.ReadText(
            '//*[@id="bd"]/table[3]/tbody/tr[1]/td[2]/span[2]'
        )
        return patient_id

    def Sleep(self):
        """Pause all action for the specified number of seconds."""
        self.slept += 1
        for i in range(self.sleep_duration):
            time_remaining = self.sleep_duration - i
            print(
                f"Sleeping for: {time_remaining//60:02d}:{time_remaining%60:02d}",
                end="\r",
                flush=True,
            )
            time.sleep(1)
        print("Sleeping for: 00:00", end="\r", flush=True)

    ######################## Email / Config Methods ########################

    def send_email_local_outlook_client(
        self, recipient, cc, subject, message, attachment=None
    ):
        """Send an email using local Outlook client."""
        self.clear_gen_py()
        outlook = win32.Dispatch("outlook.application")
        mail = outlook.CreateItem(0)
        mail.GetInspector
        mail.To = recipient
        mail.CC = cc
        mail.Subject = subject
        mail.Body = message
        if attachment is not None:
            mail.Attachments.Add(attachment)
        mail.Send()

    def clear_gen_py(self):
        """Clear the contents of the gen_py directory to ensure emails can always be sent."""
        current_user = getpass.getuser().lower()
        gen_py_path = r"C:\Users" + "\\" + current_user + r"\AppData\Local\Temp\gen_py"
        gen_py_path = Path(gen_py_path)

        if gen_py_path.exists() and gen_py_path.is_dir():
            rmtree(gen_py_path)

    def read_config(self):
        """Read in data from config.cfg."""
        self.config = configparser.ConfigParser()
        self.config.read("config.cfg")

    def get_email_info(self):
        """Read information required for NBSbot to send emails via SMTP."""
        self.smtp_server = self.config.get("email", "smtp_server")
        self.nbsbot_email = self.config.get("email", "nbsbot_email")
        self.covid_informatics_list = self.config.get(
            "email", "covid_informatics_list"
        )
        self.covid_admin_list = self.config.get("email", "covid_admin_list")
        self.covid_commander = self.config.get("email", "covid_commander")

    def get_usps_user_id(self):
        """Extract the USPS User ID from the config file for zip_code_lookup."""
        self.usps_user_id = self.config.get("usps", "user_id")

    def send_smtp_email(self, receiver, subject, body, email_name):
        """Send emails using an SMTP server."""
        message = EmailMessage()
        message.set_content(body)
        message["Subject"] = subject
        message["From"] = self.nbsbot_email
        message["To"] = ", ".join([receiver])
        try:
            smtpObj = smtplib.SMTP(self.smtp_server)
            smtpObj.send_message(message)
            print(f"Successfully sent {email_name}.")
        except smtplib.SMTPException:
            print(f"Error: unable to send {email_name}.")

    ######################## Window / Checkbox / Lookup ########################

    def get_main_window_handle(self):
        """
        Run after login to identify and store the main window handle
        so that handles for pop-up windows can be differentiated.
        """
        self.main_window_handle = self.current_window_handle

    def switch_to_secondary_window(self):
        """Set a secondary window as the current window in order to interact with the pop up."""
        new_window_handle = None
        for handle in self.window_handles:
            if handle != self.main_window_handle:
                new_window_handle = handle
                break
        if new_window_handle:
            self.switch_to.window(new_window_handle)

    def select_checkbox(self, xpath):
        """
        Ensure a given checkbox or radio button is selected.
        If not selected then click it to select.
        """
        checkbox = self.find_element(By.XPATH, xpath)
        if not checkbox.is_selected():
            checkbox.click()

    def unselect_checkbox(self, xpath):
        """
        Ensure a given checkbox or radio button is not selected.
        If selected then click it to un-select.
        """
        checkbox = self.find_element(By.XPATH, xpath)
        if checkbox.is_selected():
            checkbox.click()

    def county_lookup(self, city, state):
        """Use the Nominatim geocode service via geopy to look up county."""
        geolocator = Nominatim(user_agent="nbsbot")
        location = geolocator.geocode(city + ", " + state)
        if location:
            location = location[0].split(", ")
            county = [x for x in location if "County" in x]
            if len(county) == 1:
                county = county[0].split(" ")[0]
            else:
                county = ""
        else:
            county = ""
        return county

    def zip_code_lookup(self, street, city, state):
        """
        Given a street address, city, and state use the USPS API
        via the usps Python package to lookup the associated zip code.
        """
        address = Address(
            name="",
            address_1=street,
            city=city,
            state=state,
            zipcode="",
        )
        usps = USPSApi(self.usps_user_id, test=True)
        try:
            validation = usps.validate_address(address)
            if "Address Not Found" not in json.dumps(validation.result):
                zip_code = validation.result["AddressValidateResponse"]["Address"]["Zip5"]
            else:
                zip_code = ""
        except Exception:
            zip_code = ""
        return zip_code

    def check_for_error_page(self):
        """See if NBS encountered an error."""
        error_page_path = "/html/body/table/tbody/tr/td/table/tbody/tr[2]/td/table/tbody/tr/td/table/tbody/tr[2]/td[1]"
        try:
            if self.ReadText(error_page_path) == "\xa0Error Page":
                nbs_error = True
            else:
                nbs_error = False
        except Exception:
            nbs_error = False
        return nbs_error

    def go_to_home_from_error_page(self):
        """Go to NBS Home page from an NBS error page."""
        xpath = "/html/body/table/tbody/tr/td/table/tbody/tr[1]/td/table/tbody/tr/td/table/tbody/tr/td[1]/a"
        for _ in range(self.num_attempts):
            try:
                WebDriverWait(self, self.wait_before_timeout).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                self.find_element(By.XPATH, xpath).click()
                self.home_loaded = True
                break
            except TimeoutException:
                self.home_loaded = False
        if not self.home_loaded:
            sys.exit(
                print(
                    f"Made {self.num_attempts} unsuccessful attempts to load Home page. A persistent issue with NBS was encountered."
                )
            )
    
    def save_and_print_results(self, 
            bot: str,
            data_frame: dict,
            file_suffix=""
        ):
        """Helper function to save results to Excel - appends if file exists"""
        try: 
            if len(data_frame['Inv ID']) > 0:
                print(f"Saving results: {', '.join([str(v) for k, v in data_frame.items()])}")
                new_data = pd.DataFrame(
                data_frame)
                
                filename = f"saved/{bot}/{bot}_bot_activity_{file_suffix}_{datetime.now().date().strftime('%m_%d_%Y')}.xlsx"
                
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
        except Exception as e:
            print(f"an error occured: {str(e)}")
            return False
    
    def disease_case_count(self, bot, default_count):
        # If SortQueue found no matching condition option, the queue could not be
        # filtered to this disease, so NBS is showing every case. The true count
        # for this disease is 0 -- don't misread the unfiltered total as cases.
        if getattr(self, "condition_filter_matches", None) == 0:
            print(f"No '{bot}' condition option in the queue filter; 0 cases.")
            return 0
        try:
            # Get the case count element using the provided XPath
            case_count_element = self.find_element(By.XPATH, '//*[@id="bd"]/table[2]/tbody/tr/td/span[2]/b')
            case_count_text = case_count_element.text.strip()
            print(f"Case count text found: '{case_count_text}'")
            
            # Parse the count - Format: "Results 1 to 1 of 1" or "Results 1 to 16 of 45"
            match = re.search(r'Results\s+\d+\s+to\s+\d+\s+of\s+(\d+)', case_count_text)
            if match:
                disease_case_count = int(match.group(1))
                print(f"Total {bot} cases in queue: {disease_case_count}")
            else:
                raise ValueError(f"Could not parse count from: '{case_count_text}'")
            
        except Exception as e:
            print(f"Error getting case count: {e}")
            # Fallback: count table rows
            try:
                case_rows = self.find_elements(By.XPATH, '/html/body/div[2]/form/div/table[2]/tbody/tr/td/table/tbody/tr')
                disease_case_count = len(case_rows)
                print(f"Fallback: Found {disease_case_count} case rows in table")
            except:
                # Ultimate fallback
                disease_case_count = default_count
                print(f"Could not determine case count, using default value of {default_count}")
        finally:
            return disease_case_count


    ################# Notification & Comments ############

    def write_general_comment(self, note):
        """Write a note in the general comments box of an investigation."""
        xpath = '//*[@id="INV167"]'
        self.find_element(By.XPATH, xpath).send_keys(note)

    def RejectNotification(self, n: int = 1):
        """
        Reject notification on nth case in notification queue.
        To be used when issues were encountered during review of the case.
        """
        print("issues seen in reject:", self.issues)
        reject_path = f'//*[@id="parent"]/tbody/tr[{n}]/td[2]/img'
        main_window_handle = self.current_window_handle
        WebDriverWait(self, self.wait_before_timeout).until(
            EC.element_to_be_clickable((By.XPATH, reject_path))
        )
        self.find_element(By.XPATH, reject_path).click()
        rejection_comment_window = None
        print("rejection windows: ", self.window_handles, "current_window: ", main_window_handle)
        handles = self.window_handles
        
        for handle in handles:
            self.switch_to.window(handle)
            print(self.title)
            # if handle != main_window_handle:
            #     rejection_comment_window = handle
            #     break
        rejection_comment_window = handles[2] if len(handles) > 2 else handles[1]
        if rejection_comment_window:
            self.switch_to.window(rejection_comment_window)
            timestamp = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
            self.issues.append("-nbsbot " + timestamp)
            self.find_element(By.XPATH, '//*[@id="rejectComments"]').send_keys(
                " ".join(self.issues)
            )
            self.find_element(
                By.XPATH, "/html/body/form/table/tbody/tr[3]/td/input[1]"
            ).click()
            self.switch_to.window(main_window_handle)
            self.num_rejected += 1

    def ApproveNotification(self):
        """Approve notification on first case in notification queue."""
        main_window_handle = self.current_window_handle
        self.find_element(By.XPATH, '//*[@id="createNoti"]').click()
        approval_comment_window = None
        handles = self.window_handles
        for handle in handles:
            self.switch_to.window(handle)
            print(self.title)

        approval_comment_window = handles[2] if len(handles) > 2 else handles[1]
        # for handle in self.window_handles:
        #     if handle != main_window_handle:
        #         approval_comment_window = handle
        #         break
        if approval_comment_window:
            self.switch_to.window(approval_comment_window)
            self.find_element(By.XPATH, '//*[@id="botcreatenotId"]/input[1]').click()
            self.switch_to.window(main_window_handle)
            self.num_approved += 1

    # Email summary methods for specific bots

    def SendManualReviewEmail(self):
        """Send email containing NBS IDs that required manual review (older COVID bot)."""
        if (len(self.not_a_case_log) > 0) or (len(self.lab_data_issues_log) > 0):
            subject = "Cases Requiring Manual Review"
            email_name = "manual review email"
            body = (
                "COVID Commander,\nThe case(s) listed below have been moved to the rejected notification queue and require manual review.\n\nNot a case:"
            )
            for id_value in self.not_a_case_log:
                body = body + f"\n{id_value}"
            body = body + "\n\nAssociated lab issues:"
            for id_value in self.lab_data_issues_log:
                body = body + f"\n{id_value}"
            body = body + "\n\n-Nbsbot"
            self.send_smtp_email(self.covid_commander, subject, body, email_name)
            self.not_a_case_log = []
            self.lab_data_issues_log = []

    def SendBotRunEmail(self):
        """Send a summary email when HepB or iGAS case closing bot finishes."""
        if self.HepB_notification_bot:
            bot_name = "Hepatitis B Case Closing Bot"
        elif self.iGAS_notification_bot:
            bot_name = "iGAS Case Closing Bot"
        else:
            bot_name = "NBS Bot"

        completion_message = (
            f"{bot_name} has finished running on "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}."
        )
        self.send_smtp_email(
            "disease.reporting@maine.gov",
            f"{bot_name} ",
            completion_message,
            "Daily Bot Run Notification",
        )

    def CreateExcelSheet(self):
        """Create an Excel spreadsheet summarizing the cases reviewed."""
        print("ending, printing, saving")
        bot_act = pd.DataFrame(
            {
                "Inv ID": self.reviewed_ids,
                "Action": self.what_do,
                "Reason": self.reason,
            }
        )
        if self.HepB_notification_bot:
            bot_act.to_excel(
                f"saved/HepB/HepB_bot_activity_{datetime.now().date().strftime('%m_%d_%Y %H:%M:%S')}.xlsx"
            )
            print("excel sheet created")
        if self.iGAS_notification_bot:
            bot_act.to_excel(
                f"saved/iGAS/iGAS_bot_activity_{datetime.now().date().strftime('%m_%d_%Y %H:%M:%S')}.xlsx"
            )
            print("excel sheet created")
