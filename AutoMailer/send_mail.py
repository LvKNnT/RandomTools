from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv
import re

# Before running this script, ensure you have:
# 1. Window + R - > "msedge.exe --remote-debugging-port=9222 --user-data-dir="C:\edge_debug_profile""
# 2. Open Gmail in that Edge window and log in to the delegated account.

# ================= CONFIGURATION =================
SUBJECT = "[SAB] Xác nhận đăng kí CTV Bước chân yêu thương 2026"
HTML_TEMPLATE_PATH = "Mail xác nhận đăng ký CTV.html"
CSV_DATA_PATH = "Nhân sự BCYT - Sheet1.csv"
# =================================================

def read_html_template(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: Could not find HTML file at {file_path}")
        return None

def create_drafts_via_edge():
    base_html = read_html_template(HTML_TEMPLATE_PATH)
    if not base_html: return

    print("Connecting to your active Edge browser...")

    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

    try:
        driver = webdriver.Edge(options=options)
        # We need a small timeout allowance for the clipboard JS to execute
        driver.set_script_timeout(5)
        print("Connected successfully! Ensure the delegated Gmail is the active tab.")
    except Exception as e:
        print("Failed to connect. Did you launch Edge with the debugging command?")
        return

    # check if has all necessary columns for the template
    html_placeholders = set(re.findall(r'\{\{(.*?)\}\}', base_html))
    required_columns = html_placeholders.union({'Email'})

    try:
        with open(CSV_DATA_PATH, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            try:
                csv_headers = set(next(reader)) # Get the first row
            except StopIteration:
                print(f"❌ Error: '{CSV_DATA_PATH}' is empty.")
                return
    except FileNotFoundError:
        print(f"❌ Error: Could not find '{CSV_DATA_PATH}'")
        return

    # 3. Compare the two sets of data
    missing_columns = required_columns - csv_headers
    extra_columns = csv_headers - required_columns

    print("\n--- Validation Report ---")
    print(f"HTML Placeholders found: {html_placeholders}")
    print(f"CSV Headers found:       {csv_headers}")
    print("-------------------------")

    if missing_columns:
        print(f"❌ FAILED: Your CSV is missing these required columns: {missing_columns}")
        return
    else:
        print("✅ PASSED: Your CSV has all the necessary columns to send the emails!")

    if extra_columns:
        print(f"⚠️  Note: Your CSV has extra columns that will be ignored: {extra_columns}")


    print("\nStarting to create drafts in Gmail...")
    try:
        with open(CSV_DATA_PATH, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)

            for row_num, row in enumerate(reader, start=1):
                receiver_email = row.get('Email')
                if not receiver_email: continue

                print(f"[{row_num}] Creating draft for: {receiver_email}...")

                customized_html = base_html
                for key, value in row.items():
                    if key != 'Email' and key is not None:
                        customized_html = customized_html.replace(f"{{{{{key}}}}}", str(value))

                try:
                    # Step A: Find the Compose button and click
                    compose_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, ".T-I.T-I-KE.L3"))
                    )
                    compose_button.click()
                    time.sleep(2)

                    # Step B: Enter email
                    active_element = driver.switch_to.active_element
                    active_element.send_keys(receiver_email)
                    active_element.send_keys(Keys.ENTER)
                    time.sleep(0.5)

                    # Step C: Enter Subject
                    active_element.send_keys(Keys.TAB)
                    subject_field = driver.switch_to.active_element
                    subject_field.send_keys(SUBJECT)
                    time.sleep(0.5)

                    # Step D: Move to Message Body and use Clipboard to Paste
                    subject_field.send_keys(Keys.TAB)
                    time.sleep(0.5)
                    editor = driver.switch_to.active_element

                    # JavaScript to silently copy the rich HTML to your clipboard
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
                    # Execute the copy command
                    res = driver.execute_async_script(js_copy_to_clipboard, customized_html)

                    if res == "OK":
                        # Simulate Ctrl + V to paste the rich text
                        editor.send_keys(Keys.CONTROL, 'v')
                    else:
                        print(f"[{row_num}] Clipboard blocked. Error: {res}")

                    time.sleep(1.5)

                    # Step E: Press ESCAPE to save to Drafts
                    driver.switch_to.active_element.send_keys(Keys.ESCAPE)

                    print(f"[{row_num}] Draft saved successfully!")
                    time.sleep(2)

                except Exception as e:
                    print(f"Error automating draft {row_num}: {e}")
                    break

    except FileNotFoundError:
        print(f"Error: Could not find CSV file at {CSV_DATA_PATH}")

if __name__ == "__main__":
    create_drafts_via_edge()