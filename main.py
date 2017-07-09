#!/usr/bin/env python
import os
import sys
import time
import traceback
import random
import netifaces
import ConfigParser
from daemonize import Daemonize
from subprocess import Popen, PIPE

import thingworx

HOME_DIR = os.path.dirname(os.path.abspath(__file__)) 
BIN_PATH = os.path.join(HOME_DIR, 'bin')
PID_FILE = '/tmp/thingworx.pid' 


def network_ready(interface):
    addr = netifaces.ifaddresses(interface)
    return netifaces.AF_INET in addr


def get_unique_id(interface):
    addrs = netifaces.ifaddresses(interface)
    mac = addrs[netifaces.AF_LINK][0]['addr']
    return 'DEVICE_' + mac.replace(':', '-')


def get_data():
    command = os.path.join(BIN_PATH, 'getBME')
    if not os.path.exists(command):
        temp = 37.0 + (random.random() - 0.5)
        pres = 101325 + random.randrange(-100, 100)
        humid = 37.0 + (random.random() - 0.5)
    else:
        # getBME returns value in this format
        # 37.79C
        # 100990Pa
        # 36.65%
        proc = Popen(command, stdout=PIPE)
        lines = proc.stdout.readlines()
        proc.stdout.close()
        temp = float(lines[0].rstrip('\r\nC'))
        pres = float(lines[1].lstrip(' ').rstrip('\r\nPa'))
        humid = float(lines[2].rstrip('\r\n%'))

    return (temp, pres, humid)


def upload_data(thing):
    (temp, pres, humid) = get_data()
    thing.add_property_value('temperature', temp)
    thing.add_property_value('pressure', pres)
    thing.add_property_value('humidity', humid)


def main():
    random.seed()

    config = ConfigParser.ConfigParser()
    config.read(os.path.join(HOME_DIR, 'settings.ini'))

    app_key = config.get('thingworx', 'app_key')
    server = config.get('thingworx', 'server')
    interface = config.get('network', 'interface')

    unique_id = get_unique_id(interface)
    print app_key, server, interface, unique_id

    thing = thingworx.Thing(server, app_key, unique_id)

    while True:
        if not network_ready(interface):
            time.sleep(1)
            continue

        try:
            if not thing.get_thing():
                thing.register_thing()
            while True:
                upload_data(thing)
                time.sleep(1)
        except Exception, e:
            print traceback.format_exc()


if __name__ == '__main__':
    daemon = Daemonize(app="thingworx", pid=PID_FILE, action=main)
    daemon.start()

