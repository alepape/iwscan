#!/bin/sh
# get some vars from env and write to json

RUNTIME_CONF="{
    \"topic\": \"$TOPIC_PREFIX\",
    \"mqtt_host\": \"$MQTT_HOST\",
    \"mqtt_port\": $MQTT_PORT,
    \"mqtt_user\": \"$MQTT_USR\",
    \"mqtt_pwd\": \"$MQTT_PWD\",
    \"ssids\": [ \"$SSID\" ]
}"
echo "configuration loaded:"
echo $SSID

echo $RUNTIME_CONF > ./config.json
echo "json created - starting python..."

# OOTB starting command
python ./iwscan.py