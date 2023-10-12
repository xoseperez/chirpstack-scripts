import os
import sys
import time

import grpc
import csv
import logging
import argparse

from chirpstack_api import api
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.config import Config
from common.utils import get_pass, get_input, convert_to_seconds, shell

# -----------------------------------------------------------------------------
# Globals
# -----------------------------------------------------------------------------

APP_NAME = "Chirpstack Device Importer"
APP_VERSION = "v1.0.0"

# -----------------------------------------------------------------------------
# Methods
# -----------------------------------------------------------------------------

# Globals
updated = 0
created = 0

def create_or_update(client, auth_token, device, application_id, device_profile_id):

  global updated, created

  exists = True
  dev_eui = device.get('dev_eui')

  # Check if device already exists
  req = api.GetDeviceRequest()
  req.dev_eui = dev_eui
  try:
    resp = client.Get(req, metadata=auth_token)
  except:
    exists = False

  if not exists:

    # Create device
    req = api.CreateDeviceRequest()
    req.device.dev_eui = dev_eui
    req.device.name = device.get('device_id')
    req.device.description = device.get('description', dev_eui)
    req.device.application_id = application_id
    req.device.device_profile_id = device_profile_id
    req.device.skip_fcnt_check = False
    req.device.is_disabled = False
    req.device.join_eui = device.get('join_eui')
    try:
      resp = client.Create(req, metadata=auth_token)
    except:
      logging.error(f"{dev_eui}: error creating device")
      return

    # Create keys (not needed?)
    req = api.CreateDeviceKeysRequest()
    req.device_keys.dev_eui = dev_eui
    req.device_keys.nwk_key = device.get('app_key')
    req.device_keys.app_key = device.get('app_key')
    try:
      resp = client.CreateKeys(req, metadata=auth_token)
    except:
      logging.error(f"{dev_eui}: error creating keys")
      return
    
  # Activate keys
  if not '' == device.get('dev_addr'):
    req = api.ActivateDeviceRequest()
    req.device_activation.dev_eui = dev_eui
    req.device_activation.dev_addr = device.get('dev_addr')
    req.device_activation.app_s_key = device.get('app_s_key')
    req.device_activation.nwk_s_enc_key = device.get('nwk_s_enc_key')
    req.device_activation.s_nwk_s_int_key = device.get('s_nwk_s_int_key')
    req.device_activation.f_nwk_s_int_key = device.get('f_nwk_s_int_key')
    req.device_activation.f_cnt_up = int('0'+device.get('f_cnt_up'))
    req.device_activation.n_f_cnt_down = int('0'+device.get('n_f_cnt_down'))
    req.device_activation.a_f_cnt_down = int('0'+device.get('a_f_cnt_down'))
    try:
      resp = client.Activate(req, metadata=auth_token)
    except:
      logging.error(f"{dev_eui}: error activating device")
      return

  if exists:
    updated += 1
  else:
    created += 1


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    
    # Start time
    start = time.time()
    now = datetime.utcnow()

    # CLI arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", dest="CHIRPSTACK_SERVER", help = "Chirpstack server (ip/domain and port)")
    parser.add_argument("--api-token", dest="CHIRPSTACK_API_TOKEN", help = "API token with permissions on the application")
    parser.add_argument("--application-id", dest="CHIRPSTACK_APPLICATION_ID", help = "Application EUI to save the devices to")
    parser.add_argument("--device-profile-id", dest="CHIRPSTACK_DEVICE_PROFILE_ID", help = "Device profile EUI to use when creating the devices")
    parser.add_argument("--filename", dest="FILENAME", help = "File with the data to import")
    parser.add_argument("-y", action='store_true', help = "Skip interactive promt")
    args = parser.parse_args()

    # Load configuration file
    config = Config(args=vars(args))

    # Set logging level based on settings (10=DEBUG, 20=INFO, ...)
    level=config.get("logging.level", logging.DEBUG)
    logging.basicConfig(format='[%(asctime)s] %(message)s', level=level)
    logging.info(f"{APP_NAME} {APP_VERSION}")
    logging.debug(f"Setting logging level to {level}")

    # Interactive prompt
    if not args.y:
      logging.debug("Interactive prompt")
      print()
      config.set('chirpstack.server', get_input("Chirpstack server (ip/domain and port)", config.get('chirpstack.server')))
      config.set('chirpstack.api_token', get_pass("API token with permissions on the application", config.get('chirpstack.api_token')))
      config.set('chirpstack.application_id', get_input("Application EUI to save the devices to", config.get('chirpstack.application_id')))
      config.set('chirpstack.device_profile_id', get_input("Device profile EUI to use when creating the devices", config.get('chirpstack.device_profile_id')))
      config.set('filename', get_input("File with the data to import", config.get('filename')))
      print()

    # Some variables and checks
    filename = config.get('filename')
    if not filename:
        logging.error("ERROR: Missing file to import")
        sys.exit()
    application_id = config.get('chirpstack.application_id')
    if not application_id:
        logging.error("ERROR: Missing application_id to import to")
        sys.exit()
    device_profile_id = config.get('chirpstack.device_profile_id')
    if not device_profile_id:
        logging.error("ERROR: Missing device_profile_id to use when creatig new devices")
        sys.exit()
    server = config.get('chirpstack.server', 'localhost:8080')

    # Hello
    logging.info(f"Importing devices from {filename} to {server} on app ID {application_id}")

    # Define the API key meta-data.
    auth_token = [("authorization", "Bearer %s" % config.get('chirpstack.api_token'))]

    # Connect without using TLS.
    channel = grpc.insecure_channel(server)

    # Device-queue API client.
    client = api.DeviceServiceStub(channel)

    # Go thourhg the file rows
    with open(filename, 'r') as file:
      csvreader = csv.reader(file)
      line = 0
      for row in csvreader:
        line += 1
        if 1 == line:
          header = row
        else:
          logging.debug(f'Processing line {line-1}')
          device = dict(zip(header, row))
          create_or_update(client, auth_token, device, application_id, device_profile_id)

    logging.info(f"{created} devices created")
    logging.info(f"{updated} devices updated")

    total_time=round(time.time() - start, 2)
    logging.info(f"Total time {total_time}s")
