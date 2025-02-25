from http.server import BaseHTTPRequestHandler, HTTPServer
import socketserver
import re
import cgi
import sys
import json
import time
import subprocess
import paho.mqtt.client as mqtt

mqttc = set()

with open("config.json", "r") as jsonfile:
  config = json.load(jsonfile)

print("Config loaded - checking "+config['ssids'][0])

measures = '[{"measure":"freq","unit":"MHz"},{"measure":"channel","unit":null},{"measure":"signal","unit":"dB"},{"measure":"ssid","unit":null}]' # TODO: put me in docker ENV config
config["measures"] = json.load(measures)

# config = data
# {
#     "topic": "alepape/test/ssids",
#     "mqtt_host": "192.168.1.17",
#     "mqtt_port": 1883,
#     "mqtt_user": "alepape",
#     "mqtt_pwd": "tfg73pki",
#     "ssids": [ "AlexHD" ]
# }

def parseiwscan(iw_output):
    output = {}
    for line in iw_output.splitlines():
        if re.search("^BSS", line):
            #print(line)
            regex = r'(([0-9a-f]{2}[:-]){5}([0-9a-f]){2})'
            if (re.findall(regex, line)[0][0]):
                bss = re.findall(regex, line)[0][0]
            else:
                continue
            output[bss] = {}
        # if SSID: AlexSTD 
        if re.search("^\tSSID:", line):
            #print(line)
            regex = r'(?:^\tSSID: )(.*)'
            if (re.findall(regex, line)[0]):
                ssid = re.findall(regex, line)[0]
            else:
                ssid = ""
            #print("ssid=" + ssid)
            output[bss]["ssid"] = ssid
        # if signal: -22.00 dBm
        if re.search("^\tsignal:", line):
            #print(line)
            regex = r'(?:^\tsignal: )(.*)(?:\ .*)'
            if (re.findall(regex, line)[0]):
                signal = re.findall(regex, line)[0]
            else:
                signal = ""
            #print("signal=" + signal)
            output[bss]["signal"] = signal
        # if freq: 2417
        if re.search("^\tfreq:", line):
            #print(line)
            regex = r'(?:^\tfreq: )([0-9]*)'
            if (re.findall(regex, line)[0]):
                freq = re.findall(regex, line)[0]
            else:
                freq = ""
            #print("freq=" + freq)
            output[bss]["freq"] = freq
        # if primary channel: 8
        if re.search("^[\ |\t]*\*\ primary\ channel:", line):
            #print(line)
            regex = r'(?:^[\ |\t]*\*\ primary\ channel: )([0-9]*)'
            if (re.findall(regex, line)[0]):
                channel = re.findall(regex, line)[0]
            else:
                channel = ""
            #print("channel=" + channel)
            output[bss]["channel"] = channel
    #print(output)
    return output

def json2prom(parsed):
    output = "# HELP wifi_ssids All scanned SSIDs with their signal quality.\n"
    output += "# TYPE wifi_ssids gauge\n"
    for mac in parsed: # TODO: protect from missing attributes
        try:
            channel = parsed[mac]["channel"]
        except KeyError:
            channel = "?"
            print(parsed[mac]["ssid"] + " has no channel data")
        output += "wifi_ssids{mac=\"" + mac + "\",ssid=\"" + parsed[mac]["ssid"] + "\",freq=\"" + parsed[mac]["freq"] + "\",channel=\"" + channel + "\",} " + parsed[mac]["signal"] + "\n"
    return output

def filterSSIDjson(parsed, ssids):
    res = {}
    for mac in parsed: 
        if parsed[mac]["ssid"] in ssids:
            res[mac] = parsed[mac]
    return res

# Topic: homeassistant/sensor/TVPC/TVPC_cpuload/config
# {
#   "availability_topic": "homeassistant/sensor/TVPC/availability",
#   "icon": "mdi:chart-areaspline", -----------------------------> use wifi-star
#   "unique_id": "aa15fb6b-6cce-45e1-8101-e839b1292b55",
#   "unit_of_measurement": "%",
#   "device": {
#     "identifiers": "hass.agent-TVPC",
#     "manufacturer": "LAB02 Research",
#     "model": "Microsoft Windows NT 10.0.19045.0",
#     "name": "TVPC",
#     "sw_version": "2022.14.0"
#   },
#   "name": "TVPC_cpuload",
#   "state_topic": "homeassistant/sensor/TVPC/TVPC_cpuload/state"
# }

# TODO: availability per mac (needs a new topic)
# need a unique ID per sensor, that *stays* between runs!!!!?
# TODO: generate config
# TODO: send config @ frequency??? => upon start, w/ retain flag
# TODO: availability_topic as well as state_topic

def config2mqtt(client, topic, payloadobj, config):
# Topic: homeassistant/sensor/ssids/ + mac <= each mac is a device
# {
#   "availability_topic": "homeassistant/sensor/ssids/ + mac + /availability",
#   "icon": "mdi:wifi-star",
#   "unique_id": mac,
#   "unit_of_measurement": "MHz",
#   "device": {
#     "identifiers": "hass.agent-TVPC",
#     "manufacturer": "LAB02 Research",
#     "model": "Microsoft Windows NT 10.0.19045.0",
#     "name": "TVPC",
#     "sw_version": "2022.14.0"
#   },
#   "name": "TVPC_cpuload",
#   "state_topic": "homeassistant/sensor/TVPC/TVPC_cpuload/state"
# }
    for mac in payloadobj:
        root = topic + "/" + mac + "/"
        topic = root + "config"
        config = {}
        config["availability_topic"] = root + "availability"
        config["icon"] = "mdi:wifi-star"
        config["unique_id"] = mac
        config["unit_of_measurement"] = "" #TODO
        config["name"] = mac + "" #TODO
        config["state_topic"] = root + "" #TODO



def push2mqtt(client, topic, payloadobj):
    # parse the json first to build the topic structure:
    # mac/freq, mac/channel, mac/signal, and mac/ssid
    # TODO: availability_topic as well!!!

    for mac in payloadobj:
        client.publish(topic + "/" + mac + "/" + "freq", payloadobj[mac]["freq"], qos=1) # MHz
        client.publish(topic + "/" + mac + "/" + "channel", payloadobj[mac]["channel"], qos=1) # no unit
        client.publish(topic + "/" + mac + "/" + "signal", payloadobj[mac]["signal"], qos=1) # dB
        client.publish(topic + "/" + mac + "/" + "ssid", payloadobj[mac]["ssid"], qos=1) # no unit

    # TODO: use HA hierarchy (device + sensors + config for auto discovery)

def on_connect(client, userdata, flags, rc, properties):
    print("Connected with result code " + str(rc))

class Server(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        
    def do_HEAD(self):
        self._set_headers()
        
    # GET sends prometheus data
    def do_GET(self):
        global config
        global mqttc
        self._set_headers()
        #command = ['iw', 'wlan0 scan | egrep -i '^BSS|SSID:|signal:|freq:'']
        command = ["iw", "wlan0", "scan"]
        result = subprocess.run(command, capture_output=True, text=True)
        ifscan = result.stdout
        parsed = parseiwscan(ifscan)

        #MQTT
        push2mqtt(mqttc, config['topic'], filterSSIDjson(parsed, config['ssids']))

        #PROMETHEUS
        metrics = json2prom(parsed)
        #print(result.returncode, result.stdout, result.stderr)
        self.wfile.write(metrics.encode("utf-8"))
        
    # POST echoes the message adding a JSON field
    def do_POST(self):
        self._set_headers()
        test = "please use HTTP GET"
        self.wfile.write(test.encode("utf-8"))
        
def run(server_class=HTTPServer, handler_class=Server, port=5024): # TODO: put the port in the main config so it can be managed from container config
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    
    print('Starting MQTT loop')
    global config
    global mqttc
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqttc.username_pw_set(config['mqtt_user'], config['mqtt_pwd'])
    mqttc.connect(config['mqtt_host'], config['mqtt_port'])
    mqttc.loop_start()

    print('Starting httpd on port %d...' % port)
    httpd.serve_forever()

    mqttc.disconnect()
    mqttc.loop_stop()
    
if __name__ == "__main__":
    from sys import argv
    
    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
        