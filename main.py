from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
import sys
import json
import os
import datetime

STORAGE_FILE = "local_storage.json"


def load_local_storage(driver):
    """Load Local Storage data from file if it exists."""
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r") as f:
            storage_data = json.load(f)
            for key, value in storage_data.items():
                driver.execute_script(f"localStorage.setItem('{key}', '{value}');")
        print("Local Storage loaded successfully")
    else:
        print("No saved Local Storage found")


def save_local_storage(driver):
    """Save current Local Storage data to file."""
    storage_data = driver.execute_script(
        "return Object.fromEntries(Object.entries(localStorage));"
    )
    with open(STORAGE_FILE, "w") as f:
        json.dump(storage_data, f)
    print("Local Storage saved successfully")


def setup_driver(headless=True):
    """Initialize Firefox WebDriver with optional headless mode."""
    driver_options = Options()
    if headless:
        driver_options.add_argument("--headless")  # Run without UI
        driver_options.add_argument("--disable-gpu")
    driver = webdriver.Firefox(options=driver_options)
    driver.get("https://web.telegram.org/a/")  # To set what to load for
    load_local_storage(driver)
    driver.get("https://web.telegram.org/a/")  # needed...
    return driver


def get_user_status(driver, user_id):
    """Check if the specified Telegram user is online."""
    print(f"Opening https://web.telegram.org/a/#{user_id}")
    # Do not remove, it should be here to reset telegram scripts ahahahaha
    driver.get("https://google.com/")
    driver.get(f"https://web.telegram.org/a/#{user_id}")
    try:
        print("Waiting 10 seconds...")
        return (
            WebDriverWait(driver, 10)
            .until(EC.presence_of_element_located((By.CLASS_NAME, "user-status")))
            .text
        )
    except Exception as e:
        print(e)
        return "Error or user not found"


def is_logged_in(driver):
    """Check if logged in by looking for the chatlist element."""
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "ChatFolders"))
        )
        return True
    except:
        return False


def log(status, log_file="log.txt"):
    print(f"logging status {status}")
    with open(log_file, "a") as f:
        f.write(f"{datetime.datetime.now().strftime('[%Y-%m-%d %H:%M:%S]')} {status}\n")


def main():
    """Main execution logic."""
    if len(sys.argv) < 2:
        print("Please provide a Telegram user ID as a command-line argument")
        print("Usage: python main.py <user_id>")
        sys.exit(1)
    user_id = sys.argv[1]
    driver = setup_driver()  # Set False here for debug

    if not is_logged_in(driver):
        print("Not logged in. Please log in manually in the browser.")
        input("Press Enter after logging in...")
        setup_driver(headless=False)
        save_local_storage(driver)  # Save cookies after manual login
    log(get_user_status(driver, user_id), f"{user_id}.log")


if __name__ == "__main__":
    main()
