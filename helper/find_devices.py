import bluetooth
import muselsl
from pyempatica import EmpaticaClient, EmpaticaServerConnectError
import pywifi
import time
import serial.tools.list_ports


class FindDevices:
    @staticmethod
    # Function to find nearby muse devices via Muselsl bleak scanner
    def find_muse():
        muses = muselsl.list_muses()
        return muses

    @staticmethod
    # Function to find nearby E4 devices via PyEmpatica client
    def find_empatica():
        e4s = []
        try:
            client = EmpaticaClient()
            print("Connected to E4 Streaming Server...")
            client.list_connected_devices()
            time.sleep(1)
            if len(client.device_list) != 0:
                for i in client.device_list:
                    e4s.append(i.decode("utf-8"))
            else:
                print("Could not connect to Empatica E4:", client.device_list)
            client.close()

        except EmpaticaServerConnectError:
            print(
                "Failed to connect to server, check that the E4 Streaming Server is open and connected to the BLE dongle.")

        if not e4s:
            print("No E4 devices found.")
        return e4s

    @staticmethod
    # Function to find nearby bluetooth devices
    def scan_bluetooth():
        devices = []
        nearby_devices = bluetooth.discover_devices(lookup_names=True)
        for addr, name in nearby_devices:
            devices.append({'name': name, 'address': addr, 'type': 'Bluetooth'})
        return devices

    @staticmethod
    # Function to find nearby wifi devices
    def scan_wifi():
        devices = []
        wifi = pywifi.PyWiFi()
        iface = wifi.interfaces()[0]
        iface.scan()
        time.sleep(1)
        results = iface.scan_results()
        for i in results:
            bssid = i.bssid
            ssid = i.ssid
            devices.append({'name': f'{ssid}', 'address': f'{bssid}', 'type': 'WiFi'})
        return devices

    @staticmethod
    # Function to find available Bluegiga BLED112 ports
    def serial_ports():
        bled_ports = []
        ports = serial.tools.list_ports.comports()
        for port, desc, hwid in sorted(ports):
            if "Bluegiga Bluetooth Low Energy" in desc:
                bled_ports.append(port)
        return bled_ports




