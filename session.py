import os
import pickle
from logger import log

class SessionManager:
    def __init__(self, browser_manager):
        self.bm = browser_manager
        self.cookies_path = "cookies/cookies.pkl"
        os.makedirs("cookies", exist_ok=True)

    def save_cookies(self):
        if not self.bm.driver:
            return
        try:
            cookies = self.bm.driver.get_cookies()
            with open(self.cookies_path, "wb") as f:
                pickle.dump(cookies, f)
            log.info("Cookies saved successfully.")
        except Exception as e:
            log.error(f"Failed to save cookies: {e}")

    def load_cookies(self):
        if not self.bm.driver:
            return False
        if not os.path.exists(self.cookies_path):
            log.info("No saved cookies found.")
            return False
        try:
            with open(self.cookies_path, "rb") as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                self.bm.driver.add_cookie(cookie)
            log.info("Cookies loaded successfully.")
            return True
        except Exception as e:
            log.error(f"Failed to load cookies: {e}")
            return False

    def clear_session(self):
        if self.bm.driver:
            try:
                self.bm.driver.delete_all_cookies()
                self.bm.driver.execute_script("window.localStorage.clear();")
                self.bm.driver.execute_script("window.sessionStorage.clear();")
                log.info("Browser session cleared.")
            except Exception as e:
                log.error(f"Error clearing session: {e}")
