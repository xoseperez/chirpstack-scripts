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

APP_NAME = "Chirpstack Device Exporter"
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

def get_device_keys(channel, auth_token, dev_eui):

  client = api.DeviceServiceStub(channel)
  req = api.GetDeviceKeysRequest()
  req.dev_eui = dev_eui
  try:
    resp = client.GetKeys(req, metadata=auth_token)
  except Exception as err:
    print(f"Error getting the root keys for device {dev_eui} ({str(err)})")
    return {}

  return resp.device_keys

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

def get_device_link_metrics(channel, auth_token, dev_eui, days=7):

  now = datetime.utcnow()
  start_dt = (now - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')
  end_dt = now.strftime('%Y-%m-%dT%H:%M:%SZ')

  client = api.DeviceServiceStub(channel)
  req = api.GetDeviceLinkMetricsRequest()
  req.dev_eui = dev_eui
  req.start.FromDatetime(now - timedelta(days=days))
  req.end.FromDatetime(now)
  req.aggregation = 1 # days

  try:
    resp = client.GetLinkMetrics(req, metadata=auth_token)
  except Exception as err:
    print(f"Error getting the activation keys for device {dev_eui} ({str(err)})")
    return {}

  return resp

# -----------------------------------------------------------------------------

def row_to_csv(device, keys, activation, metrics, days = 7):

    fields = []
    fields.append(device.name)
    fields.append(device.description)
    fields.append(device.dev_eui)
    #fields.append(device.device_profile_id)
    #fields.append(device.device_profile_name)
    fields.append("")
    fields.append(keys.nwk_key) # nwk_key is actually the application key
    fields.append(activation.dev_addr)
    fields.append(activation.app_s_key)
    fields.append(activation.nwk_s_enc_key)
    fields.append(activation.s_nwk_s_int_key)
    fields.append(activation.f_nwk_s_int_key)
    fields.append(str(activation.f_cnt_up))
    fields.append(str(activation.n_f_cnt_down))
    fields.append(str(activation.a_f_cnt_down))
    fields.append(str(device.last_seen_at.seconds))
    
    for i in range(days):
      fields.append(str(int(metrics.rx_packets.datasets[0].data[i])))

    return ','.join(fields)


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
    filename_datetime = now.strftime("%Y%m%d%H%M%SZ")
    application_id = config.get('chirpstack.application_id')
    if not application_id:
        logging.error("ERROR: Missing application_id to import to")
        sys.exit()
    server = config.get('chirpstack.server', 'localhost:8080')

    # Hello
    logging.info(f"Exporting all devices from ChirpStack application '{application_id}'")

    # Define the API key meta-data.
    auth_token = [("authorization", "Bearer %s" % config.get('chirpstack.api_token'))]

    # Connect without using TLS.
    channel = grpc.insecure_channel(server)

    # Get devices
    devices = get_devices(channel, auth_token, application_id)
    num_devices = len(devices)

    # Open filename
    folder = config.get('export_folder', './')
    filename = f"{folder}cs_devices_{application_id}_{filename_datetime}_all.csv"
    with open(filename, "w") as f:

        # Header
        f.write("device_id description dev_eui join_eui app_key dev_addr app_s_key nwk_s_enc_key s_nwk_s_int_key f_nwk_s_int_key f_cnt_up n_f_cnt_down a_f_cnt_down last_seen_at 7 6 5 4 3 2 1\n".replace(' ',','))

        # Walk devices
        processed=0
        for device in devices:

            try:
                keys = get_device_keys(channel, auth_token, device.dev_eui)
                activation = get_device_activation(channel, auth_token, device.dev_eui)
                metrics = get_device_link_metrics(channel, auth_token, device.dev_eui, 7)
                f.write(row_to_csv(device, keys, activation, metrics, 7) + "\n")
                f.flush()
                processed += 1
            except Exception as e:
                logging.error(f"ERROR: processing device {device.dev_eui}: {str(e)}")    

    # Summary
    logging.info(f"{processed} devices processed and saved into {filename}")
    total_time=round(time.time() - start, 2)
    logging.info(f"Total time {total_time}s")


