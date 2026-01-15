import yaml
import webbrowser
import urllib.parse
import time


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


def open_google_maps_directions(start_address, destination_address):
    base_url = "https://www.google.com/maps/dir/"
    url = base_url + urllib.parse.quote(start_address) + "/" + urllib.parse.quote(destination_address)
    webbrowser.open(url)
    print("#"*50)
    print("opening browser")


def main():
    vehicle_file = "vehicles.txt"
    config_file = "zip_code_ignore.yml"

    START_ADDRESS = "Nørreport Station, Copenhagen"
    DELAY_BETWEEN_TABS = 1.5  # seconds

    ignored_zip_codes = load_ignored_zip_codes(config_file)
    vehicles = parse_vehicle_file(vehicle_file, ignored_zip_codes)

    print(f"Opening Google Maps for {len(vehicles)} vehicles...\n")

    for v, i in enumerate(vehicles):
        print(f"Opening route to {v['plate']} ({v['address']})")
        if i==0:
            open_google_maps_directions(START_ADDRESS, v["address"])
        time.sleep(DELAY_BETWEEN_TABS)


if __name__ == "__main__":
    main()
