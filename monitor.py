import time
import random
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from logger import log
from calendar_handler import CalendarHandler
from notify import Notifier

class Monitor:
    def __init__(self, browser_manager, config):
        self.bm = browser_manager
        self.config = config
        self.notifier = Notifier()
        self.calendar = CalendarHandler(self.bm, self.config)
        self.ofc_posts = self.config.get('cities', [])
        
        # Timing settings
        waits = self.config.get('wait_times', {})
        self.bot_run_interval_start = float(waits.get('bot_run_interval_start_time', 5))
        self.bot_run_interval_end = float(waits.get('bot_run_interval_end_time', 15))
        
        self.pause_duration_start = float(waits.get('pause_duration_start_time', 30))
        self.pause_duration_end = float(waits.get('pause_duration_end_time', 45))
        
        self.outer_start_time = float(waits.get('outer_start_time', 2))
        self.outer_end_time = float(waits.get('outer_end_time', 12.9))
        
        self.inner_start_time = float(waits.get('inner_start_time', 1.1))
        self.inner_end_time = float(waits.get('inner_end_time', 3))
        
        self.city_dropdown_wait_time = float(waits.get('city_dropdown_wait_time', 5))
        
        self.start_time = time.time()
        self.bot_run_interval = random.uniform(self.bot_run_interval_start * 60, self.bot_run_interval_end * 60)
        self.pause_duration = random.uniform(self.pause_duration_start, self.pause_duration_end)
        dates_raw = self.config.get('dates', [])
        self.dates_filter_list = [f"{d['year']}|{d['month']}|{d['range']}" for d in dates_raw]
        self.year_numbers = list(set([o.split("|")[0] for o in self.dates_filter_list]))

    def reset_timer(self):
        self.start_time = time.time()

    def is_element_present(self, locator, timeout=0):
        try:
            if timeout > 0:
                wait = WebDriverWait(self.bm.driver, timeout, poll_frequency=0.2)
                element = wait.until(EC.presence_of_element_located((By.XPATH, locator)))
                return element.is_displayed()
            else:
                element = self.bm.driver.find_element(By.XPATH, locator)
                return element.is_displayed()
        except Exception as e:
            # Removed log.error here as is_element_present is expected to return False if not found
            return False

    def select_dropdown(self, locator, value, by_value=False):
        # If locator has multiple XPaths separated by |, split and try each
        locators = [x.strip() for x in locator.split("|")]
        for loc in locators:
            try:
                element = self.bm.driver.find_element(By.XPATH, loc)
                if element:
                    select = Select(element)
                    if by_value:
                        select.select_by_value(value)
                    else:
                        select.select_by_visible_text(value)
                    return True
            except Exception as e:
                # log.warning(f"Failed to select dropdown {loc}: {e}") # Too noisy
                continue
        return False

    def cycle_cities(self, session_manager):
        driver = self.bm.driver
        ofc_post_city_select_dropdown_path = "//select[@id='post_city'] | //select[contains(@id, 'post_city')] | //label[contains(text(), 'OFC Post')]/following::select[1] | //select[contains(@name, 'post_city')]"
        ofc_post_city_calendar_date_picker = "//div[@id='ui-datepicker-div']"
        ofc_post_city_calendar_date_picker_year = "//select[@class='ui-datepicker-year']"
        ofc_post_city_calendar_date_picker_month = "//select[@class='ui-datepicker-month']"
        group_members_path = "//h2[text()='Group Members']"

        for post_city in self.ofc_posts:
            current_time = time.time()
            elapsed_time = current_time - self.start_time
            if elapsed_time >= self.bot_run_interval:
                self.select_dropdown(ofc_post_city_select_dropdown_path, "")
                session_manager.clear_session()
                log.info(f"Pausing for '{self.pause_duration}' Seconds after every '{self.bot_run_interval_start}' to '{self.bot_run_interval_end}' Minutes...")
                time.sleep(self.pause_duration)
                
                self.bot_run_interval = random.uniform(self.bot_run_interval_start * 60, self.bot_run_interval_end * 60)
                self.pause_duration = random.uniform(self.pause_duration_start, self.pause_duration_end)
                self.start_time = time.time()

            page_source = self.bm.driver.page_source.lower()
            if "access limitation" in page_source or "prohibited conduct" in page_source:
                return {"status": "SOFT_BAN"}
                
            too_many_requests_path = "//*[contains(text(), 'The system is processing too many requests')]"
            if self.is_element_present(too_many_requests_path) or "error 1015" in page_source or "rate_limited" in page_source:
                return {"status": "RATE_LIMITED"}

            if self.is_element_present(group_members_path):

                if self.is_element_present(ofc_post_city_select_dropdown_path, timeout=8):
                    if len(self.ofc_posts) == 1:
                        self.select_dropdown(ofc_post_city_select_dropdown_path, "")
                        time.sleep(random.uniform(0.2, 0.7))

                    self.select_dropdown(ofc_post_city_select_dropdown_path, post_city)
                    
                    self.calendar.wait_for_any_element_to_be_visible(
                        ofc_post_city_calendar_date_picker, 
                        "//div[not(contains(@style,'none'))]/div[text()='No Slots Available']", 
                        self.city_dropdown_wait_time
                    )
                    time.sleep(random.uniform(0.5, 1))

                    if not self.is_element_present(ofc_post_city_calendar_date_picker) and not self.is_element_present(group_members_path):
                        log.info("Date Input Not Loaded or Found So Maybe OFC Page Navigated to any other page or Something Went Wrong.")
                        return {"status": "KICKED_OUT"}

                    if self.is_element_present(ofc_post_city_calendar_date_picker):
                        for year in self.year_numbers:
                            self.calendar.wait_for_element_to_visible(ofc_post_city_calendar_date_picker_year, 3)
                            if not self.is_element_present(ofc_post_city_calendar_date_picker_year + f"/option[@value='{year}' and @selected]"):
                                self.select_dropdown(ofc_post_city_calendar_date_picker_year, year, True)

                            months = [o.split("|")[1] for o in self.dates_filter_list if str(year) in o]
                            for num in months:
                                if self.is_element_present(ofc_post_city_calendar_date_picker_month):
                                    if not self.is_element_present(ofc_post_city_calendar_date_picker_month + f"/option[@value='{num}' and @selected]"):
                                        self.select_dropdown(ofc_post_city_calendar_date_picker_month, num, True)
                                        time.sleep(random.uniform(0.2, 0.4))

                                    result = self.calendar.handle_calendar(num, post_city, "first", year)
                                    if result["status"] != "CONTINUE": return result
                                    
                                    if str(int(num) + 1) in months:
                                        result = self.calendar.handle_calendar(str(int(num) + 1), post_city, "last", year)
                                        if result["status"] != "CONTINUE": return result
                        
                        # Calendar checked but no matching dates found.
                        self.notifier.notify_info(f"Checked {post_city} calendar. No matching dates found. Moving to next city...")
                    else:
                        if not self.is_element_present("//div[not(contains(@style,'none'))]/div[text()='No Slots Available']"):
                            log.error(f"Calendar hung on 'Loading...' for {post_city}. Refreshing...")
                            self.bm.driver.refresh()
                            time.sleep(5)
                            return {"status": "KICKED_OUT"}
                        else:
                            log.info(f"Date Picker Not Found For City: {post_city}. ('No Slots Available')")
                            # self.notifier.notify_info(f"Checked {post_city}. No Slots Available. Moving to next city...")
                else:
                    log.error("First City Dropdown not Found. The page is stuck. Refreshing...")
                    self.bm.driver.refresh()
                    time.sleep(5)
                    return {"status": "KICKED_OUT"}
            else:
                return {"status": "KICKED_OUT"}

            time.sleep(random.uniform(self.inner_start_time, self.inner_end_time))
            
        if len(self.ofc_posts) == 1:
            time.sleep(random.uniform(self.outer_start_time, self.outer_end_time))
        elif len(self.ofc_posts) == 2:
            time.sleep(random.uniform(6.1, 15.9))
        elif len(self.ofc_posts) == 3:
            time.sleep(random.uniform(7.1, 20.9))
        elif len(self.ofc_posts) == 4:
            time.sleep(random.uniform(8.1, 25.9))
        elif len(self.ofc_posts) == 5:
            time.sleep(random.uniform(9.1, 30.9))
            
        return {"status": "CYCLE_COMPLETE"}
