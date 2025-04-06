#!/usr/bin/env python3

from time import sleep
from datetime import datetime
import requests
import subprocess
import sys
import logging
import argparse

_LOGGER = logging.getLogger(__name__)

def truncate_utf8(s, max_bytes=200):

    # If our string is already shorter than 200 bytes, do nothing 
    if len(s.encode('utf-8')) <= max_bytes: 
        return [s]

    # Worst case suffix length
    suffix_length = len(f" {MAX_MESSAGES}/{MAX_MESSAGES}".encode('utf-8')) 
    extra_suffix_length = 0

    words = s.split(" ")
    chunks = []
    current_words = []
    current_size = 0  # track byte length in UTF-8

    for word in words:
        word_bytes = word.encode('utf-8')
        word_size = len(word_bytes)

        # If the word alone is bigger than max_bytes, skip it. This is extremely unlikely.
        if word_size > max_bytes:
            continue
        extra = 1 + word_size

        if len(chunks) == MAX_MESSAGES-1:
            extra_suffix_length = 6

        # If we add " " + word, measure extra bytes
        # (space is 1 byte in UTF-8, plus the new word's bytes)

        if current_size + extra <= max_bytes-suffix_length-extra_suffix_length:
            # Fits in current chunk
            current_words.append(word)
            current_size += extra
        else:
            # Finalize current chunk
            chunks.append(" ".join(current_words))


            if len(chunks) == MAX_MESSAGES:
                chunks[-1] += " [...]"
                # Start a new chunk with the current word
                current_words = []
                current_size = 0

                break

            # Start a new chunk with the current word
            current_words = [word]
            current_size = word_size

    # Finalize any remaining words in the last chunk
    if current_words:
        chunks.append(" ".join(current_words))

    for i in range(len(chunks)):
        chunks[i] = chunks[i].strip() + f" {i+1}/{len(chunks)}"

    return chunks

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

    alert_ids = {str(item.get("identifier")) for item in data['alerts']}
    return alert_ids, data


def call_meshtastic(template, message, output=True):
    """
    Call meshtastic to send message
    """
    meshtastic_cmd = template.copy()
    meshtastic_cmd.append(message)

    try:
        result = subprocess.run(meshtastic_cmd, capture_output = True, text = True, check = True)
        if output:
            _LOGGER.info(result.stdout.strip())
        return result
    except subprocess.CalledProcessError as e:
        _LOGGER.error("Error running meshtastic command: %s", e)
        return False


def main():
    """
    Main loop:
    1. Fetches alerts
    2. Checks for new alerts vs. previously seen,
    3. Parses data and generates a message
    4. Sends message to meshtastic
    5. Waits before repeating.
    """
    first = True

    known_alerts = set()  # Keep track of the alerts we have seen

    while True:
        # Fetch current alerts
        current_alerts, data = fetch_alerts()

        # Find what's new compared to known_alerts
        new_alerts = current_alerts - known_alerts

        _LOGGER.info("Got %s alerts in total of which %s were new.", len(current_alerts), len(new_alerts))

        if not first: # Make sure we don't spam the channel when script starts. Assume any alerts that are already present have been sent already

            for id in new_alerts:
                alert = next((d for d in data['alerts'] if d["identifier"] == id), None)

                if alert['status'] != "Test" and alert['msgType'] == "Cancel": # The previous alert is no longer active. Notably, the info field is empty.
                    message = f"UPPHÄVD: Varningen utfärdad {datetime.fromisoformat(alert['sent']).strftime('%Y-%m-%d %H:%M')} är inte längre aktuell. Faran är över."

                elif alert['status'] == "Exercise" and alert['info'][0]['event'] == "Kvartalstest av utomhussignal för viktigt meddelande till allmänheten (VMA)":
                    message = "VMA TEST: Idag kl 15 testas “Viktigt meddelande”-signalen - 7s ljud följt av 14s tystnad under 2min. Efter testet ljuder “Faran över” - en 30s lång signal."

                elif alert['status'] == "Exercise":
                    message = f"ÖVNING: {alert['info'][0]['description']}"

                elif alert['status'] == "Actual":
                    message = f"VMA: {alert['info'][0]['description']}"

                else:
                    continue
                
                # Todo: Send repeated messages
                messages = truncate_utf8(message)
                _LOGGER.debug(f"Alert was split into {len(messages)} messages. Sending now")

                for message in messages:
                    call_meshtastic(MESHTASTIC_CMD_TEMPLATE, message)
                    #sleep(5)

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

    # Required:
    parser.add_argument("executable", type=str, help="Path to meshtastic executable")

    # Optional
    parser.add_argument("--verbose", action="store_true", help="Increase output verbosity. [False]")
    parser.add_argument("--connection-type", type=str, default="host", help="Connection type (host/port/ble) [host]")
    parser.add_argument("--connection-argument", type=str, default="localhost", help="Connection argument [localhost]")
    parser.add_argument("--ch-index", type=str, default="0", help="Meshtastic channel to which messages will be sent. [0]")
    parser.add_argument("--api-uri", type=str, default="https://vmaapi.sr.se/api/v3-beta/alerts", help="API URI to fetch [https://vmaapi.sr.se/api/v3-beta/alerts]")
    parser.add_argument("--api-interval", type=int, default=120, help="Time interval in seconds at which API will be fetched. [120]")
    parser.add_argument("--api-geocode", type=str, default="00", help="Geocode. [00]")
    parser.add_argument("--max-messages", type=int, default=2, help="Maximum number of messages to send for each alert. Will trunkate to this number of messages. [2]")
    parser.add_argument("--repeat-number", type=int, default=2, help="Number of re-broadcasts to perform. [2]")
    parser.add_argument("--repeat-cycles", type=int, default=2, help="Number of api-intervals between rebroadcast. [2]")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.DEBUG)
    else:
        logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)

    INTERVAL = args.api_interval
    CHANNEL = args.ch_index
    MAX_MESSAGES = args.max_messages
    REPEAT_NUM_MSG = args.repeat_number
    REPEAT_NUM_CYCL = args.repeat_cycles

    API_URL = f"{args.api_uri}?geocode={args.api_geocode}"
    MESHTASTIC_CMD_TEMPLATE = [args.executable, "--"+args.connection_type, args.connection_argument, "--ch-index", CHANNEL, "--sendtext"]  # Message will be appended at the end

    _LOGGER.info(f"""Starting meshtastic_VMA\n
Parameters:
    verbose: {args.verbose}
    executable: {args.executable}
    connection-type: {args.connection_type}
    connection-argument: {args.connection_argument}
    ch-index: {CHANNEL}
    api-uri: {args.api_uri}
    api-interval: {INTERVAL}
    api-geocode: {args.api_geocode}
    max-messages: {MAX_MESSAGES}
    repeat-number: {REPEAT_NUM_MSG}
    repeat-cycles: {REPEAT_NUM_CYCL}

    Constructed API_URL: {API_URL}
    Constructed MESHTASTIC_CMD_TEMPLATE: {" ".join(MESHTASTIC_CMD_TEMPLATE)} [message]
""")

    # Attempt connecting to radio
    if not call_meshtastic([args.executable], "--info", False):
        raise Exception("Could not communicate with meshtastic device") 
    
    main()