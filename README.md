# Scope

iwscan is a simple python script that parses the result if the "iw" command and exposes it as prometheus metrics.
It's also available as a docker image on [alexlepape/iwscan](https://hub.docker.com/r/alexlepape/iwscan)

# Notes

- For now, a few things are hard coded but should suit most RPi setup where the SBC has its main connection to the network via ethernet, leaving the Wifi module free to be used for scanning 
  - wlan0 is the interface used
  - 5024 is the TCP port exposed
- The docker version (based on arm64v8/python:3.11-rc-bullseye) needs 2 things to work
  - priviledge mode
  - network type "host"

