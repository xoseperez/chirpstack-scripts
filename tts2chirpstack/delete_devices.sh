#!/bin/bash

# Get data from command line
while [[ $# -gt 0 ]]; do
  
  if [[ "${1}" == "-c" ]]; then
    CONFIG_FILE=$2
    shift
  
  elif [[ "${1}" == "-f" ]]; then
    CSV_FILE=$2
    shift
  
  fi

  shift

done

# Check data
if [[ -z "${CONFIG_FILE}" ]]; then
    echo "ERROR: Config file not provided"
    exit 1
fi
if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "ERROR: Config file does not exist"
    exit 1
fi
if [[ -z "${CSV_FILE}" ]]; then
    echo "ERROR: CSV file not provided"
    exit 1
fi
if [[ ! -f "${CSV_FILE}" ]]; then
    echo "ERROR: CSV file does not exist"
    exit 1
fi

# Get data from config file
APIKEY=$( yq '.thethingsstack.apikey' "${CONFIG_FILE}" )
APP_ID=$( yq '.thethingsstack.application_id' "${CONFIG_FILE}" )

if [[ -z "${APIKEY}" ]]; then
    echo "ERROR: Could not get token from config file"
    exit 1
fi
if [[ -z "${APP_ID}" ]]; then
    echo "ERROR: Could not get application_id from config file"
    exit 1
fi

# Start
LINES=$( wc -l < "${CSV_FILE}" )
echo "Processing $(( LINES - 1 )) lines"

FIRST=1

while read -r LINE; do

    # Skip header
    if [[ $FIRST -eq 1 ]]; then
        FIRST=0
        continue
    fi

    # Get device_id
    DEVICE_ID=$( echo "${LINE}" | cut -d',' -f1 )

    # Build request
    COMMAND="https://eu1.cloud.thethings.network/api/v3/applications/${APP_ID}/devices/${DEVICE_ID}"

    # Execute command
    RESPONSE=$( curl -s -o /dev/null -I -w "%{http_code}" \
        --header "Authorization: Bearer ${APIKEY}" \
        -X DELETE "${COMMAND}" )

    echo "${DEVICE_ID}: ${RESPONSE}"

done < "${CSV_FILE}"