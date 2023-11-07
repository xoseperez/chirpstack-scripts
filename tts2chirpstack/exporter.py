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

APP_NAME = "The Things Stack Device Exporter"
APP_VERSION = "v1.0.0"

# -----------------------------------------------------------------------------
# Methods
# -----------------------------------------------------------------------------

def row_to_csv(row):

    row = flatdict.FlatDict(row, delimiter='.')

    fields = []
    fields.append(row.get('ids.device_id'))
    fields.append(row.get('ids.device_id'))
    fields.append(row.get('ids.dev_eui'))
    fields.append(row.get('ids.join_eui'))
    fields.append(row.get('root_keys.app_key.key', ''))
    fields.append(row.get('session.dev_addr', ''))
    fields.append(row.get('session.keys.app_s_key.key', ''))
    fields.append(row.get('session.keys.nwk_s_enc_key.key', ''))
    fields.append(row.get('session.keys.s_nwk_s_int_key.key', ''))
    fields.append(row.get('session.keys.f_nwk_s_int_key.key', ''))
    fields.append(str(row.get('session.last_f_cnt_up', '')))
    fields.append(str(row.get('session.last_n_f_cnt_down', '')))
    fields.append(str(row.get('session.last_a_f_cnt_down', '')))
    
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
    parser.add_argument("--application-id", dest="THETHINGSSTACK_APPLICATION_ID", help = "Application ID")
    parser.add_argument("--apikey", dest="THETHINGSSTACK_APIKEY", help = "API Key to login")
    parser.add_argument("--active-since", dest="THETHINGSSTACK_ACTIVE_SINCE", help = "Active in the last X seconds (also time units or fixed datetime allowed)")
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
      config.set('thethingsstack.application_id', get_input("Application ID", config.get('thethingsstack.application_id')))
      config.set('thethingsstack.apikey', get_pass("API Key to login", config.get('thethingsstack.apikey')))
      config.set('thethingsstack.active_since', get_input("Active in the last X seconds (also time units or fixed datetime allowed)", config.get('thethingsstack.active_since')))
      print()

    # Some variables and checks
    filename_datetime = now.strftime("%Y%m%d%H%M%SZ")
    application_id = config.get('thethingsstack.application_id')
    if not application_id:
        logging.error("ERROR: Application ID not defined")
        sys.exit()

    # Get delta time in ISO
    delta = config.get('thethingsstack.active_since', '0')
    if '0' == delta:
        last_seen_after = '0'
        delta = 'all'
    elif delta.isnumeric():
        last_seen_after = (now - datetime.timedelta(seconds=int(delta))).isoformat()+'Z'
        delta = f"{delta}s"
    elif re.match("\d+[smhdw]", delta):
        last_seen_after = (now - datetime.timedelta(seconds=convert_to_seconds(delta))).isoformat()+'Z'
    else:
        last_seen_after = delta

    # Summary
    if '0' == last_seen_after:
        logging.info(f"Exporting all devices from {application_id}")
    else:
        logging.info(f"Exporting devices from {application_id} last updated after {last_seen_after}")

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

    # Get devices in application
    logging.debug("Getting application devices")
    (code, output) = shell(f"ttn-lw-cli end-devices search {application_id} --last-seen-at")
    if not 0 == code:
        logging.error(f"ERROR: not enough permissions for application {application_id}")
        sys.exit(2)
    devices=json.loads(output.decode('utf-8'))

    # Open filename
    folder = config.get('export_folder', './')
    filename = f"{folder}devices_{application_id}_{filename_datetime}_{delta}.csv"
    with open(filename, "w") as f:

        # Header
        f.write("device_id description dev_eui join_eui app_key dev_addr app_s_key nwk_s_enc_key s_nwk_s_int_key f_nwk_s_int_key f_cnt_up n_f_cnt_down a_f_cnt_down\n".replace(' ',','))

        # Walk devices
        processed=0
        for device in devices:

            # Check if we should filter it out
            last_seen_at = device.get('last_seen_at', '0')
            if last_seen_at < last_seen_after:
                continue
            
            # Get device ID
            device_id = device['ids']['device_id']
            logging.debug(f"Processing device {device_id}")
            
            # Get info from devices
            try:
                (code, output) = shell(f"ttn-lw-cli end-devices get {application_id} {device_id} --name --description --root-keys --session")
                if 0 == code:
                    try:
                        f.write(row_to_csv(json.loads(output.decode('utf-8'))) + "\n")
                        f.flush()
                        processed += 1
                    except Exception as e:
                        logging.error(f"ERROR: parsing device {device_id}: {str(e)}")    
                else:
                    logging.error(f"ERROR: processing device {device_id}")
            except Exception as e:
                logging.error(f"ERROR: processing device {device_id}: {str(e)}")    

    logging.info(f"{processed} devices processed and saved into {filename}")

    total_time=round(time.time() - start, 2)
    logging.info(f"Total time {total_time}s")
