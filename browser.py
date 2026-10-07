import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from logger import log
from config import load_config
import os

class BrowserManager:
    def __init__(self):
        self.config = load_config()
        self.driver = None
        
    def create_proxy_extension(self, proxy_str):
        import zipfile
        proxy_str = proxy_str.replace('http://', '').replace('https://', '')
        if '@' not in proxy_str:
            return None
        auth_part, ip_port = proxy_str.split('@')
        user, pwd = auth_part.split(':')
        host, port = ip_port.split(':')
        
        ext_dir = os.path.join(os.getcwd(), 'proxy_ext')
        os.makedirs(ext_dir, exist_ok=True)
        
        manifest_json = """
        {
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "Chrome Proxy",
            "permissions": [
                "proxy",
                "tabs",
                "unlimitedStorage",
                "storage",
                "<all_urls>",
                "webRequest",
                "webRequestBlocking"
            ],
            "background": {
                "scripts": ["background.js"]
            },
            "minimum_chrome_version":"22.0.0"
        }
        """
        
        background_js = f"""
        var config = {{
                mode: "fixed_servers",
                rules: {{
                  singleProxy: {{
                    scheme: "http",
                    host: "{host}",
                    port: parseInt({port})
                  }},
                  bypassList: ["localhost"]
                }}
              }};

        chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

        function callbackFn(details) {{
            return {{
                authCredentials: {{
                    username: "{user}",
                    password: "{pwd}"
                }}
            }};
        }}

        chrome.webRequest.onAuthRequired.addListener(
                    callbackFn,
                    {{urls: ["<all_urls>"]}},
                    ['blocking']
        );
        """
        
        with open(os.path.join(ext_dir, 'manifest.json'), 'w') as f:
            f.write(manifest_json)
        with open(os.path.join(ext_dir, 'background.js'), 'w') as f:
            f.write(background_js)
            
        return ext_dir

    def start(self):
        log.info("Starting BrowserManager...")
        options = uc.ChromeOptions()
        
        # Disable saving passwords and automation overlays
        prefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False}
        options.add_experimental_option("prefs", prefs)
        
        proxies = self.config.get('proxies', [])
        if proxies:
            proxy = random.choice(proxies)
            if '@' in proxy:
                ext_dir = self.create_proxy_extension(proxy)
                if ext_dir:
                    options.add_argument(f'--load-extension={ext_dir}')
                    log.info(f"Using authenticated proxy: {proxy}")
            else:
                options.add_argument(f'--proxy-server={proxy}')
                log.info(f"Using random unauthenticated proxy: {proxy}")
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                # Force a specific chrome version if defined in config to avoid driver mismatch errors
                version_main = self.config.get('chrome', {}).get('version_main')
                if version_main:
                    self.driver = uc.Chrome(options=options, version_main=int(version_main))
                else:
                    self.driver = uc.Chrome(options=options)
                
                # Advanced Turnstile Stealth CDP Injections
                try:
                    self.driver.execute_cdp_cmd(
                        "Page.addScriptToEvaluateOnNewDocument",
                        {
                            "source": """
                                Object.defineProperty(navigator, 'webdriver', {
                                    get: () => undefined
                                });
                                Object.defineProperty(navigator, 'plugins', {
                                    get: () => [1, 2, 3, 4, 5]
                                });
                                window.chrome = {
                                    runtime: {}
                                };
                            """
                        }
                    )
                except Exception as cdp_e:
                    log.warning(f"Could not inject CDP stealth script: {cdp_e}")

                log.info("Browser started successfully with enhanced Turnstile stealth.")
                return
            except Exception as e:
                log.warning(f"Failed to start browser (Attempt {attempt}/{max_retries}): {e}")
                if attempt == max_retries:
                    log.error("Max retries reached. Browser failed to start.")
                    raise e
                time.sleep(3)

    def stop(self):
        if self.driver:
            try:
                self.driver.quit()
                log.info("Browser stopped.")
            except Exception as e:
                log.error(f"Error stopping browser: {e}")
        self.driver = None

    def restart(self):
        log.info("Restarting browser...")
        self.stop()
        self.start()

    def get_url(self, url):
        if self.driver:
            self.driver.get(url)

    def current_url(self):
        return self.driver.current_url if self.driver else ""

    def take_screenshot(self, name_prefix="screenshot"):
        if not self.driver:
            return
        try:
            os.makedirs('screenshots', exist_ok=True)
            path = f"screenshots/{name_prefix}_{int(time.time())}.png"
            self.driver.save_screenshot(path)
            log.info(f"Screenshot saved: {path}")
            return path
        except Exception as e:
            log.error(f"Failed to take screenshot: {e}")
            
    def dump_diagnostics(self, attempt=1):
        if not self.driver:
            return
        try:
            log.info(f"--- DIAGNOSTIC DUMP (Attempt {attempt}) ---")
            log.info(f"URL: {self.driver.current_url}")
            log.info(f"Title: {self.driver.title}")
            
            # Save screenshot
            self.take_screenshot("diagnostic_dump")
            
            # Save HTML source
            os.makedirs('logs', exist_ok=True)
            html_path = f"logs/error_page_{int(time.time())}.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            log.info(f"HTML source saved to: {html_path}")
            log.info("-----------------------------------")
        except Exception as e:
            log.error(f"Failed to dump diagnostics: {e}")
            
    def switch_to_main_window(self, url_substring="usvisascheduling.com"):
        if not self.driver:
            return False
        try:
            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                if url_substring in self.driver.current_url:
                    return True
            return False
        except Exception as e:
            log.error(f"Error switching windows: {e}")
            return False
            
    def disable_alerts(self):
        if self.driver:
            try:
                self.driver.execute_script("window.alert = function() {};")
            except Exception as e:
                log.warning(f"Failed to disable alerts: {e}")
