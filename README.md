# 🚍 Green Mobility – Public Transport Route Analyzer

This project automates route lookups on **Rejseplanen.dk** using Selenium to determine **public transport travel time, changes, and detailed journey steps** for a list of vehicles and their locations.

It is designed to:
- Read vehicle data from a text file
- Ignore vehicles in specified ZIP codes
- Automatically search routes from a configurable start address
- Extract and print **structured journey details** (bus, train, metro, walking)
- Format output clearly with icons, alignment, and colors
- Handle Rejseplanen popups automatically
- Run **headless or with a visible browser**

---

## ✨ Features

- 🚗 Parse vehicle data (plate, address, battery %)
- 📍 Ignore ZIP codes via YAML config
- 🧭 Single browser tab reused for all searches
- ⏱ Extract:
  - Start time
  - End time
  - Travel duration
  - Number of changes
  - Step-by-step journey breakdown
- 🎨 Rich terminal output:
  - Icons per transport type
  - Color-coded battery levels
  - Color-coded line numbers (bus/train/metro)
  - Alignment for easy reading
- 🤖 Automatic popup handling (cookies + welcome screen)

---

## 📄 Input Files

### `vehicles.txt`
Expected format (repeating blocks):

```

Vehicle
AB12345
Street Name 1
1234 City
Ignored line
78%

```

Only vehicles **not** in ignored ZIP codes will be processed.

---

### `zip_code_ignore.yml`
```yaml
ignored_zip_codes:
  - "1000"
  - "2000"
```

---

### `start_address.txt`

```
Nørreport St
```

This is used as the **FROM** address for all route searches.

---

## 🧠 How It Works

1. Load ignored ZIP codes
2. Parse vehicle list
3. Open Rejseplanen once
4. Clean popups (cookies & welcome modal)
5. For each vehicle:

   * Reuse same browser tab
   * Search route
   * Click **“Detaljer”** on the first result
   * Extract journey steps
   * Print formatted output
6. Repeat until all vehicles are processed

---

## 🖨 Example Output

```
AB12345 → Ølstykke St
🔋 42%

start time:           08:08
🚶 walk:               11 min
🚇 metro (M3):          6 min
🚶 walk:                4 min
🚌 bus (23):             6 min
🚶 walk:                2 min
end time:             08:50
```

Battery colors:

* 🟣 Purple: < 20%
* 🔵 Blue: < 40%
* 🟢 Green: < 60%
* Default: ≥ 60%

---

## 🎨 Transport Line Color Rules

### 🚌 Bus

* Number → **Yellow**
* Letter:

  * A → Red
  * S → Blue
  * C → Light blue
  * E → Green

### 🚆 Train (S-train)

* A → Light blue
* B → Green
* C → Orange
* E → Purple
* F → Yellow
* H → Red

### 🚇 Metro

* M1 → Green
* M2 → Yellow
* M3 → Red
* M4 → Light blue

---

## 🕶 Running Headless (Optional)

To run Chrome without opening a window:

```python
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
```

Remove `--headless=new` if you want to watch the browser.

---

## 📦 Requirements

* Python 3.10+
* Google Chrome installed

### Python dependencies

```
pip install selenium webdriver-manager pyyaml
```

---

## ⚠ Notes & Caveats

* Rejseplanen HTML structure may change — selectors may need updates
* Network delays may require adjusting wait times
* Headless mode sometimes behaves slightly differently than visible mode

---

## 🟢 Status

✅ Stable
🛠 Actively extendable
🚀 Production-ready with minor hardening
