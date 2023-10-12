# ChirpStack Device Statistics

This script generates a JSON file with the statistics of each application of each tenant in a ChirpStack instance.

## Usage

Recommended usage is via virtualenv. A convenient Makefile is included to easily create and run the scripts inside a virtual python environment. If you prefer you can also do it manually:

```
pip install virtualenv
virtualenv .venv
source .venv/bin/activate
pip install -Ur requirements.txt
deactivate
```

The lines above will create the environment and install the required packages. Then, to run the scripts you will have to:

```
source .venv/bin/activate
python statstics.py
deactivate
```

Steps to export devices from a TTS application into a ChirpStack application.

1) Copy the `config.example.yml` file into `config.yml` and edit it to match your requirements.
1) Run the script and provide missing information. The script will generate a JSON in the local folder with the output.

## Output

The script outputs a JSON file with a ist of objects. Each object has the information about a specific application from a specific tenant. The information includes:

* number of devices
* uplinks over the last 24h
* uplinks per channel and DR

Example output:

```
> python statistics.py 
Getting metrics from tenants, applications and devices
> cat statistics.json | jq
[
  {
    "timestamp": 1697129766,
    "tenant_id": "52f14cd4-c6f1-4fcd-8f37-4025e4d49242",
    "tenant_name": "xoseperez",
    "application_id": "023fdefb-df27-4c07-a152-1ef72b1e5908",
    "application_name": "xp-airquality",
    "num_devices": 2,
    "uplinks": 490,
    "f867700000": 54,
    "f868500000": 62,
    "f867300000": 55,
    "f867100000": 65,
    "f868100000": 62,
    "f868300000": 58,
    "f867500000": 71,
    "f867900000": 63,
    "dr5": 490
  }
]

```