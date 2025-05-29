from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
import sys
import json
import os
import datetime
import time
from google import genai
from dotenv import load_dotenv

load_dotenv()
STORAGE_FILE = "local_storage.json"
LOGS_DIR = "logs"
MODEL = "gemini-2.0-flash"  # gemini-2.5-pro-preview-05-06
# Dictionary to store the last known online status for each user ID
# user_id: True (online) / False (offline)
last_known_status = {}

api_key = os.environ["GEMINI_API_KEY"]
if not api_key:
    print("Please provide the GEMINI_API_KEY environment variable")
    sys.exit(1)

prompt_template = """Below is a list of pairs ('channel_name', 'new_messages'). Your task is to write a summary of the chat history.
The TLDR should be at the top and contain only fun messages, invitations for events, news of historical importance, and mentions of my name (Luka).
Note, that I am not that much interested in TLDR from groups starting with '9-4', '10-4', or '11-4'.
After TLDR should come a statistic with every channel/group mentioned and what did it write about
--- Channels Content: ---


"""


def query_gemini(texts):
    context = genai.Client(api_key=api_key)
    prompt = f"{prompt_template}\n\n--- Channels Content: ---\n{'\n\n\n'.join(texts)}"
    print(f"Querying Gemini with {len(prompt)} characters")
    return context.models.generate_content(model=MODEL, contents=prompt).text


def safe_find(target, *args):
    try:
        return target.find_element(*args)
    except:
        return None


def parse_message(message_element):
    message_description = ""
    if message_time := safe_find(message_element, By.CLASS_NAME, "message-time"):
        message_description += f"[{message_time.text}] "
    if sender_name_element := safe_find(message_element, By.CLASS_NAME, "sender-title"):
        message_description += f"<{sender_name_element.text}> "
    if safe_find(message_element, By.CSS_SELECTOR, "video.full-media"):
        message_description += "<video> "
    elif safe_find(message_element, By.CSS_SELECTOR, "img.full-media"):
        message_description += "<image> "
    if safe_find(message_element, By.CSS_SELECTOR, "img.sticker-media"):
        message_description += "<sticker> "
    if text_content_element := safe_find(message_element, By.CLASS_NAME, "text-content"):
        message_description += text_content_element.text
    return message_description.strip()


def summary(driver):
    print("Writing summary...")
    if archive_element := safe_find(driver, By.CLASS_NAME, "chat-item-archive"):
        archive_element.click()
    else:
        raise Exception("Archive element not found. Terminating")
    texts = []
    for chat in driver.find_elements(By.CLASS_NAME, "chat-item-clickable"):
        if not safe_find(chat, By.CLASS_NAME, "unread"):
            continue

        chat.click()
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "Message")))

        new_messages = "\n".join(map(parse_message, driver.find_elements(By.CLASS_NAME, "Message")))

        chat_name = "Unknown Chat"
        if chat_name_element := safe_find(chat, By.CLASS_NAME, "fullName"):
            chat_name = chat_name_element.text
        elif chat_name_element := safe_find(chat, By.CSS_SELECTOR, ".ChatInfo .title"):
            chat_name = chat_name_element.text
        print("Added summary for", chat_name)
        if chat_name and new_messages:
            texts.append(f"('{chat_name}', '{new_messages}')")
    return texts


def log_online(driver):
    while True:
        for chat in driver.find_elements(By.CLASS_NAME, "chat-item-clickable"):
            is_online = bool(safe_find(chat, By.CLASS_NAME, "avatar-online-shown"))

            user_id_element = safe_find(chat, By.XPATH, ".//a[contains(@href, '#')]")
            user_id = user_id_element.get_attribute("href").split("#")[-1] if user_id_element else "unknown_user"
            if user_id == "unknown_user" or int(user_id) < 0:
                continue  # That is a channel or a group.
            if user_id not in last_known_status:
                last_known_status[user_id] = not is_online

            if is_online and not last_known_status[user_id]:
                log(user_id, "online")
                last_known_status[user_id] = True
            elif not is_online and last_known_status[user_id]:
                log(user_id, "offline")
                last_known_status[user_id] = False
            else:
                pass  # print(f"User {user_id}: Status unchanged.")
        time.sleep(2)


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
    storage_data = driver.execute_script("return Object.fromEntries(Object.entries(localStorage));")
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


def is_logged_in(driver):
    """Check if logged in by looking for the chatlist element."""
    try:
        print("wait! 15 seconds for the page to load")
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "ChatFolders")))
        return True
    except:
        return False


def log(user_id, message):
    """Log status changes to a user-specific file."""
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
    log_file_path = os.path.join(LOGS_DIR, f"{user_id}.log")
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    log_entry = f"{timestamp} {message}\n"
    print(f"Logging to {log_file_path}: {log_entry}")
    with open(log_file_path, "a") as f:
        f.write(log_entry)


def login():
    print("Not logged in. Please log in manually in the browser that will open now")
    driver = setup_driver(headless=False)
    input("Press Enter after logging in...")
    print("Re-checking login status...")
    if not is_logged_in(driver):
        print("Login failed. Exiting.")
        driver.quit()
        sys.exit(1)
    else:
        print("Successfully logged in.")
        save_local_storage(driver)
    return driver


def main():
    """Main execution logic."""
    print("Setting up the driver...")
    driver = setup_driver()
    print("Driver ready!")
    if not os.path.exists(STORAGE_FILE) or not is_logged_in(driver):
        driver = login()
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        print(query_gemini(summary(driver)))
    else:
        log_online(driver)
    driver.quit()


if __name__ == "__main__":
    main()
