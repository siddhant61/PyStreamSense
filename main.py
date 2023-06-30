import argparse
import os
from datetime import datetime
from pathlib import Path
import muselsl
import threading
import time
import userpaths
import serial
# import wmi TODO: does not work under linux, so we need a switch here for checking OS and importing based on this
import logging
from recorder.save_data import SaveData
from helper.find_devices import FindDevices
from streamer.stream_muse import StreamMuse
from streamer.stream_e4 import StreamE4
from viewer.view_streams import ViewStreams


def main():

    log_path = userpaths.get_my_documents().replace("\\", "/") + f"/Data_Logs"
    output_folder_path = Path(log_path)
    output_folder_path.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=f"{log_path}/{str(datetime.today().timestamp()).replace('.', '_')}.log", level=logging.INFO, force=True)
    logging.basicConfig(format='%(asctime)s %(message)s')

    while True:
        print("The following options are available:\n")
        print("(1) Connect and stream Muse devices.\n")
        print("(2) View all the active LSL Streams.\n")
        print("(3) Connect and stream  E4  devices.\n")
        print("(4) Start recording all the streams.\n")
        choice = input("Enter your choice: ")
        choice = int(choice)

        if choice == 1:
            muse_reg = {}
            adapters = {}
            muse_streamers = {}
            muse_threads = {}
            devices = FindDevices()
            com_ports = []

            for port in devices.serial_ports():
                try:
                    ser = serial.Serial(port)
                    if ser.isOpen():
                        com_ports.append(port)
                    ser.close()
                except serial.serialutil.SerialException:
                    print(f"{port} is not available.\n")

            print(f"{len(com_ports)} free serial port(s) detected.\n")

            if len(com_ports) != 0:
                muses = devices.find_muse()
                if len(com_ports) > len(muses):
                    n = len(muses)
                else:
                    n = len(com_ports)
                if len(muses) != 0:
                    for i in range(n):
                        key = muses[i]['name']
                        value = muses[i]['address']
                        muse_reg[key] = value
                    print(f"{len(muse_reg)} Muse device(s) registered\n")
                else:
                    print("No Muse devices found.\n")

                if len(muse_reg) != 0:
                    for i in range(len(muse_reg)):
                        key = f"muse_streamer_{i + 1}"
                        value = StreamMuse(list(muse_reg.keys())[i], list(muse_reg.values())[i], com_ports[i])
                        muse_streamers[key] = value

                        key = f"thread_{i + 1}"
                        value = threading.Thread(target=list(muse_streamers.values())[i].start_streaming)
                        muse_threads[key] = value

                    if len(muse_threads) != 0:
                        for i in range(len(muse_threads)):
                            list(muse_threads.values())[i].start()
                            time.sleep(10)
                        time.sleep(10)
                        print(f"{len(muse_threads)} Muse streaming thread(s) running\n")
                    else:
                        print("No Muse streaming threads running.\n")

        elif choice == 2:
            while True:
                print("The following options are available:\n")
                print("(1) View all the active EEG Streams.\n")
                print("(2) View all the active ACC Streams.\n")
                print("(3) View all the active BVP Streams.\n")
                print("(4) View all the active GSR Streams.\n")
                print("(5) Go back to the main menu.\n")
                view_choice = input("Enter your choice: ")
                view_choice = int(view_choice)

                if view_choice < 5 and view_choice > 0:
                    viewer = ViewStreams()
                    viewer.start_viewing(view_choice)
                elif view_choice == 5:
                    break
                else:
                    print("Invalid Input. Please choose within (1-5)\n")

        elif choice == 3:
            e4_reg = {}
            e4_streamers = {}
            e4_threads = {}
            devices = FindDevices()

            e4_server = False

            while not (e4_server):
                print('Checking for E4 Server Process.\n')
                f = wmi.WMI()

                flag = 0

                # Iterating through all the running processes
                for process in f.Win32_Process():
                    if "EmpaticaBLEServer.exe" == process.Name:
                        print("E4 Server is running. Finding Serial Ports.\n")
                        e4_server = True
                        flag = 1
                        break

                if flag == 0:
                    e4_server = False
                    print("E4 Server is not running. Please start the server first.\n")
                    time.sleep(10)

            e4s = devices.find_empatica()

            if len(e4s) != 0:
                for i in range(len(e4s)):
                    key = str(e4s[i])
                    value = str(e4s[i])
                    e4_reg[key] = value
            else:
                print("No E4 devices found")

            if len(e4_reg) != 0:
                for i in range(len(e4_reg)):
                    key = f"e4_streamer_{i + 1}"
                    value = StreamE4(list(e4_reg.values())[i])
                    e4_streamers[key] = value

                    key = f"thread_{i + 1}"
                    value = threading.Thread(target=list(e4_streamers.values())[i].start_streaming)
                    e4_threads[key] = value
                print(f"{len(e4_reg)} E4 device(s) registered\n")
            else:
                print("No E4 devices registered\n")

            if len(e4_threads) != 0:
                for i in range(len(e4_threads)):
                    list(e4_threads.values())[i].start()
                    time.sleep(5)
                time.sleep(10)
                print(f"{len(e4_threads)} E4 streaming thread(s) running\n")
            else:
                print("No E4 streaming threads running.\n")

        elif choice == 4:
            data_recorder = SaveData()
            data_recorder.record_streams()
        else:
            print("Invalid Input. Please choose within (1-5)\n")


if __name__ == '__main__':
    # parser = argparse.ArgumentParser(description='Command-line menu')
    # parser.add_argument('script', type=str, help='The script to run')
    # args = parser.parse_args()
    main()


