import time
import random
import sys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from logger import log

class CalendarHandler:
    def __init__(self, browser_manager, config):
        self.bm = browser_manager
        self.config = config
        dates_raw = self.config.get('dates', [])
        self.dates_filter_list = [f"{d['year']}|{d['month']}|{d['range']}" for d in dates_raw]

    def isElementPresent(self, locator):
        try:
            element = self.bm.driver.find_element(By.XPATH, locator)
            if element.is_displayed():
                return True
            return False
        except Exception as e:
            # Removed log.error here as isElementPresent is often expected to fail
            return False

    def ClickElement(self, XPath):
        try:
            self.bm.driver.find_element(By.XPATH, XPath).click()
        except Exception as ex:
            log.info(f"XPath Not Found to Click: {XPath}")

    def ClickElementWithJS(self, XPath):
        try:
            element = self.bm.driver.find_element(By.XPATH, XPath)
            self.bm.driver.execute_script("arguments[0].click();", element)
        except Exception as ex:
            log.info(f"XPath Not Clicked with JS: {XPath}")

    def wait_for_any_element_to_be_visible(self, locator1, locator2, wait_time):
        try:
            wait = WebDriverWait(self.bm.driver, wait_time, poll_frequency=0.1)
            wait.until(lambda d: d.find_element(By.XPATH, locator1).is_displayed() or d.find_element(By.XPATH, locator2).is_displayed())
        except Exception as e:
            log.warning(f"Wait timeout for elements: {locator1} or {locator2}. Error: {e}")

    def wait_for_element_to_visible(self, locator, wait_time):
        try:
            wait = WebDriverWait(self.bm.driver, wait_time, poll_frequency=0.1)
            wait.until(EC.visibility_of_element_located((By.XPATH, locator)))
        except Exception as e:
            log.warning(f"Wait timeout for element: {locator}. Error: {e}")

    def getElements(self, locator, locaType=By.XPATH):
        try:
            return self.bm.driver.find_elements(locaType, locator)
        except Exception as e:
            log.warning(f"Failed to get elements for locator {locator}: {e}")
            return None

    def getElementText(self, locator, locaType=By.XPATH):
        try:
            gettext = self.bm.driver.find_element(locaType, locator)
            if gettext.text != "":
                return gettext.text
            return gettext.get_attribute("textContent") or ""
        except Exception as e:
            log.warning(f"Failed to get text for locator {locator}: {e}")
            return ""

    def getListofText(self, locator, locatorType=By.XPATH):
        elements = self.getElements(locator, locatorType)
        elemsList = []
        try:
            if elements:
                for element in elements:
                    if element is not None:
                        elemsList.append(element.text)
        except Exception as e:
            log.warning(f"Failed to get list of text for locator {locator}: {e}")
        return elemsList

    def handle_calendar(self, num, post_city, calendar, year):
        driver = self.bm.driver
        date_picker_green = f"//div[contains(@class,'ui-datepicker-group-{calendar}')]//tr/td[contains(@class,'greenday')]"
        if self.isElementPresent(date_picker_green):
            filter_date = [o.split("|")[2] for o in self.dates_filter_list if o.split("|")[0] == year and o.split("|")[1] == num]
            if not filter_date:
                return {"status": "CONTINUE"}
            filter_date = filter_date[0].split("-")
            filter_start_date = int(filter_date[0])
            filter_end_date = int(filter_date[1])
            all_dates = list(range(filter_start_date, filter_end_date + 1))

            for i in all_dates:
                date_picker_green_day = f"//div[contains(@class,'ui-datepicker-group-{calendar}')]//tr/td[contains(@class,'greenday')]/a[text()='{i}']"
                if self.isElementPresent(date_picker_green_day):
                    log.info(f"Slot Found For Month: {num}")
                    self.ClickElement(date_picker_green_day)
                    
                    slot_times_path = "//input[@name='schedule-entries']"
                    allocations_path = "//input[@name='schedule-entries']/parent::label/ancestor::td/following-sibling::td[2]"
                    allocations_error_path = "//div[contains(@class,'alert-danger')]"
                    
                    self.wait_for_any_element_to_be_visible(allocations_path, allocations_error_path, 60)
                    time.sleep(random.uniform(0.5, 1))
                    
                    if self.isElementPresent(slot_times_path):
                        slot_times = self.getElements(slot_times_path)
                        allocations = self.getListofText(allocations_path, By.XPATH)
                        log.info(f"All Available Allocations: {allocations}")
                        if allocations:
                            allocations = [int(x) for x in allocations if x]
                            allocations.sort(reverse=True)
                            allocations = [str(x) for x in allocations if x]
                        else:
                            allocations = []
                            
                        allocation_counts = {}
                        for allocation in allocations:
                            log.info(f"Current Allocation: {allocation}")
                            if allocation not in allocation_counts:
                                allocation_counts[allocation] = 1
                            else:
                                allocation_counts[allocation] += 1

                            count = allocation_counts[allocation]
                            allocation_xpath = f"({allocations_path}[.={allocation}])[{count}]"
                            
                            if self.isElementPresent(allocation_xpath + "/preceding-sibling::td[2]//input"):
                                self.ClickElementWithJS(allocation_xpath + "/preceding-sibling::td[2]//input")

                                submit_btn_not_disabled_path = '//input[@type="submit" and not (@disabled)]'
                                self.wait_for_element_to_visible(submit_btn_not_disabled_path, 5)

                                if self.isElementPresent(submit_btn_not_disabled_path):
                                    log.info("Submit Button Found")
                                    slot_date_path = allocation_xpath + "/preceding-sibling::td[2]"
                                    slot_time_path = allocation_xpath + "/preceding-sibling::td[1]"
                                    slot_date = self.getElementText(slot_date_path)
                                    slot_time = self.getElementText(slot_time_path)
                                    
                                    self.ClickElementWithJS(submit_btn_not_disabled_path)

                                    ofc_post_label = "//label[text()='OFC Post']"
                                    slot_no_longer_avail_path = "//div[.='The selected appointment time is no longer available, please select another appointment time.']"
                                    if len(slot_times) > 1:
                                        self.wait_for_element_to_visible(slot_no_longer_avail_path, 40)
                                    else:
                                        self.wait_for_element_to_visible(slot_no_longer_avail_path, 60)
                                        
                                    page_source = self.bm.driver.page_source.lower()
                                    too_many_requests_path = "//*[contains(text(), 'The system is processing too many requests')]"
                                    if self.isElementPresent(too_many_requests_path) or "error 1015" in page_source or "rate_limited" in page_source:
                                        log.info("Rate limit detected after submit (Error 1015 or Too Many Requests).")
                                        return {"status": "RATE_LIMITED"}

                                    if not self.isElementPresent(ofc_post_label):
                                        log.info(f"Slot City: {post_city}")
                                        log.info(f"Slot Date: {slot_date}")
                                        log.info(f"Slot Time: {slot_time}")
                                        log.info(f"Slot Allocation: {allocation}")
                                        log.info("Clicked on Submit Button Successfully, OFC Page Navigated to Next Page Successfully! Stopping bot.")
                                        return {"status": "SLOT_BOOKED", "city": post_city, "date": slot_date, "time": slot_time, "allocation": allocation}
                                    else:
                                        log.info("It seems like Submit Button is Clicked but OFC Page Doesn't Navigate to the Next Page So Program is Continue & Looking Forward for any other Slot Time or Green Day to Catch.")
        return {"status": "CONTINUE"}
