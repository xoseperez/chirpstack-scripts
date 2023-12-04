# The Things Stack (TTN/TTI) to ChirpStack Gateway Exporter

Two-stage script to export gateways from a The Things Stack server (TTN/TTI) to a ChirpStack server. Gateways are exported with location. Only UDP gateways will work after export, BasicStation links should be configured manually on ChirpStack and the gateway.

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
python importer.py
deactivate
```

Steps to export gateways from a TTS application into a ChirpStack tenant.

1) Copy the `config.example.yml` file into `config.yml` and edit it to match your requirements.
1) Run the export script and provide missing information. The script will generate a CSV file under the `export` folder with all the gateways exported.
1) Run the import script and provide missing information and the CSV generated by the import script.

## Export

```
> python exporter.py --help
usage: exporter.py [-h] [--appkey THETHINGSSTACK_APPKEY] [-y]

options:
  -h, --help            Show this help message and exit
  --appkey              THETHINGSSTACK_APPKEY
                        App Key to login
  -y                    Skip interactive promt

```

The export script uses `ttn-lw-cli` in the background. If you don't have it installed you have to follow the instructions here: https://www.thethingsindustries.com/docs/the-things-stack/interact/cli/installing-cli/.

You can provide the configuration for both the exporter and importer in 3 different ways:

* the `config.yml` file
* via command line arguments (check the help output above)
* via environment variables (check the uppercase keys in the help output above)

For instance, in your `config.yml` file you can have something like:

```
thethingsstack:
  apikey: 'NNSXS.DWHQF...'
```

This will by default export all the gateways property of the user that issued the apikey. You can do the same by running:

```
python exporter.py --apikey "NNSXS.DWHQF..."
```

or

```
THETHINGSSTACK_APIKEY="NNSXS.DWHQF..." python exporter.py
```

For a complete unattended export, provide a personal `apikey` with the `View gateway information` and `View gateway location` rights and the run the script with the `-y` argument to skip the interactive prompt.

## Import

```
> python importer.py -h
usage: importer.py [-h] [--server CHIRPSTACK_SERVER] [--api-token CHIRPSTACK_API_TOKEN] [--tenant-id CHIRPSTACK_TENANT_ID][--filename FILENAME] [-y]

options:
  -h, --help            show this help message and exit
  --server              CHIRPSTACK_SERVER
                        Chirpstack server (ip/domain and port)
  --api-token           CHIRPSTACK_API_TOKEN
                        API token with permissions on the tenant gateways
  --tenant-id           CHIRPSTACK_TENANT_ID
                        Tenant EUI to assign gateways to
  --filename            FILENAME
                        File with the data to import
  -y                    Skip interactive promt
  ```

  The import script uses ChirpStack RPC API and can be configured in the same was as the export script (`config.yml`, command line arguments or environment variables). The only exception is the tags, these should be set in the `config.yml` file as an array under the `tags` property:

  ```
    # Tags to assign to gateways
    tags: 
      - packet-multiplexer: ttn local_uplink_only
  ```

  You will first have to create a tenant to host the gateways. The EUI for the tenanrt can be found under its name in the tenant dashboard page.

  The script expects a CSV file in the same format as the export script creates.