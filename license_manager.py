import subprocess
import hashlib
import requests
import sys
import platform
from logger import log

class LicenseManager:
    def __init__(self, database_url):
        self.database_url = database_url
        self.hwid = self._generate_hwid()

    def _get_windows_uuid(self):
        try:
            # Use WMIC to get the unique UUID of the motherboard/system
            cmd = "wmic csproduct get uuid"
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8')
            uuid = output.split('\n')[1].strip()
            if uuid and uuid.lower() != "ffffffff-ffff-ffff-ffff-ffffffffffff":
                return uuid
        except Exception as e:
            pass
        return "UNKNOWN_UUID"

    def _get_windows_cpu_id(self):
        try:
            # Use WMIC to get CPU ID
            cmd = "wmic cpu get ProcessorId"
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8')
            cpu_id = output.split('\n')[1].strip()
            if cpu_id:
                return cpu_id
        except Exception as e:
            pass
        return "UNKNOWN_CPUID"

    def _generate_hwid(self):
        """Generates a secure HWID based on system hardware components."""
        if platform.system() != "Windows":
            return "NON_WINDOWS_SYSTEM"

        uuid = self._get_windows_uuid()
        cpu_id = self._get_windows_cpu_id()

        # Combine hardware components and hash them for a clean HWID string
        raw_hwid = f"{uuid}-{cpu_id}"
        hashed_hwid = hashlib.sha256(raw_hwid.encode('utf-8')).hexdigest()
        
        # Format the hash to look like a standard license key (e.g. XXXX-XXXX-XXXX-XXXX)
        short_hwid = hashed_hwid[:16].upper()
        formatted_hwid = f"{short_hwid[:4]}-{short_hwid[4:8]}-{short_hwid[8:12]}-{short_hwid[12:16]}"
        return formatted_hwid

    def verify_license(self):
        """Checks if the HWID exists in the remote database."""
        print("=========================================")
        print(f"YOUR HARDWARE ID: {self.hwid}")
        print("=========================================\n")
        print("Verifying License with Server...")

        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = requests.get(self.database_url, timeout=10, verify=False)
            if response.status_code == 200:
                authorized_hwids = response.text.splitlines()
                # Clean up the list to ignore empty lines and comments
                authorized_hwids = [hwid.strip() for hwid in authorized_hwids if hwid.strip() and not hwid.startswith("#")]

                if self.hwid in authorized_hwids:
                    print("[SUCCESS] License Verified! Access Granted.\n")
                    return True
                else:
                    print("\n[ERROR] LICENSE INVALID OR EXPIRED!")
                    print("This computer is not authorized to run this software.")
                    print(f"Please send the Hardware ID above ({self.hwid}) to the developer to activate your license.")
                    input("\nPress Enter to exit...")
                    sys.exit(0)
            else:
                print(f"\n[ERROR] Could not reach the License Server (HTTP {response.status_code}).")
                print("Please check your internet connection and try again.")
                input("\nPress Enter to exit...")
                sys.exit(1)

        except requests.exceptions.RequestException as e:
            print(f"\n[ERROR] Could not connect to the License Server: {e}")
            print("Please check your internet connection or proxy settings.")
            input("\nPress Enter to exit...")
            sys.exit(1)

if __name__ == "__main__":
    # Test block
    # Replace this URL with a raw text link from Pastebin/Github
    test_db = "https://raw.githubusercontent.com/placeholder/license/main/hwids.txt" 
    lm = LicenseManager(test_db)
    print(f"Generated HWID: {lm.hwid}")
