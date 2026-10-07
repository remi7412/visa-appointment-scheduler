import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from logger import log

class CloudflareSolver:
    def __init__(self, browser_manager):
        self.bm = browser_manager
        
    def is_cloudflare_challenge(self):
        """Detects if the current page is a Cloudflare challenge page."""
        if not self.bm.driver:
            return False
            
        try:
            page_source = self.bm.driver.page_source.lower()
            
            # Combine multiple signals (Text + Structure + Attributes)
            signals_matched = 0
            
            # 1. Text markers
            if any(phrase in page_source for phrase in ["verify you are human", "security verification", "protect against malicious bots"]):
                signals_matched += 1
                
            # 2. Structural/DOM markers
            if self.bm.driver.find_elements(By.XPATH, "//div[contains(@class, 'cf-turnstile')]") or self.bm.driver.find_elements(By.XPATH, "//div[@id='turnstile-wrapper']"):
                signals_matched += 1
                
            # 3. Iframe markers
            if self.bm.driver.find_elements(By.XPATH, "//iframe[contains(@title, 'Cloudflare') or contains(@src, 'cloudflare')]"):
                signals_matched += 1
                
            # If any structural element is found, it's definitely CF
            if signals_matched >= 1:
                return True
                
        except Exception:
            pass
            
        return False
        
    def solve(self):
        """Attempts to bypass the Cloudflare challenge dynamically."""
        if not self.is_cloudflare_challenge():
            return False
            
        log.info("Cloudflare challenge detected! Attempting to solve dynamically...")
        driver = self.bm.driver
        
        try:
            # Helper to wait dynamically for CF to disappear
            def wait_for_clearance(timeout=15):
                try:
                    WebDriverWait(driver, timeout).until_not(lambda d: self.is_cloudflare_challenge())
                    log.info("Cloudflare challenge cleared dynamically!")
                    return True
                except Exception:
                    return False

            # 1. Passive waiting (undetected_chromedriver often bypasses it automatically if we just wait)
            log.info("Passively waiting for auto-clearance...")
            if wait_for_clearance(timeout=8):
                return True
                
            # 2. Try clicking the Turnstile wrapper directly (Shadow DOM / modern Turnstile)
            try:
                turnstile_wrappers = driver.find_elements(By.XPATH, "//div[contains(@class, 'cf-turnstile')] | //div[@id='turnstile-wrapper'] | //label[contains(text(), 'Verify you are human')]")
                for wrapper in turnstile_wrappers:
                    if wrapper.is_displayed():
                        log.info("Found Cloudflare wrapper element. Clicking directly...")
                        try:
                            ActionChains(driver).move_to_element(wrapper).pause(random.uniform(0.5, 1.5)).click().perform()
                        except Exception:
                            log.warning("ActionChains click intercepted, trying JavaScript click...")
                            driver.execute_script("arguments[0].click();", wrapper)
                        
                        if wait_for_clearance(timeout=10):
                            return True
                        break
            except Exception as e:
                log.warning(f"Failed to click Turnstile wrapper directly: {e}")
                
            # 3. Active solving (aggressively check all iframes)
            iframes = driver.find_elements(By.XPATH, "//iframe")
            for iframe in iframes:
                try:
                    driver.switch_to.frame(iframe)
                    time.sleep(1)
                    
                    # Look for checkbox, label, or body inside the iframe
                    wrappers = driver.find_elements(By.XPATH, "//*[@type='checkbox'] | //label[contains(text(), 'Verify you are human')] | //*[contains(text(), 'Verify')] | //div[contains(@class, 'cb-c')]")
                    
                    clicked = False
                    if wrappers:
                        for w in wrappers:
                            if w.is_displayed():
                                log.info("Found Cloudflare element inside iframe! Clicking...")
                                try:
                                    ActionChains(driver).move_to_element(w).pause(random.uniform(0.5, 1.5)).click().perform()
                                except Exception:
                                    driver.execute_script("arguments[0].click();", w)
                                clicked = True
                                break
                    else:
                        # Fallback to clicking center of iframe body just in case
                        body = driver.find_element(By.TAG_NAME, "body")
                        if body.is_displayed():
                            log.info("Clicking center of unknown iframe as fallback...")
                            try:
                                ActionChains(driver).move_to_element(body).pause(random.uniform(0.5, 1.5)).click().perform()
                                clicked = True
                            except Exception:
                                pass

                    driver.switch_to.default_content()
                    
                    if clicked:
                        if wait_for_clearance(timeout=10):
                            return True
                except Exception as inner_e:
                    log.warning(f"Error interacting with iframe: {inner_e}")
                    try:
                        driver.switch_to.default_content()
                    except:
                        pass
                    
            # 4. Keyboard Brute-Force (Tab + Space)
            log.info("Attempting keyboard brute-force for Cloudflare...")
            try:
                # Tab 3-6 times and press space
                actions = ActionChains(driver)
                for _ in range(5):
                    actions.send_keys(Keys.TAB).pause(0.5)
                actions.send_keys(Keys.SPACE).perform()
                
                if wait_for_clearance(timeout=10):
                    log.info("Cloudflare bypass successful via keyboard!")
                    return True
            except Exception:
                pass
                
            log.warning("Cloudflare bypass failed dynamically. Relying on state machine loop.")
            return False
                
        except Exception as e:
            log.error(f"Fatal error during Cloudflare bypass attempt: {e}")
            try:
                driver.switch_to.default_content()
            except:
                pass
            return False

class LoginSolver:
    def __init__(self, browser_manager, config):
        self.bm = browser_manager
        self.config = config
        
    def is_login_page(self):
        """Detects if we are on the B2C login page."""
        if not self.bm.driver:
            return False
        return "b2clogin.com" in self.bm.driver.current_url.lower()
        
    def is_security_questions_page(self):
        """Detects if we are on the security questions page."""
        if not self.bm.driver:
            return False
        page_source = self.bm.driver.page_source.lower()
        return "security question" in page_source or "answer your security questions" in page_source
        
    def solve_login(self):
        """Types the username and password."""
        driver = self.bm.driver
        creds = self.config.get("credentials", {})
        username = creds.get("username", "")
        password = creds.get("password", "")
        
        if not username or not password:
            log.warning("No credentials found in config.json. Cannot auto-login.")
            return False
            
        log.info("Auto-login: Entering credentials...")
        try:
            # Wait for email field
            email_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "signInName"))
            )
            email_field.clear()
            for char in username:
                email_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
                
            password_field = driver.find_element(By.ID, "password")
            password_field.clear()
            for char in password:
                password_field.send_keys(char)
                time.sleep(random.uniform(0.05, 0.15))
                
            try:
                sign_in_btn = driver.find_element(By.ID, "next")
                driver.execute_script("arguments[0].click();", sign_in_btn)
                log.info("Auto-login: Clicked Sign In via JavaScript.")
            except Exception:
                log.info("Auto-login: Pressing Enter to submit...")
                password_field.send_keys(Keys.RETURN)
                
            time.sleep(8)
            return True
        except Exception as e:
            log.error(f"Auto-login failed: {e}")
            return False
            
    def solve_security_questions(self):
        """Answers the security questions."""
        driver = self.bm.driver
        answers = self.config.get("credentials", {}).get("security_answers", {})
        
        log.info("Auto-login: Security questions detected. Attempting to answer...")
        try:
            filled_inputs = []
            
            queries = []
            for key, val in answers.items():
                if val:
                    queries.append((key, val))
            
            for keyword, answer in queries:
                if not answer:
                    continue
                try:
                    # Find element whose direct text contains the keyword (case-insensitive)
                    # and grab ALL inputs that come after it.
                    xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]/following::input[not(@type='hidden') and not(@type='submit') and not(@type='button')]"
                    inps = driver.find_elements(By.XPATH, xpath)
                    
                    for inp in inps:
                        if inp in filled_inputs:
                            continue
                            
                        # Only try to type into inputs that are actually visible on screen!
                        if inp.is_displayed() and inp.is_enabled():
                            try:
                                inp.clear()
                            except:
                                pass
                            for char in answer:
                                inp.send_keys(char)
                                time.sleep(random.uniform(0.05, 0.15))
                                
                            filled_inputs.append(inp)
                            log.info(f"Filled answer for keyword '{keyword}'.")
                            break # Move on to the next question!
                except Exception as inner:
                    log.warning(f"Could not fill answer for '{keyword}': {inner}")
                    
            # Click next/submit/continue
            try:
                next_btn = driver.find_element(By.XPATH, "//button[@id='continue' or @id='next' or contains(text(), 'Continue')]")
                driver.execute_script("arguments[0].click();", next_btn)
                log.info("Auto-login: Clicked Continue via JS.")
            except Exception:
                log.info("Auto-login: Pressing Enter to submit security questions...")
                if filled_inputs:
                    filled_inputs[-1].send_keys(Keys.RETURN)
                    
            time.sleep(8)
            return True
        except Exception as e:
            log.error(f"Security questions solver failed: {e}")
            return False
