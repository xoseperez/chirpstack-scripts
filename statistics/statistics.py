import os
import sys

import grpc
import json
from datetime import datetime

from chirpstack_api import api
import collections, functools, operator

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.config import Config
from common.utils import get_pass, get_input, convert_to_seconds, shell

# -----------------------------------------------------------------------------
# Methods
# -----------------------------------------------------------------------------

def get_tenants(channel, auth_token):

  client = api.TenantServiceStub(channel)
  req = api.ListTenantsRequest()
  req.limit = 10000
  req.offset = 0
  try:
    resp = client.List(req, metadata=auth_token)
  except Exception as err:
    print(f"Error getting the list of tenants ({str(err)})")
    return {}

  tenants = dict([ (tenant.id, tenant.name) for tenant in resp.result ])
  return tenants

def get_applications(channel, auth_token, tenant_id):

  client = api.ApplicationServiceStub(channel)
  req = api.ListApplicationsRequest()
  req.limit = 10000
  req.offset = 0
  req.tenant_id = tenant_id
  try:
    resp = client.List(req, metadata=auth_token)
  except Exception as err:
    print(f"Error getting the list of applications for tenant {tenant_id} ({str(err)})")
    return {}

  applications = dict([ (application.id, application.name) for application in resp.result ])
  return applications

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

  devices = [ device.dev_eui for device in resp.result ]
  return devices

def get_metrics(channel, auth_token, device_id):

  client = api.DeviceServiceStub(channel)
  req = api.GetDeviceLinkMetricsRequest()
  req.dev_eui = device_id
  req.start.seconds = int(datetime.now().timestamp() - 60*60*24)
  req.end.seconds = int(datetime.now().timestamp())
  req.aggregation = 1 # 0: hour, 1: day, 2: month
  try:
    resp = client.GetLinkMetrics(req, metadata=auth_token)
  except Exception as err:
    print(f"Error getting the metrics from device {device_id} ({str(err)})")
    return {}

  fields = []
  fields += [ ("uplinks", int(sum(dataset.data))) for dataset in resp.rx_packets.datasets ]
  fields += [ ("f"+dataset.label, int(sum(dataset.data))) for dataset in resp.rx_packets_per_freq.datasets ]
  fields += [ ("dr"+dataset.label, int(sum(dataset.data))) for dataset in resp.rx_packets_per_dr.datasets ]
  return dict(fields)

# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

# Hello
print("Getting metrics from tenants, applications and devices")

# Read configuration
config = Config()

# Define the API key meta-data.
auth_token = [("authorization", "Bearer %s" % config.get('server.api_token'))]

# Connect without using TLS.
channel = grpc.insecure_channel(config.get('server.host', 'localhost:8080'))

# Current timestamp
now = int(datetime.now().timestamp())

# Header
headers = ["timestamp", "tenant_id", "tenant_name", "application_id", "application_name", "num_devices"]

# Open filename
with open(config.get('filename', 'stats.json'), "w") as f:

  # Start array
  f.write('[')

  # Get Tenants
  tenants = get_tenants(channel, auth_token)

  # Lines
  line = 0

  # Applications
  for tenant in tenants:
    applications = get_applications(channel, auth_token, tenant)
    for application in applications:
      
      devices = get_devices(channel, auth_token, application)
      data = [ now, tenant, tenants[tenant], application, applications[application], len(devices) ]
      output = dict(zip(headers, data))

      metrics = []
      for device in devices:
        metrics.append(get_metrics(channel, auth_token, device))
      result = dict(functools.reduce(operator.add, map(collections.Counter, metrics)))
      output.update(result)
      
      if not 0 == line:
        f.write(',')
      f.write('\n')
      f.write(json.dumps(output))

      line += 1

  # End array
  f.write('\n]\n')


