import csv
import logging
import time
import userpaths
import threading
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta
from pylsl import resolve_streams, StreamInlet


class SaveData:
    def __init__(self):
        self.output_files = {}
        self.stream_inlets = {}
        self.timestamps = {}
        self.connected = {}
        self.streams = {}
        self.sync_timestamp = None
        self.output_folder = userpaths.get_my_documents().replace("\\", "/") + \
                             f"/Data_Recordings/{str(datetime.today().timestamp()).replace('.', '_')}"
        self.output_folder_path = Path(self.output_folder)
        self.output_folder_path.mkdir(parents=True, exist_ok=True)
        self.stream_update_interval = 2.0
        self.stream_update_thread = threading.Thread(target=self.update_streams)
        logging.basicConfig(format='%(asctime)s %(message)s')


    def save_to_csv(self, stream_id, data, timestamp):
        timestamp_str = timestamp.isoformat()
        with open(self.output_files[stream_id], 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp_str] + data)


    def check_streams(self):
        all_streams = resolve_streams()
        stream_ids = {}
        result = {}
        streams = {}

        for stream in all_streams:
            key = stream.created_at()
            value = stream.name()
            stream_ids[key] = value

        # Create a Counter from the dictionary values
        counts = Counter(stream_ids.values())

        # Create a new dictionary with only the keys whose value has a count greater than 1
        duplicates = {k: v for k, v in stream_ids.items() if counts[v] > 1}

        # Keep values which were created later to access the latest stream
        for key, value in duplicates.items():
            if value not in result or key > result[value]:
                result[value] = key

        result = {v: k for k, v in result.items()}

        # Remove older duplicate streams from the dictionary
        for stream in all_streams:
            if not stream.name() in duplicates.values():
                key = stream.created_at()
                value = stream.name()
                result[key] = value

        # Save latest stream names and objects in the streams dictionary
        for stream in all_streams:
            if stream.created_at() in result.keys():
                streams[stream.name()] = stream

        return streams


    def update_streams(self):
        while True:
            self.streams = self.check_streams()
            time.sleep(self.stream_update_interval)


    def record_streams(self):

        self.stream_update_thread.start()

        self.streams = self.check_streams()

        miss_count = {}

        for stream_id, stream in self.streams.items():
            inlet = StreamInlet(stream)
            self.stream_inlets[stream_id] = inlet
            self.connected[stream_id] = True
            print(f"Stream Connected: {stream_id}")
            logging.info(f"Stream Connected: {stream_id}")
            output_file = f"{self.output_folder}/{stream_id}.csv"
            self.output_files[stream_id] = output_file
            miss_count[stream_id] = 0

        #mainloop_starts = time.time()
        while True:
            #now = time.time()
            #elapsed_time = now - mainloop_starts #to find out the time taken by each iteration of the loop (T = 0.13s)

            disconnected_streams = []

            for stream_id, inlet in self.stream_inlets.items():
                sample = inlet.pull_sample(timeout=0.0)
                if sample[0] is None:
                    miss_count[stream_id] = miss_count.get(stream_id) + 1
                else:
                    miss_count[stream_id] = 0

                # If there are more than 2 missing samples then the stream is disconnected.
                # SR = 256, each iteration should receive 256*0.13=33 samples.
                if "EEG" in stream_id:
                    if miss_count.get(stream_id) > 2:
                        if self.connected[stream_id]:
                            logging.info(f"Stream disconnected: {stream_id}")
                        disconnected_streams.append(stream_id)
                        self.connected[stream_id] = False

                # If there are more than 10 missing samples then the stream is disconnected.
                # SR = 64, each iteration should receive 64*0.13=8 samples.
                elif "BVP" in stream_id:
                    if miss_count.get(stream_id) > 10:
                        if self.connected[stream_id]:
                            logging.info(f"Stream disconnected: {stream_id}")
                        disconnected_streams.append(stream_id)
                        self.connected[stream_id] = False

                # If there are more than 20 missing samples then the stream is disconnected
                # SR = 32, each iteration should receive 32*0.13=4 samples.
                elif "ACC" in stream_id:
                    if miss_count.get(stream_id) > 20:
                        if self.connected[stream_id]:
                            logging.info(f"Stream disconnected: {stream_id}")
                        disconnected_streams.append(stream_id)
                        self.connected[stream_id] = False

                # If there are more than 30 missing samples then the stream is disconnected
                # SR = 4, each iteration should receive 4*0.13= 0.5 samples or 1 sample every 2 iterations.
                elif "GSR" in stream_id:
                    if miss_count.get(stream_id) > 40:
                        if self.connected[stream_id]:
                            logging.info(f"Stream disconnected: {stream_id}")
                        disconnected_streams.append(stream_id)
                        self.connected[stream_id] = False

                # If there are more than 30 missing samples then the stream is disconnected
                # SR = 4, each iteration should receive 4*0.13= 0.5 samples or 1 sample every 2 iterations.
                elif "TEMP" in stream_id:
                    if miss_count.get(stream_id) > 40:
                        if self.connected[stream_id]:
                            logging.info(f"Stream disconnected: {stream_id}")
                        disconnected_streams.append(stream_id)
                        self.connected[stream_id] = False

            for stream_id, inlet in self.stream_inlets.items():
                if self.connected[stream_id]:
                    samples, sample_timestamps = inlet.pull_chunk(timeout=0.0)
                    if samples:
                        sample_rate = inlet.info().nominal_srate()
                        time_delta = 1.0 / sample_rate
                        for sample, sample_timestamp in zip(samples, sample_timestamps):
                            if sample_timestamp > self.timestamps.get(stream_id, 0.0):
                                self.timestamps[stream_id] = sample_timestamp
                                if self.sync_timestamp is None or sample_timestamp < self.sync_timestamp:
                                    self.sync_timestamp = sample_timestamp
                                timestamp = datetime.now() + timedelta(seconds=sample_timestamp - self.sync_timestamp)
                                self.save_to_csv(stream_id, sample, timestamp)
                else:
                    if stream_id not in self.timestamps:
                        self.timestamps[stream_id] = self.sync_timestamp
                    timestamp = datetime.now() + timedelta(seconds=self.timestamps[stream_id] - self.sync_timestamp)
                    self.save_to_csv(stream_id, ['NA'] * inlet.info().channel_count(), timestamp)

            for stream_id in disconnected_streams:
                if stream_id in self.stream_inlets and stream_id in self.streams:
                    logging.info(f"Stream reconnected: {stream_id}")
                    self.stream_inlets[stream_id] = StreamInlet(self.streams[stream_id])
                    self.connected[stream_id] = True
                    miss_count[stream_id] = 0

            time.sleep(0.1)

if __name__ == "__main__":
    data_recorder = SaveData()
    data_recorder.record_streams()
