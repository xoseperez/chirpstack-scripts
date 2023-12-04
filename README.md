# ChirpStack LoRaWAN Network Server Scripts

This repository contains different python script related to use with ChirpStack v4 using its API.

## Scripts

* multiplexer: creates a `chirpstack-packet-multiplexer` configuration file based on the script config file (`config.yml`) and inspecting the tags for the different gateways defined in the ChirpStack Server.
* statistics: output statistics for all the tenants and applications in a server to a JSON file for further processing.
* tts2chirpstack: export devices in an application in TTS (TTI/TTN) to a CSV file and later import them to a ChirpStack server using its API.
* tts2chirpstack-gw: export gateways in TTS (TTI/TTN) to a CSV file and later import them to a ChirpStack server using its API.

## Usage

Check the `README.md` file under each script folder for an detailed explanation of how to use them


Some script need a locl configuration file `config.yml`. You can find an example configuration file under `config.example.yml`, rename it and edit it to match your requirements.
Recommended usage is via virtualenv. A convenient Makefile is added to each script folder to easily create and run the script inside a virtual python environment by typing `make run`.

## License

MIT License

Copyright (c) 2023

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
