#!/usr/bin/env python3

from time import sleep
import requests
import subprocess
import sys
import logging
import argparse

_LOGGER = logging.getLogger(__name__)

def truncate_utf8(s, max_bytes=200):
    encoded = s.encode('utf-8')
    truncated_encoded = encoded[:max_bytes]

    len_cut = len(encoded)-len(truncated_encoded)

    if len_cut > 0:
        _LOGGER.debug("Removed %s bytes from the message", str(len_cut))
        text = truncated_encoded[:max_bytes-5].decode('utf-8', errors='ignore')+"[...]"
    else:
        text = truncated_encoded.decode('utf-8', errors='ignore')

    return text


def fetch_alerts():
    """
    Fetch alerts from the VMA API.
    """
    _LOGGER.debug("Fetching %s", API_URL)
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()  # Raise an HTTPError if the response was unsuccessful
    except requests.RequestException as e:
        _LOGGER.error("Error fetching alerts: ", e)
        return set()

    data = response.json()
    _LOGGER.debug("Got %s alerts ...", len(data['alerts']))

    alert_ids = {str(item.get("identifier")) for item in data['alerts']}
    return alert_ids, data


def send_meshtastic_message(message):
    """
    Call meshtastic to send message
    """
    meshtastic_cmd = MESHTASTIC_CMD_TEMPLATE
    meshtastic_cmd.append("'"+message+"'")

    try:
        result = subprocess.run(meshtastic_cmd, capture_output = True, text = True, check = True)
        _LOGGER.info(result.stdout)
    except subprocess.CalledProcessError as e:
        _LOGGER.info(result.stderr)
        _LOGGER.error("Error sending message: %s to channel %s - %s", message, CHANNEL, e)


def main():
    """
    Main loop:
    1. Fetches alerts
    2. Checks for new alerts vs. previously seen,
    3. Parses data and generates a message
    4. Sends message to meshtastic
    5. Waits before repeating.
    """
    first = False

    known_alerts = set()  # Keep track of the alerts we have seen

    while True:
        # Fetch current alerts
        current_alerts, data = fetch_alerts()

        # Find what's new compared to known_alerts
        new_alerts = current_alerts - known_alerts
        _LOGGER.debug("... of which %s were new", str(len(new_alerts)))

        if not first: # Make sure we don't spam the channel when script starts. Assume any alerts that are already present have been sent already

            for id in new_alerts:
                alert = next((d for d in data['alerts'] if d["identifier"] == id), None)

                if alert['status'] != "Test" and alert['msgType'] == "Cancel": # The previous alert is no longer active. Notably, the info field is empty.
                    message = f"UPPHÄVD: Varningen utfärdad {alert['sent']} är inte längre aktuell. Faran är över."

                elif alert['status'] == "Exercise" and alert['info'][0]['event'] == "Kvartalstest av utomhussignal för viktigt meddelande till allmänheten (VMA)":
                    message = "VMA TEST: Idag kl 15 testas “Viktigt meddelande”-signalen - 7s ljud följt av 14s tystnad under 2min. Efter testet ljuder “Faran över” - en 30s lång signal."

                elif alert['status'] == "Exercise":
                    message = f"ÖVNING: {alert['info'][0]['description']}"

                elif alert['status'] == "Actual":
                    message = f"VMA: {alert['info'][0]['description']}"

                else:
                    continue
                
                message_truncated = truncate_utf8(message)

                send_meshtastic_message(message_truncated)

        # Update our known alerts set
        known_alerts = current_alerts
        if first:
            _LOGGER.debug("Variable 'first' = False")
            first = False

        # Sleep for INTERVAL seconds before checking again
        _LOGGER.debug("Sleeping for %s seconds...", INTERVAL)
        sleep(INTERVAL)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Fetches Swedish VMAs from Swedish Radio and broadcasts them to your local Meshtastic network.")

    parser.add_argument("--verbose", action="store_true", help="Increase output verbosity. [False]")
    parser.add_argument("--ch-index", type=str, default="0", help="Meshtastic channel to which messages will be sent. [0]")
    parser.add_argument("--interval", type=int, default="120", help="Time interval in seconds at which VMA API will be fetched. [120]")
    parser.add_argument("--geocode", type=str, default="00", help="Geocode as specified by SCB. [00]")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)

    INTERVAL = args.interval
    CHANNEL = args.ch_index

    API_URL = f"https://vmaapi.sr.se/api/v3-beta/alerts?geocode={args.geocode}"
    MESHTASTIC_CMD_TEMPLATE = ["/home/mesh/.local/bin/meshtastic", "--host", "localhost", "--ch-index", CHANNEL, "--sendtext"]  # Message will be appended at the end

    _LOGGER.info("Starting meshtastic_VMA")
    _LOGGER.info("Verbose: %s, interval: %s, geocode: %s, ch-index: %s", str(args.verbose), str(args.interval), args.geocode, args.ch_index)

    main()