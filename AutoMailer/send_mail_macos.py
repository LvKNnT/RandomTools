"""Create personalized Gmail drafts on macOS through Google Chrome.

Start Chrome with remote debugging enabled, open Gmail in that browser window,
then run this script from the directory containing the configured input files.
"""

import csv
import re
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# ================= CONFIGURATION =================
SUBJECT = "[SAB] Xác nhận đăng kí CTV Bước chân yêu thương 2026"
HTML_TEMPLATE_PATH = "Mail xác nhận đăng ký CTV.html"
CSV_DATA_PATH = "Nhân sự BCYT - Sheet1.csv"
# =================================================


def read_html_template(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: Could not find HTML file at {file_path}")
        return None


def create_drafts_via_chrome():
    base_html = read_html_template(HTML_TEMPLATE_PATH)
    if not base_html:
        return

    print("Connecting to your active Chrome browser...")

    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

    try:
        driver = webdriver.Chrome(options=options)
        driver.set_script_timeout(5)
        print("Connected successfully! Ensure the correct Gmail tab is active.")
    except Exception as error:
        print("Failed to connect to Chrome.")
        print("Start Chrome with remote debugging on port 9222, then try again.")
        print(f"Details: {error}")
        return

    html_placeholders = set(re.findall(r"\{\{(.*?)\}\}", base_html))
    required_columns = html_placeholders.union({"Email"})

    try:
        with open(CSV_DATA_PATH, "r", encoding="utf-8-sig") as file:
            reader = csv.reader(file)
            try:
                csv_headers = set(next(reader))
            except StopIteration:
                print(f"❌ Error: '{CSV_DATA_PATH}' is empty.")
                return
    except FileNotFoundError:
        print(f"❌ Error: Could not find '{CSV_DATA_PATH}'")
        return

    missing_columns = required_columns - csv_headers
    extra_columns = csv_headers - required_columns

    print("\n--- Validation Report ---")
    print(f"HTML Placeholders found: {html_placeholders}")
    print(f"CSV Headers found:       {csv_headers}")
    print("-------------------------")

    if missing_columns:
        print(f"❌ FAILED: Your CSV is missing these required columns: {missing_columns}")
        return

    print("✅ PASSED: Your CSV has all the necessary columns to create the drafts!")

    if extra_columns:
        print(f"⚠️  Note: Your CSV has extra columns that will be ignored: {extra_columns}")

    print("\nStarting to create drafts in Gmail...")
    try:
        with open(CSV_DATA_PATH, mode="r", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            for row_num, row in enumerate(reader, start=1):
                receiver_email = row.get("Email")
                if not receiver_email:
                    continue

                print(f"[{row_num}] Creating draft for: {receiver_email}...")

                customized_html = base_html
                for key, value in row.items():
                    if key != "Email" and key is not None:
                        customized_html = customized_html.replace(
                            f"{{{{{key}}}}}", str(value)
                        )

                try:
                    compose_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, ".T-I.T-I-KE.L3"))
                    )
                    compose_button.click()
                    time.sleep(2)

                    active_element = driver.switch_to.active_element
                    active_element.send_keys(receiver_email)
                    active_element.send_keys(Keys.ENTER)
                    time.sleep(0.5)

                    active_element.send_keys(Keys.TAB)
                    subject_field = driver.switch_to.active_element
                    subject_field.send_keys(SUBJECT)
                    time.sleep(0.5)

                    subject_field.send_keys(Keys.TAB)
                    time.sleep(0.5)
                    editor = driver.switch_to.active_element

                    js_copy_to_clipboard = """
                    var html = arguments[0];
                    var done = arguments[1];
                    try {
                        var blob = new Blob([html], {type: 'text/html'});
                        var item = new ClipboardItem({'text/html': blob});
                        navigator.clipboard.write([item]).then(function() {
                            done("OK");
                        }).catch(function(err) {
                            done("ERR: " + err.message);
                        });
                    } catch(e) {
                        done("ERR: " + e.message);
                    }
                    """
                    result = driver.execute_async_script(
                        js_copy_to_clipboard, customized_html
                    )

                    if result == "OK":
                        # macOS uses Command+V rather than Control+V.
                        editor.send_keys(Keys.COMMAND, "v")
                    else:
                        print(f"[{row_num}] Clipboard blocked. Error: {result}")

                    time.sleep(1.5)
                    driver.switch_to.active_element.send_keys(Keys.ESCAPE)

                    print(f"[{row_num}] Draft saved successfully!")
                    time.sleep(2)

                except Exception as error:
                    print(f"Error automating draft {row_num}: {error}")
                    break

    except FileNotFoundError:
        print(f"Error: Could not find CSV file at {CSV_DATA_PATH}")


if __name__ == "__main__":
    create_drafts_via_chrome()
