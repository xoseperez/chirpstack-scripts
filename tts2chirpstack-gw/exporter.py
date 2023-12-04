import os
import sys
import json
import time
import re
import logging
import datetime
import argparse
import flatdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.config import Config
from common.utils import get_pass, get_input, convert_to_seconds, shell

# -----------------------------------------------------------------------------
# Globals
# -----------------------------------------------------------------------------

APP_NAME = "The Things Stack Gateway Exporter"
APP_VERSION = "v1.0.0"

# -----------------------------------------------------------------------------
# Methods
# -----------------------------------------------------------------------------

def row_to_csv(row):

    row = flatdict.FlatterDict(row, delimiter='.')

    fields = []
    fields.append(row.get('ids.gateway_id'))
    fields.append(row.get('ids.eui'))
    fields.append(row.get('name'))
    fields.append(row.get('description', '').replace('\n', '. '))
    fields.append(row.get('frequency_plan_id', ''))
    #fields.append(row.get('lbs_lns_secret.value', ''))
    fields.append(str(row.get('status_public', False)))
    fields.append(str(row.get('location_public', False)))
    fields.append(str(row.get('antennas.0.location.latitude', '')))
    fields.append(str(row.get('antennas.0.location.longitude', '')))
    fields.append(str(row.get('antennas.0.location.altitude', '')))
    fields.append(row.get('antennas.0.placement', ''))
    
    return ','.join(fields)

# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    
    # Start time
    start = time.time()
    now = datetime.datetime.utcnow()

    # CLI arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", default="config.yml", help = "Configuration file")
    parser.add_argument("--apikey", dest="THETHINGSSTACK_APIKEY", help = "API Key to login")
    parser.add_argument("-y", action='store_true', help = "Skip interactive promt")
    args = parser.parse_args()

    # Load configuration file
    config = Config(file=args.config, args=vars(args))

    # Set logging level based on settings (10=DEBUG, 20=INFO, ...)
    level=config.get("logging.level", logging.DEBUG)
    logging.basicConfig(format='[%(asctime)s] %(message)s', level=level)
    logging.info(f"{APP_NAME} {APP_VERSION}")
    logging.debug(f"Setting logging level to {level}")
    logging.debug(f"Configuration read from '{args.config}'")

    # Interactive prompt
    if not args.y:
      logging.debug("Interactive prompt")
      print()
      config.set('thethingsstack.apikey', get_pass("API Key to login", config.get('thethingsstack.apikey')))
      print()

    # Some variables and checks
    filename_datetime = now.strftime("%Y%m%d%H%M%SZ")

    # Server
    host = config.get('thethingsstack.host', False)
    if host:
        logging.debug(f"Using server {host}")
        (code, output) = shell(f"ttn-lw-cli use {host} --overwrite")
        if not 0 == code:
            logging.error("ERROR: could not set TTS host")
            sys.exit(2)

    # Login
    logging.debug("Login in to your TTI/TTN account")
    apikey = config.get("thethingsstack.apikey", False)
    if apikey:
        (code, output) = shell(f"ttn-lw-cli login --api-key={apikey}")
    else:
        (code, output) = shell("ttn-lw-cli login")
    if not 0 == code:
        logging.error("Login error")
        sys.exit(2)
    logging.debug("Logged in correctly")

    # Get gateways
    logging.debug("Getting gateways")
    (code, output) = shell(f"ttn-lw-cli gateways list --all")
    if not 0 == code:
        logging.error(f"ERROR: not enough permissions to get the list of gateways")
        sys.exit(2)
    gateways=json.loads(output.decode('utf-8'))

    # Open filename
    folder = config.get('export_folder', './')
    filename = f"{folder}gateways_{filename_datetime}.csv"
    with open(filename, "w") as f:

        # Header
        f.write("gateway_id eui name description frequency_plan status_public location_public latitude longitude altitude placement\n".replace(' ',','))

        # Walk gateways
        processed=0
        for gateway in gateways:

            gateway_id = gateway['ids']['gateway_id']

            try:
                f.write(row_to_csv(gateway) + "\n")
                f.flush()
                processed += 1
            except Exception as e:
                logging.error(f"ERROR: parsing gateway {gateway_id}: {str(e)}")    

    logging.info(f"{processed} gateways processed and saved into {filename}")

    total_time=round(time.time() - start, 2)
    logging.info(f"Total time {total_time}s")
