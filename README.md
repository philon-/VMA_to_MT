# meshtastic_VMA
Broadcast issued VMAs on your local [Meshtastic](https://meshtastic.org/) network

Uses [Sveriges Radio's API](https://vmaapi.sr.se/index.html?urls.primaryName=v3.0-beta) for Important Public Announcements / Viktigt meddelande till allmänheten (3.0-beta) to extract alerts for a given region and broadcast to a local Meshtastic network.

Requires `meshtastic` [Python CLI](https://meshtastic.org/docs/software/python/cli/) to be installed and in the user's PATH.

## Usage

Set up the script to run as a service using your service manager of choice.

```
meshtastic_VMA.py [-h] [--verbose] [--ch-index CH_INDEX] [--interval INTERVAL] [--geocode GEOCODE]

Fetches Swedish VMAs from Swedish Radio and broadcasts them to your local Meshtastic network.

options:
  -h, --help           show this help message and exit
  --verbose            Increase output verbosity. [False]
  --ch-index CH_INDEX  Meshtastic channel to which messages will be sent. [0]
  --interval INTERVAL  Time interval in seconds at which VMA API will be fetched. [120]
  --geocode GEOCODE    Geocode as specified by SCB. [00]
  ```

Available geocodes can be found at [SCB's website](https://www.scb.se/hitta-statistik/regional-statistik-och-kartor/regionala-indelningar/lan-och-kommuner/lan-och-kommuner-i-kodnummerordning). The default value 00 corresponds to all of Sweden.

## Notes

Any alerts retrieved in the first API call will not be broadcasted. This is intentional in order to not flood the network with duplicate alerts if the script is restarted.

Messages (alert type and description) longer than 200 bytes will be truncated in order to fit within one Meshtastic message.

Please be sensible when setting the interval setting as to not put undue strain on the API service.
