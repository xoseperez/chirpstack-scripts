import os
import sys

import grpc
import csv
import yaml
import argparse
from chirpstack_api import api

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.config import Config
from common.utils import get_pass, get_input, convert_to_seconds, shell

# -----------------------------------------------------------------------------
# Methods
# -----------------------------------------------------------------------------

def get_tags(client, auth_token):

  tags = {}

  # List gateways
  req = api.ListGatewaysRequest()
  req.limit = 10000
  req.offset = 0
  try:
    resp = client.List(req, metadata=auth_token)
  except Exception as err:
    print("Error getting the list of gateways", err)
    return tags

  gateway_ids = [ gateway.gateway_id for gateway in resp.result ]
  
  for gateway_id in gateway_ids:
    
    # Get tags
    req = api.GetGatewayRequest()
    req.gateway_id = gateway_id
    try:
      resp = client.Get(req, metadata=auth_token)
    except Exception as err:
      print("Error getting gateway data for gateway %s" % gateway_id, err)

    tags[gateway_id] = resp.gateway.tags
    
  return tags

# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    
  # Hello
  print("Creating chirpstack-packet-multiplexer config file from gateway tags")

  # CLI arguments
  parser = argparse.ArgumentParser()
  parser.add_argument("--config", "-c", default="config.yml", help = "Configuration file")
  args = parser.parse_args()

  # Read configuration
  config = Config(file=args.config)

  # Define the API key meta-data.
  auth_token = [("authorization", "Bearer %s" % config.get('server.api_token'))]

  # Connect without using TLS.
  channel = grpc.insecure_channel(config.get('server.host', 'localhost:8080'))

  # Device-queue API client.
  client = api.GatewayServiceStub(channel)

  # Get the tags from the gateways
  tags = get_tags(client, auth_token)

  # Get default backends
  default_backends = config.get('multiplexer.default_backends', 'local').replace(',',' ').split()

  # Filter and transverse 'packet-multiplexer' tag
  map = {}
  for eui in tags:
    backends = []
    if 'packet-multiplexer' in tags[eui]:
      backends = tags[eui]['packet-multiplexer'].replace(',',' ').split()
      backends = list(filter(None, backends))
    if len(backends) == 0:
      backends = default_backends
    for backend in backends:
      if not backend in map:
        map[backend] = []
      map[backend].append(eui)

  # Open file
  with open(config.get('multiplexer.configfile', 'chirpstack-packet-multiplexer.toml'), "w") as f:

    # Header
    f.write("[general]\n  log_level=%d\n\n[packet_multiplexer]\n  bind=\"%s\"\n" % (
      config.get("log_level", 4), 
      config.get("multiplexer.bind", "0.0.0.0:1700")
    ))

    # Backends
    for backend in config.get('multiplexer.backends', {}).as_dict():
      f.write("\n[[packet_multiplexer.backend]]\n  host=\"%s\"\n  uplink_only=%s\n  gateway_ids=%s\n" % (
        config.get(f"multiplexer.backends.{backend}.host"), 
        str(config.get(f"multiplexer.backends.{backend}.uplink_only", True)).lower(), 
        str(map.get(backend, [])).replace('\'', '"'))
      )
