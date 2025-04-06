# meshtastic_VMA
Broadcast issued VMAs on your local [Meshtastic](https://meshtastic.org/) network

Uses [Sveriges Radio's API](https://vmaapi.sr.se/index.html?urls.primaryName=v3.0-beta) for Important Public Announcements / Viktigt meddelande till allmänheten (3.0-beta) to extract alerts for a given region and broadcast to a local Meshtastic network.

Requires `meshtastic` [Python CLI](https://meshtastic.org/docs/software/python/cli/) to be installed.

## Usage

Set up the script to run as a service using your service manager of choice.

```
usage: meshtastic_VMA.py [-h] [--verbose] [--connection-type CONNECTION_TYPE] [--connection-argument CONNECTION_ARGUMENT] [--ch-index CH_INDEX] [--api-uri API_URI] [--api-interval API_INTERVAL] [--api-geocode API_GEOCODE] [--max-messages MAX_MESSAGES] [--repeat-number REPEAT_NUMBER] [--repeat-cycles REPEAT_CYCLES] executable

Fetches Swedish VMAs from Swedish Radio and broadcasts them to your local Meshtastic network.

positional arguments:
  executable            Path to meshtastic executable

options:
  -h, --help            show this help message and exit
  --verbose             Increase output verbosity. [False]
  --connection-type CONNECTION_TYPE
                        Connection type (host/port/ble) [host]
  --connection-argument CONNECTION_ARGUMENT
                        Connection argument [localhost]
  --ch-index CH_INDEX   Meshtastic channel to which messages will be sent. [0]
  --api-uri API_URI     API URI to fetch [https://vmaapi.sr.se/api/v3-beta/alerts]
  --api-interval API_INTERVAL
                        Time interval in seconds at which API will be fetched. [120]
  --api-geocode API_GEOCODE
                        Geocode. [00]
  --max-messages MAX_MESSAGES
                        Maximum number of messages to send for each alert. Will trunkate to this number of messages. [2]
  --repeat-number REPEAT_NUMBER
                        Number of re-broadcasts to perform. [2]
  --repeat-cycles REPEAT_CYCLES
                        Number of api-intervals between rebroadcast. [2]
  ```

Example:

``` python3 meshtastic_VMA.py /home/USER/.local/bin/meshtastic ```

Available geocodes can be found at [SCB's website](https://www.scb.se/hitta-statistik/regional-statistik-och-kartor/regionala-indelningar/lan-och-kommuner/lan-och-kommuner-i-kodnummerordning). The default value 00 corresponds to all of Sweden.

## Notes

Any alerts retrieved in the first API call will not be broadcasted. This is intentional in order to not flood the network with duplicate alerts if the script is restarted.

Alerts may be split into multiple nessages and/or truncated at 200 byte length in order to fit within Meshtastic message boundaries.

Please be sensible when setting the interval setting as to not put undue strain on the API service.
