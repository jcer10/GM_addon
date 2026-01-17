import yaml
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import re

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager


# ===== Terminal colors =====
RESET      = "\033[0m"

RED        = "\033[91m"
GREEN      = "\033[92m"
YELLOW     = "\033[93m"
BLUE       = "\033[94m"
PURPLE     = "\033[95m"
LIGHT_BLUE = "\033[96m"   # cyan / light blue


def load_ignored_zip_codes(config_file):
    with open(config_file, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    return set(config.get("ignored_zip_codes", []))


def parse_vehicle_file(filename, ignored_zip_codes):
    vehicles = []

    with open(filename, "r", encoding="utf-8") as file:
        lines = [line.strip() for line in file.readlines()]

    i = 0
    while i < len(lines):
        if lines[i] == "Vehicle":
            plate = lines[i + 1]
            address_line_1 = lines[i + 2]
            address_line_2 = lines[i + 3]
            percentage = lines[i + 5]

            zip_code = address_line_2[:4]

            if zip_code not in ignored_zip_codes:
                vehicles.append({
                    "plate": plate,
                    "address": f"{address_line_1}, {address_line_2}",
                    "battery": percentage,
                })

            i += 6
        else:
            i += 1

    return vehicles


def extract_first_connection_info(driver):
    wait = WebDriverWait(driver, 15)

    try:
        # Wait for at least one result to appear
        first_result = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.hfs_itemResultsConnectionOverviewLine")
            )
        )

        info_text_elem = first_result.find_element(
            By.CSS_SELECTOR, "span.infoText"
        )

        raw_text = info_text_elem.text.strip()
        # Example: "Rejsetid 1 t 5 min, 3 skift"

        # Extract travel time
        time_match = re.search(r"(\d+\s*t\s*\d+\s*min|\d+\s*min)", raw_text)

        # Extract number of changes
        changes_match = re.search(r"(\d+)\s*skift", raw_text)

        travel_time = time_match.group(1) if time_match else "N/A"
        changes = changes_match.group(1) if changes_match else "N/A"

        return travel_time, changes

    except TimeoutException:
        return None, None


def clean_pop_ups(driver):
    wait = WebDriverWait(driver, 10)

    # Small initial pause to allow popups to render
    time.sleep(5)

    # 1) Cookie consent popup
    try:
        cookie_button = wait.until(
            EC.element_to_be_clickable(
                (By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
            )
        )
        cookie_button.click()
        print("✔ Cookie popup accepted")
    except TimeoutException:
        print("ℹ Cookie popup not found")

    # 2) Welcome / location popup
    try:
        welcome_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(@onclick, 'closeWelcomeScreen')]"
                )
            )
        )
        welcome_button.click()
        print("✔ Welcome popup closed")
    except TimeoutException:
        print("ℹ Welcome popup not found")

def open_rejseplanen(driver):
    driver.get("https://www.rejseplanen.dk")
    clean_pop_ups(driver)

def search_route(driver, from_address, to_address, TIME_REST):
    wait = WebDriverWait(driver, 10)

    from_input = wait.until(
        EC.element_to_be_clickable((By.ID, "From"))
    )
    to_input = wait.until(
        EC.element_to_be_clickable((By.ID, "To"))
    )

    # Only set FROM if it's empty (first run)
    if not from_input.get_attribute("value"):
        from_input.send_keys(from_address)
        time.sleep(TIME_REST)
        from_input.send_keys(Keys.ENTER)
        time.sleep(TIME_REST)

    # Clear and set TO
    to_input.clear()
    time.sleep(TIME_REST)

    to_input.send_keys(to_address)
    time.sleep(TIME_REST)
    to_input.send_keys(Keys.ENTER)
    time.sleep(TIME_REST + 0.5)

    # # Click Find
    # find_button = wait.until(
    #     EC.element_to_be_clickable((By.ID, "HFS_SearchButton"))
    # )
    # time.sleep(TIME_REST)
    # find_button.click()

    # --- Wait for first result ---
    wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.hfs_itemResultsConnectionOverviewLine")
        )
    )

    # --- Click "Detaljer" for first connection ---
    details_button = wait.until(
        EC.element_to_be_clickable(
            (By.ID, "HFS_ConnectionBtn_cl_pt_0")
        )
    )
    time.sleep(TIME_REST)
    details_button.click()

    # --- Wait until expanded details are visible ---
    wait.until(
        EC.presence_of_element_located(
            (By.ID, "HFS_cl_pt_0")
        )
    )

    # --- Extract overview info ---
    travel_time, changes = extract_first_connection_info(driver)

    return travel_time, changes



def extract_journey_steps(driver, details_id="HFS_cl_pt_0"):
    wait = WebDriverWait(driver, 5)

    container = wait.until(
        EC.presence_of_element_located((By.ID, details_id))
    )

    steps = []

    # --- Start time ---
    start_time = container.find_element(
        By.CSS_SELECTOR,
        ".hfs_resultDepartureRow .hfs_resultTime"
    ).text.strip()

    # --- End time ---
    end_time = container.find_elements(
        By.CSS_SELECTOR,
        ".hfs_resultArrivalRow .hfs_resultTime"
    )[-1].text.strip()

    # --- Each journey leg ---
    legs = container.find_elements(
        By.CSS_SELECTOR,
        "li.hfs_itemResult"
    )

    for leg in legs:
        # Detect transport mode
        mode = None
        icon_classes = leg.get_attribute("innerHTML")

        if "haf_prod_bus" in icon_classes:
            mode = "bus"
        elif "haf_prod_sbahn" in icon_classes:
            mode = "s-train"
        elif "haf_prod_ubahn" in icon_classes:
            mode = "metro"
        elif "haf_prod_walk" in icon_classes:
            mode = "walk"
        else:
            continue

        # Line / label (optional)
        try:
            label = leg.find_element(
                By.CSS_SELECTOR,
                ".hfs_productLabel"
            ).text.strip()
        except:
            label = None

        # Duration
        duration_text = leg.text
        duration_match = re.search(r"(\d+)\s*min", duration_text)
        duration = duration_match.group(1) if duration_match else None

        if duration:
            steps.append({
                "mode": mode,
                "label": label,
                "minutes": duration
            })

    return start_time, steps, end_time

RED = "\033[91m"
RESET = "\033[0m"

def color_delay(time_str):
    """
    Colors +1 / -1 (including the symbol) in red.
    """
    match = re.search(r"([+-]\d+)$", time_str)
    if match:
        delay = match.group(1)
        base_time = time_str.replace(delay, "").strip()
        return f"{base_time} {RED}{delay}{RESET}"
    return time_str

import re

def color_bus_label(label):
    match = re.match(r"(\d+)([A-Z]?)", label)
    if not match:
        return label

    number, letter = match.groups()
    result = f"{YELLOW}{number}{RESET}"

    BUS_LETTERS = {
        "A": RED,
        "S": BLUE,
        "C": LIGHT_BLUE,
        "E": GREEN,
    }

    if letter:
        color = BUS_LETTERS.get(letter, RESET)
        result += f"{color}{letter}{RESET}"

    return result


def color_train_label(label):
    TRAIN_COLORS = {
        "A": LIGHT_BLUE,
        "B": GREEN,
        "C": YELLOW,   # closest to orange
        "E": PURPLE,
        "F": YELLOW,
        "H": RED,
    }

    color = TRAIN_COLORS.get(label, RESET)
    return f"{color}{label}{RESET}"


def color_metro_label(label):
    METRO_COLORS = {
        "M1": GREEN,
        "M2": YELLOW,
        "M3": RED,
        "M4": LIGHT_BLUE,
    }

    color = METRO_COLORS.get(label, RESET)
    return f"{color}{label}{RESET}"



def print_journey(start_time, steps, end_time):
    ICONS = {
        "bus": "🚌",
        "s-train": "🚆",
        "metro": "🚇",
        "walk": "🚶",
    }

    LEFT_WIDTH = 28
    RIGHT_WIDTH = 6

    print(f"{'start time:':<{LEFT_WIDTH}} {start_time}")

    for s in steps:
        icon = ICONS.get(s["mode"], "➡️")
        label = s.get("label")

        colored_label = ""
        if label:
            if s["mode"] == "bus":
                colored_label = color_bus_label(label)
            elif s["mode"] == "s-train":
                colored_label = color_train_label(label)
            elif s["mode"] == "metro":
                colored_label = color_metro_label(label)

        left = f"{icon} {s['mode']}"
        if colored_label:
            left += f" ({colored_label})"

        right = f"{s['minutes']} min"

        print(f"{left:<{LEFT_WIDTH}} {right:>{RIGHT_WIDTH}}")

    print(f"{'end time:':<{LEFT_WIDTH}} {end_time}")



def print_vehicle_with_battery(v):
    # Extract numeric battery percentage
    battery_pct = int(v["battery"].replace("%", "").strip())

    if battery_pct < 20:
        color = PURPLE     # was green → now purple
    elif battery_pct < 40:
        color = LIGHT_BLUE       # was yellow → now blue
    elif battery_pct < 60:
        color = GREEN      # was red → now green
    else:
        color = RESET



    print(f"{color}{v['plate']} → {v['address']}{RESET}")
    print(f"{color}Battery: {battery_pct}%{RESET}")

def load_start_address(filename="start_address.txt"):
    with open(filename, "r", encoding="utf-8") as f:
        return f.read().strip()


def main():
    vehicle_file = "vehicles.txt"
    config_file = "zip_code_ignore.yml"

    START_ADDRESS = load_start_address()
    DELAY_BETWEEN_SEARCHES = 1.5
    TIME_REST = 1

    ignored_zip_codes = load_ignored_zip_codes(config_file)
    vehicles = parse_vehicle_file(vehicle_file, ignored_zip_codes)

    print(f"Processing {len(vehicles)} vehicles via Rejseplanen...\n")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # modern headless
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")


    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # ✅ Open once
    open_rejseplanen(driver)

    for v in vehicles:
        print("-"*50)
        print_vehicle_with_battery(v)

        travel_time, changes = search_route(
            driver,
            START_ADDRESS,
            v["address"],
            TIME_REST,
        )

        start, steps, end = extract_journey_steps(driver)
        print("---")
        print_journey(start, steps, end)
        print("---")

        if travel_time:
            print(f"   🕒 {travel_time} | 🔁 {changes} skift")
        else:
            print("   ⚠️ No connection found")

        time.sleep(DELAY_BETWEEN_SEARCHES)



if __name__ == "__main__":
    main()
