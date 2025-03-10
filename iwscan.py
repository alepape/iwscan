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

print("Config loaded - checking " + config['ssids'][0] + " for:")

#measures = '[{"measure":"freq","icon":"mdi:sine-wave","unit":"MHz"},{"measure":"channel","icon":"mdi:radio-tower","unit":null},{"measure":"signal","icon":"mdi:signal-cellular-2","unit":"dB"},{"measure":"ssid","icon":"mdi:wifi","unit":null}]' # TODO: put me in docker ENV config
measures = '[{"measure":"freq","icon":"mdi:sine-wave","unit":"MHz"},{"measure":"channel","icon":"mdi:radio-tower","unit":null},{"measure":"signal","icon":"mdi:signal-cellular-2","unit":"dB"}]' # TODO: put me in docker ENV config
config["measures"] = json.loads(measures)
for mes in config["measures"]:
    print(mes["measure"])

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

# TODO: send config @ frequency??? => upon start, w/ retain flag

def config2mqtt(client, topic, payloadobj, config, _has_run=[]):
    if _has_run: return
    _has_run.append(1) # runs only once

    print("sending config:")
    measures = config["measures"]
    print(json.dumps(measures))

    for mac in payloadobj:
        macStr = mac.replace(":", "")
        root = topic + "_" + macStr + "/"
        device = {}
        device["identifiers"] = "iwscan-ssids-" + payloadobj[mac]["ssid"]
        device["manufacturer"] = "ALP"
        device["model"] = "ALP iwscan"
        device["name"] = payloadobj[mac]["ssid"] # or "ssids" ??
        for mes in measures:
            config = {}
            # config["availability_topic"] = root + "availability"
            config["icon"] = mes["icon"]
            config["unique_id"] = macStr + "_" + mes["measure"]
            config["device"] = device
            if mes["unit"] is not None:
                config["unit_of_measurement"] = mes["unit"]
            config["name"] = mac + " " + mes["measure"]
            config["state_topic"] = root + mes["measure"] + "/state"

            jsonStr = json.dumps(config)
            # retain: bool = False
            client.publish(root + mes["measure"] + "/config", jsonStr, qos=1, retain=True)

def push2mqtt(client, topic, payloadobj, config):
    measures = config["measures"]
    for mac in payloadobj:
        macStr = mac.replace(":", "")
        for mes in measures:
            client.publish(topic + "_" + macStr + "/" + mes["measure"] + "/state", payloadobj[mac][mes["measure"]], qos=1)

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
        payloadSrc = filterSSIDjson(parsed, config['ssids'])
        config2mqtt(mqttc, config['topic'], payloadSrc, config) # should only happen once
        push2mqtt(mqttc, config['topic'], payloadSrc, config)

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
        