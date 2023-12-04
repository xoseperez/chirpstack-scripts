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

APP_NAME = "Chirpstack Gateway Importer"
APP_VERSION = "v1.0.0"

# -----------------------------------------------------------------------------
# Methods
# -----------------------------------------------------------------------------

# Globals
updated = 0
created = 0

def create_or_update(client, auth_token, gateway, tenant_id, tags):

  global updated, created

  exists = True
  gateway_eui = gateway.get('eui')
  if gateway_eui == None:
    logging.error(f"Missing EUI")
    return

  # Check if gateway already exists
  req = api.GetGatewayRequest()
  req.gateway_id = gateway_eui
  try:
    resp = client.Get(req, metadata=auth_token)
  except:
    exists = False

  if not exists:
    req = api.CreateGatewayRequest()
  else: 
    req = api.UpdateGatewayRequest()

  req.gateway.gateway_id = gateway_eui
  req.gateway.name = gateway.get('name', gateway.get('gateway_id', gateway_eui))
  req.gateway.description = gateway.get('description', gateway.get('gateway_id', gateway_eui))
  req.gateway.location.latitude = float('0'+gateway.get('latitude', 0))
  req.gateway.location.longitude = float('0'+gateway.get('longitude', 0))
  req.gateway.location.altitude = float('0'+gateway.get('altitude', 0))
  req.gateway.location.source = 2 # CONFIG
  req.gateway.location.accuracy = 0
  req.gateway.tenant_id = tenant_id
  for tag in tags:
    req.gateway.tags.update(tag)
  #req.gateway.metadata = Struct()
  req.gateway.stats_interval = 30

  if not exists:
    try:
      resp = client.Create(req, metadata=auth_token)
    except Exception(e):
      logging.error(f"{gateway_eui}: error creating gateway (usually not enough permissions)")
      return
  else:
    try:
      resp = client.Update(req, metadata=auth_token)
    except:
      logging.error(f"{gateway_eui}: error updating gateway (usually not enough permissions)")
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
    parser.add_argument("--config", "-c", default="config.yml", help = "Configuration file")
    parser.add_argument("--server", dest="CHIRPSTACK_SERVER", help = "Chirpstack server (ip/domain and port)")
    parser.add_argument("--api-token", dest="CHIRPSTACK_API_TOKEN", help = "API token with permissions on the tenant gateways")
    parser.add_argument("--tenant-id", dest="CHIRPSTACK_TENANT_ID", help = "Tenant EUI to assign gateways to")
    parser.add_argument("--filename", dest="FILENAME", help = "File with the data to import")
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
      config.set('chirpstack.api_token', get_pass("API token with permissions on the tenant gateways", config.get('chirpstack.api_token')))
      config.set('chirpstack.tenant_id', get_input("Tenant EUI to assign gateways to", config.get('chirpstack.tenant_id')))
      config.set('filename', get_input("File with the data to import", config.get('filename')))
      print()

    # Some variables and checks
    filename = config.get('filename')
    if not filename:
        logging.error("ERROR: Missing file to import")
        sys.exit()
    tenant_id = config.get('chirpstack.tenant_id')
    if not tenant_id:
        logging.error("ERROR: Missing tenant_id to import to")
        sys.exit()
    server = config.get('chirpstack.server', 'localhost:8080')
    tags = config.get('chirpstack.tags', [])

    # Hello
    logging.info(f"Importing gateways from {filename} to {server} on tenant ID {tenant_id}")

    # Define the API key meta-data.
    auth_token = [("authorization", "Bearer %s" % config.get('chirpstack.api_token'))]

    # Connect without using TLS.
    channel = grpc.insecure_channel(server)

    # Gateway-queue API client.
    client = api.GatewayServiceStub(channel)

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
          gateway = dict(zip(header, row))
          create_or_update(client, auth_token, gateway, tenant_id, tags)

    logging.info(f"{created} gateways created")
    logging.info(f"{updated} gateways updated")

    total_time=round(time.time() - start, 2)
    logging.info(f"Total time {total_time}s")
