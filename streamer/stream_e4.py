import time
import pylsl
import socket
import logging
from multiprocessing import Process

# SELECT DATA TO STREAM
acc = True      # 3-axis acceleration
bvp = True      # Blood Volume Pulse
gsr = True      # Galvanic Skin Response (Electrodermal Activity)
tmp = True      # Temperature

class StreamE4():

    def __init__(self, e4):
        self.current_e4 = e4
        self.streaming = False
        self.connected = False
        self.serverAddress = '127.0.0.1'
        self.serverPort = 28000
        self.bufferSize = 4096



    def connect(self):
        global s
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)

        logging.info("Connecting to server")
        s.connect((self.serverAddress, self.serverPort))
        logging.info("Connected to server\n")

        logging.info("Devices available:")
        s.send("device_list\r\n".encode())
        response = s.recv(self.bufferSize)
        logging.info(response.decode("utf-8"))

        logging.info("Connecting to device")
        s.send(("device_connect " + self.current_e4 + "\r\n").encode())
        response = s.recv(self.bufferSize)
        print(response.decode("utf-8"))
        logging.info(response.decode("utf-8"))

        logging.info("Pausing data receiving")
        s.send("pause ON\r\n".encode())
        response = s.recv(self.bufferSize)
        logging.info(response.decode("utf-8"))

        self.connected = True


    def suscribe_to_data(self):
        if acc:
            logging.info("Suscribing to ACC")
            s.send(("device_subscribe " + 'acc' + " ON\r\n").encode())
            response = s.recv(self.bufferSize)
            logging.info(response.decode("utf-8"))
        if bvp:
            logging.info("Suscribing to BVP")
            s.send(("device_subscribe " + 'bvp' + " ON\r\n").encode())
            response = s.recv(self.bufferSize)
            logging.info(response.decode("utf-8"))
        if gsr:
            logging.info("Suscribing to GSR")
            s.send(("device_subscribe " + 'gsr' + " ON\r\n").encode())
            response = s.recv(self.bufferSize)
            logging.info(response.decode("utf-8"))
        if tmp:
            logging.info("Suscribing to Temp")
            s.send(("device_subscribe " + 'tmp' + " ON\r\n").encode())
            response = s.recv(self.bufferSize)
            logging.info(response.decode("utf-8"))

        logging.info("Resuming data receiving")
        s.send("pause OFF\r\n".encode())
        response = s.recv(self.bufferSize)
        logging.info(response.decode("utf-8"))


    def prepare_LSL_streaming(self):
        logging.info("Starting LSL streaming")
        if acc:
            infoACC = pylsl.StreamInfo(f'{self.current_e4}_ACC','ACC',3,32,'int32',f'ACC-empatica_e4_{self.current_e4}');
            global outletACC
            outletACC = pylsl.StreamOutlet(infoACC)
        if bvp:
            infoBVP = pylsl.StreamInfo(f'{self.current_e4}_BVP','BVP',1,64,'float32',f'BVP-empatica_e4_{self.current_e4}');
            global outletBVP
            outletBVP = pylsl.StreamOutlet(infoBVP)
        if gsr:
            infoGSR = pylsl.StreamInfo(f'{self.current_e4}_GSR','GSR',1,4,'float32',f'GSR-empatica_e4_{self.current_e4}');
            global outletGSR
            outletGSR = pylsl.StreamOutlet(infoGSR)
        if tmp:
            infoTemp = pylsl.StreamInfo(f'{self.current_e4}_TEMP','TEMP',1,4,'float32',f'TEMP-empatica_e4_{self.current_e4}');
            global outletTemp
            outletTemp = pylsl.StreamOutlet(infoTemp)


    def reconnect(self):
        logging.info("Reconnecting...")
        while not self.connected:
            try:
                self.connect()
            except:
                self.connected = False

        time.sleep(1)
        self.suscribe_to_data()
        time.sleep(1)
        self.stream()


    def stream(self):
        try:
            self.streaming = True
            logging.info("Streaming ACC BVP GSR TEMP...")
            while True:
                try:
                    response = s.recv(self.bufferSize).decode("utf-8")
                    if "connection lost to device" in response:
                        logging.info(response)
                        self.connected = False
                        self.reconnect()
                        break
                    samples = response.split("\n")
                    for i in range(len(samples)-1):
                        stream_type = samples[i].split()[0]
                        if stream_type == "E4_Acc":
                            timestamp = float(samples[i].split()[1].replace(',','.'))
                            data = [int(samples[i].split()[2].replace(',','.')), int(samples[i].split()[3].replace(',','.')), int(samples[i].split()[4].replace(',','.'))]
                            outletACC.push_sample(data, timestamp=timestamp)
                        if stream_type == "E4_Bvp":
                            timestamp = float(samples[i].split()[1].replace(',','.'))
                            data = float(samples[i].split()[2].replace(',','.'))
                            outletBVP.push_sample([data], timestamp=timestamp)
                        if stream_type == "E4_Gsr":
                            timestamp = float(samples[i].split()[1].replace(',','.'))
                            data = float(samples[i].split()[2].replace(',','.'))
                            outletGSR.push_sample([data], timestamp=timestamp)
                        if stream_type == "E4_Temperature":
                            timestamp = float(samples[i].split()[1].replace(',','.'))
                            data = float(samples[i].split()[2].replace(',','.'))
                            outletTemp.push_sample([data], timestamp=timestamp)
                    #time.sleep(1)
                except socket.timeout:
                    logging.info("Socket timeout")
                    self.connected = False
                    self.reconnect()
                    break
        except KeyboardInterrupt:
            logging.info("Disconnecting from device")
            s.send("device_disconnect\r\n".encode())
            self.connected = False
            s.close()


    def e4_streamer(self):
        self.connect()
        time.sleep(2)
        self.suscribe_to_data()
        time.sleep(1)
        self.prepare_LSL_streaming()
        time.sleep(1)
        self.stream()

    def start_streaming(self):
        logging.basicConfig(format='%(asctime)s %(message)s')
        process = Process(target=self.e4_streamer)
        process.start()


