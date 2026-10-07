import time
import datetime
import sys
from selenium.webdriver.common.by import By
from logger import log
from config import load_config
from browser import BrowserManager
from session import SessionManager
from monitor import Monitor
from notify import Notifier
from recover import CloudflareSolver, LoginSolver
from license_manager import LicenseManager

class VisaBot:
    def __init__(self, overrides=None):
        self.config = load_config()
        if overrides:
            if overrides.get("cities"):
                self.config["cities"] = overrides["cities"]
            if overrides.get("dates"):
                self.config["dates"] = overrides["dates"]
        self.bm = BrowserManager()
        self.session = SessionManager(self.bm)
        self.monitor = Monitor(self.bm, self.config)
        self.notifier = Notifier()
        self.cf_solver = CloudflareSolver(self.bm)
        self.login_solver = LoginSolver(self.bm, self.config)
        self.state = "INIT"
        self.metrics = {"cf_encounters": 0, "cf_successes": 0, "kicked_out": 0, "cycles": 0}
        
    def run(self):
        log.info("Starting Visa Bot State Machine...")
        
        
        while True:
            try:
                if self.state == "INIT":
                    self.bm.start()
                    # Determine URL from config if present, or fallback to default
                    url = "https://www.usvisascheduling.com/en-US/"
                    self.bm.get_url(url)
                    self.state = "LOGIN_WAIT"
                    
                elif self.state == "LOGIN_WAIT":
                    log.info("Checking page state. Waiting automatically...")
                    page_source = self.bm.driver.page_source.lower()
                    page_title = self.bm.driver.title.lower()
                    
                    if "error 1015" in page_source or "rate_limited" in page_source:
                        wait_time = float(self.config.get('wait_times', {}).get('rate_limit_wait_time', 600.0))
                        log.error(f"Cloudflare Error 1015 (Rate Limited) detected! The IP address is blocked.")
                        self.notifier.notify_warning(f"Cloudflare 1015 Rate Limit hit! Waiting {wait_time} seconds before rotating proxy and restarting...")
                        time.sleep(wait_time)
                        self.bm.stop()
                        time.sleep(5)
                        self.state = "INIT"
                        continue

                    if "sorry, you have been blocked" in page_source or "524: a timeout" in page_title or "502 bad gateway" in page_title or "504 gateway time-out" in page_title or "host error" in page_source:
                        log.error("Hard Cloudflare block or Server Timeout (5xx) detected! Restarting browser session in 30 seconds...")
                        self.notifier.notify_warning("Server Timeout or Block detected! Rotating proxy and restarting session...")
                        time.sleep(30)
                        self.bm.stop()
                        time.sleep(5)
                        self.state = "INIT"
                        continue
                        
                    if self.cf_solver.is_cloudflare_challenge():
                        self.metrics["cf_encounters"] += 1
                        if self.cf_solver.solve():
                            self.metrics["cf_successes"] += 1
                            log.info("Bypassed Cloudflare, checking page state...")
                            self.notifier.notify_info("Successfully bypassed Cloudflare challenge dynamically!")
                            time.sleep(5)
                            continue
                        else:
                            log.error("Cloudflare bypass failed dynamically. Restarting browser session to get a fresh fingerprint/proxy...")
                            self.bm.stop()
                            time.sleep(5)
                            self.state = "INIT"
                            continue
                            
                    if self.login_solver.is_login_page():
                        if self.login_solver.solve_login():
                            time.sleep(5)
                        else:
                            self.notifier.notify_warning("Login failed. Please check credentials or network.")
                            time.sleep(5)
                            
                    if self.login_solver.is_security_questions_page():
                        if self.login_solver.solve_security_questions():
                            time.sleep(5)
                            
                    if self.bm.switch_to_main_window():
                        # If we are on the dashboard/home page
                        try:
                            nav_btn = self.bm.driver.find_elements(
                                By.XPATH, 
                                "//a[contains(text(), 'Continue Application')] | "
                                "//a[contains(text(), 'Schedule Appointment')] | "
                                "//a[contains(@href, 'ofc-schedule')] | "
                                "//a[contains(@class, 'button') and (contains(text(), 'Continue') or contains(text(), 'Schedule'))]"
                            )
                            if nav_btn and nav_btn[0].is_displayed():
                                btn_text = nav_btn[0].text or "navigation link"
                                log.info(f"Found '{btn_text}' button on dashboard! Clicking it...")
                                self.bm.driver.execute_script("arguments[0].click();", nav_btn[0])
                                time.sleep(5)
                            elif "ofc-schedule" not in self.bm.driver.current_url.lower() and "b2clogin" not in self.bm.driver.current_url.lower():
                                # Fallback: Navigate directly to the ofc-schedule page if stuck on dashboard home
                                log.info("On dashboard home page. Navigating directly to OFC Schedule page...")
                                self.bm.get_url("https://www.usvisascheduling.com/en-US/ofc-schedule/")
                                time.sleep(5)
                        except Exception as nav_e:
                            log.warning(f"Error navigating from dashboard: {nav_e}")
                            
                        if self.bm.driver.find_elements(By.XPATH, "//h2[text()='Group Members']"):
                            log.info("Detected navigation to OFC Post page.")
                            self.bm.disable_alerts()
                            self.monitor.reset_timer()
                            self.state = "MONITORING"
                        else:
                            time.sleep(2)
                    else:
                        time.sleep(2)
                        
                elif self.state == "MONITORING":
                    # Call the monitor logic which handles cycling through cities
                    result = self.monitor.cycle_cities(self.session)
                    status = result.get("status")
                    
                    if status == "SLOT_BOOKED":
                        log.info("Slot successfully booked! Shutting down.")
                        self.notifier.notify_slot_booked(
                            result.get("city"), 
                            result.get("date"), 
                            result.get("time"), 
                            result.get("allocation")
                        )
                        self.state = "SHUTDOWN"
                        
                    elif status == "RATE_LIMITED":
                        wait_time = float(self.config.get('wait_times', {}).get('rate_limit_wait_time', 600.0))
                        log.error(f"Rate limit hit during monitoring. Pausing for {wait_time} seconds...")
                        self.notifier.notify_warning(f"Rate limit hit! Waiting {wait_time} seconds before rotating proxy and restarting...")
                        time.sleep(wait_time)
                        self.bm.stop()
                        time.sleep(5)
                        self.state = "INIT"
                        
                    elif status == "SOFT_BAN":
                        wait_time = 7200  # 2 hours
                        log.error(f"CRITICAL: Account Soft Banned (Access Limitation). Pausing bot for {wait_time} seconds (2 hours) to let the ban expire...")
                        self.notifier.notify_warning(f"Account Soft Banned by US Visa portal! Waiting 2 hours before resuming...")
                        time.sleep(wait_time)
                        self.bm.stop()
                        time.sleep(5)
                        self.state = "INIT"
                        
                    elif status == "KICKED_OUT":
                        self.metrics["kicked_out"] += 1
                        log.error("Group Members Label is not present. Redirected to home?")
                        self.bm.dump_diagnostics(attempt=self.metrics["kicked_out"])
                        
                        if self.cf_solver.is_cloudflare_challenge():
                            self.metrics["cf_encounters"] += 1
                            if self.cf_solver.solve():
                                self.metrics["cf_successes"] += 1
                                log.info("Successfully recovered from Cloudflare block during monitoring.")
                                self.state = "MONITORING"
                                continue
                                
                        self.state = "LOGIN_WAIT"
                        
                    elif status == "CYCLE_COMPLETE":
                        # One full loop over all configured cities finished
                        self.metrics["cycles"] += 1
                        log.info(f"Completed {self.metrics['cycles']} full checking cycles. Restarting monitoring loop...")
                        # Monitor class already handles wait times between loops
                        self.state = "MONITORING"
                        
                elif self.state == "SHUTDOWN":
                    self.bm.stop()
                    log.info("Bot execution completed.")
                    break
                    
            except Exception as e:
                log.error(f"Fatal exception in state {self.state}: {e}")
                self.bm.dump_diagnostics(attempt="fatal")
                log.info(f"Session metrics: {self.metrics}")
                log.info("Attempting basic recovery in 10 seconds...")
                time.sleep(10)
                try:
                    self.bm.stop()
                except:
                    pass
                self.state = "INIT"

def interactive_setup():
    if "--auto" in sys.argv:
        print("Running in unattended mode using config.json defaults...")
        return None

    print("=========================================")
    print("        US Visa Automation Bot           ")
    print("=========================================")
    print("0: CHENNAI VAC")
    print("1: HYDERABAD VAC")
    print("2: KOLKATA VAC")
    print("3: MUMBAI VAC")
    print("4: NEW DELHI VAC")
    
    city_map = {
        "0": "CHENNAI VAC",
        "1": "HYDERABAD VAC",
        "2": "KOLKATA VAC",
        "3": "MUMBAI VAC",
        "4": "NEW DELHI VAC"
    }
    
    cities = []
    ofc_input = input("Please Select OFC Post. Enter numbers separated by commas (e.g., 0,4): ")
    for choice in ofc_input.split(","):
        choice = choice.strip()
        if choice in city_map:
            cities.append(city_map[choice])
            print(f"Selected OFC Post: {city_map[choice]}")
            
    if not cities:
        print("No valid cities selected. Defaulting to NEW DELHI VAC")
        cities = ["NEW DELHI VAC"]
        
    dates = []
    user_years = input("\nPlease Select Years. Enter Years separated by commas Like:- 2026,2027: ")
    for year in user_years.split(","):
        year = year.strip()
        if not year: continue
        
        print("\n0: JAN | 1: FEB | 2: MAR | 3: APR | 4: MAY | 5: JUN")
        print("6: JUL | 7: AUG | 8: SEP | 9: OCT | 10: NOV | 11: DEC")
        user_months = input(f"Please Select Months for Year {year}. Enter numbers separated by commas Like:- 6,7: ")
        
        for month in user_months.split(","):
            month = month.strip()
            if not month: continue
            
            date_range = input(f"Please Enter Date Range for Month {month} (Like: 1-30): ")
            dates.append({
                "year": year,
                "month": month,
                "range": date_range.strip()
            })
            
    print("\nSetup Complete! Starting bot...\n")
    return {"cities": cities, "dates": dates}

if __name__ == "__main__":
    import multiprocessing
    import sys
    import traceback
    multiprocessing.freeze_support()
    try:
        # 1. Verify License (HWID Lock)
        # Change this URL to your actual Pastebin or GitHub Raw text link
        database_url = "https://pastebin.com/raw/EUnMHhKq"
        lm = LicenseManager(database_url)
        lm.verify_license()

        # 2. Start Bot
        overrides = interactive_setup()
        bot = VisaBot(overrides)
        bot.run()
    except Exception as e:
        print("\n=========================================")
        print("CRITICAL STARTUP ERROR:")
        traceback.print_exc()
        print("=========================================\n")
        time.sleep(10)
        sys.exit(1)
