import os
import sys
import time

import grpc
import json
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

APP_NAME = "Chirpstack Device Importer Status"
APP_VERSION = "v1.0.0"

# -----------------------------------------------------------------------------
# Methods
# -----------------------------------------------------------------------------

def get_devices(channel, auth_token, application_id):

  client = api.DeviceServiceStub(channel)
  req = api.ListDevicesRequest()
  req.limit = 10000
  req.offset = 0
  req.application_id = application_id
  try:
    resp = client.List(req, metadata=auth_token)
  except Exception as err:
    print(f"Error getting the list of devices for application {application_id} ({str(err)})")
    return {}

  return resp.result

def get_device_activation(channel, auth_token, dev_eui):

  client = api.DeviceServiceStub(channel)
  req = api.GetDeviceActivationRequest()
  req.dev_eui = dev_eui
  try:
    resp = client.GetActivation(req, metadata=auth_token)
  except Exception as err:
    print(f"Error getting the activation keys for device {dev_eui} ({str(err)})")
    return {}

  return resp.device_activation

# -----------------------------------------------------------------------------

def get_net_id(dev_addr):
    
    if dev_addr == '':
      return 'Invalid'
    dev_addr_dec = int(dev_addr, 16)
    dev_addr_bin = f'{dev_addr_dec:0>32b}'
    type_id = dev_addr_bin.find('0')
    if type_id > 7:
      return 'Invalid'
    nwkid_bits = [6,6,9,11,12,13,15,17][type_id]
    nwkid_bin = dev_addr_bin[type_id+1:type_id+nwkid_bits+1]
    nwkid = int(nwkid_bin, 2)
    netid = (type_id << 21) + nwkid

    return f"{netid:0>6X}"



# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    
    # Start time
    start = time.time()
    now = datetime.utcnow()

    # CLI arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", default="config.yml", help = "Configuration file")
    parser.add_argument("--server", dest="CHIRPSTACK_SERVER", help = "Chirpstack server (ip/domain and port)")
    parser.add_argument("--api-token", dest="CHIRPSTACK_API_TOKEN", help = "API token with permissions on the application")
    parser.add_argument("--application-id", dest="CHIRPSTACK_APPLICATION_ID", help = "Application EUI to monitor the devices")
    parser.add_argument("-y", action='store_true', help = "Skip interactive promt")
    args = parser.parse_args()

    # Load configuration file
    config = Config(file=args.config, args=vars(args))

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
      config.set('chirpstack.application_id', get_input("Application EUI to monitor the devices", config.get('chirpstack.application_id')))
      print()

    # Some variables and checks
    application_id = config.get('chirpstack.application_id')
    if not application_id:
        logging.error("ERROR: Missing application_id to import to")
        sys.exit()
    server = config.get('chirpstack.server', 'localhost:8080')

    # Hello
    logging.info(f"Analyzing devices from app ID {application_id} on server {server}")

    # Define the API key meta-data.
    auth_token = [("authorization", "Bearer %s" % config.get('chirpstack.api_token'))]

    # Connect without using TLS.
    channel = grpc.insecure_channel(server)

    # Get devices
    devices = get_devices(channel, auth_token, application_id)
    num_devices = len(devices)

    # Dict to hold the number of devices per NetID
    net_ids = {}

    # Walk the devices to get their current DevAddr and NetID
    for device in devices:
        keys = get_device_activation(channel, auth_token, device.dev_eui)
        net_id = get_net_id(keys.dev_addr)
        if net_id in net_ids:
          net_ids[net_id] = net_ids[net_id] + 1
        else:
          net_ids[net_id] = 1

    # Output totals
    print(f"\nStatistics:\n{num_devices} in total\nNet ID:")
    for net_id in net_ids:
        percent = round(100 * net_ids[net_id] / num_devices, 2)
        print(f" * {net_id}: {net_ids[net_id]} devices ({percent}%)")


