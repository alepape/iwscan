# Scope

iwscan is a simple python script that parses the result if the "iw" command and exposes it as prometheus metrics and as a Home Assistant sensor via MQTT.
It's also available as a docker image on [alexlepape/iwscan](https://hub.docker.com/r/alexlepape/iwscan).
It can then be used to generate a nice Grafana dashboard:

![iwscan grafana](https://user-images.githubusercontent.com/2038195/236711840-6d818868-b787-4f71-935d-475c5d25bb57.png)

- it can be used to detect polluting wifi networks from the outside or selecting the right channels for your APs
- you can use overrides to get rid of the weird / long SSIDs (ex: all those `\x00\x00\x00\x00\x00\x00...`)

# Notes

- For now, a few things are hard coded but should suit most RPi setup where the SBC has its main connection to the network via ethernet, leaving the Wifi module free to be used for scanning 
  - wlan0 is the interface used
  - 5024 is the TCP port exposed
- The docker version (based on python:3.9.13-alpine) needs 2 things to work
  - priviledge mode
  - network type "host"
- The Home Assistant setup is hardcoded to provide 3 measures per configured SSID
  - frequency
  - channel
  - signal
- To enable the Home Assistant setup, ENV variables need to be specified in DOCKER, or a config.json file needs to be added next to python script (see setup below). Also note that the production of the sensor values depend on prometheus to regularly query the endpoint. Therefore, the frequency of update of the sensor depends on the prometheus configuration.

# Setup

## Docker

- deploy the image [alexlepape/iwscan](https://hub.docker.com/r/alexlepape/iwscan) on your RPi Docker
- don't forget to check that it's privileged and the network type to host
- example docker compose:
```yaml
  iwscan:
    container_name: iwscan
    network_mode: "host"
    image: alexlepape/iwscan:latest
    environment:
      - TOPIC_PREFIX=homeassistant/sensor/ssids
      - MQTT_HOST=<your MQTT broker IP>
      - MQTT_PORT=1883
      - MQTT_USR=<your MQTT broker username>
      - MQTT_PWD=<your MQTT broker password>
      - SSID=<the SSID you want to monitor>    
    restart: unless-stopped
    privileged: true
```
- test it on `http://<your docker IP>:5024/metrics`

## Direct

- if you want the HA to work, create a config.json file such as
```json
{
    "topic": "homeassistant/sensor/ssids",
    "mqtt_host": "<your MQTT broker IP>",
    "mqtt_port": 1883,
    "mqtt_user": "<your MQTT broker username>",
    "mqtt_pwd": "<your MQTT broker password>",
    "ssids": [ "SSID1", "SSID2" ]
}
```
- just run `sudo python3 iwscan.py` - note: sudo-ing might not be required depending on your setup.
- note that in that case, several SSIDs can be monitored

## Using it

- add `http://<your docker IP>:5024/metrics` as a source in your prometheus:
```yaml
  - job_name: 'wifiscan'
    static_configs:
      - targets: ['<IP>:5024']
```
- an example dashboard can be found [here](grafana.json)
- you can just point it to the proper node (your RPi IP)

