# Scope

iwscan is a simple python script that parses the result if the "iw" command and exposes it as prometheus metrics.
It's also available as a docker image on [alexlepape/iwscan](https://hub.docker.com/r/alexlepape/iwscan).
It can then be used to generate a nice Grafana dashboard:

![iwscan grafana](https://user-images.githubusercontent.com/2038195/236711840-6d818868-b787-4f71-935d-475c5d25bb57.png)

- it can be used to detect polluting wifi networks from the outside or selecting the right channels for your APs

# Notes

- For now, a few things are hard coded but should suit most RPi setup where the SBC has its main connection to the network via ethernet, leaving the Wifi module free to be used for scanning 
  - wlan0 is the interface used
  - 5024 is the TCP port exposed
- The docker version (based on arm64v8/python:3.11-rc-bullseye) needs 2 things to work
  - priviledge mode
  - network type "host"

# Setup

- deploy the image [alexlepape/iwscan](https://hub.docker.com/r/alexlepape/iwscan) on your RPi Docker
- don't forget to check that it's privileged and the network type to host
- example docker compose:
```yaml
  iwscan:
    container_name: iwscan
    network_mode: "host"
    image: alexlepape/iwscan:latest
    restart: unless-stopped
    privileged: true
```
- test it on `http://<your docker IP>:5024/metrics`
- add it as a source in your prometheus
```yaml
  - job_name: 'wifiscan'
    static_configs:
      - targets: ['<IP>:5024']
```
- an example dashboard can be found [here](grafana.json)
- you can just point it to the proper node (your RPi IP)
