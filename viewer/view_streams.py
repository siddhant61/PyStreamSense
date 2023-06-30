import logging
from pylsl import resolve_streams, StreamInlet
from multiprocessing import Process
# from viewer.plot_streams import plot_stream as I was running it locally. Might need a switch or sth. like this too
from plot_streams import plot_stream
from muselsl.constants import LSL_SCAN_TIMEOUT

class ViewStreams:
    def __init__(self):
        self.eeg_streams = []
        self.acc_streams = []
        self.bvp_streams = []
        self.gsr_streams = []
        self.eeg_stream_count = 0
        logging.basicConfig(format='%(asctime)s %(message)s')
        logging.info("Initiating Viewer Instance.")

    def find_streams(self, stream_type):
        streams = resolve_streams(LSL_SCAN_TIMEOUT)
        streams = [stream for stream in streams if stream.type() == stream_type]
        active_streams = []
        for stream in streams:
            inlet = StreamInlet(stream)
            sample = inlet.pull_sample(timeout=0.1)
            print(stream.name(),sample)
            if sample is not None:
                active_streams.append(stream)
        print(active_streams)
        return active_streams

    def start_viewing(self, choice):

        logging.basicConfig(format='%(asctime)s %(message)s')

        if choice == 1:
            stream_type = 'EEG'
        elif choice == 2:
            stream_type = 'ACC'
        elif choice == 3:
            stream_type = 'BVP'
        elif choice == 4:
            stream_type = 'GSR'
        else:
            print("Invalid choice.")
            return

        streams = self.find_streams(stream_type)
        if not streams:
            print(f"No {stream_type} streams found.")
            return

        processes = []

        for i, stream in enumerate(streams):
            print('Starting stream Nr. %d for %s' % (i, stream))
            p = Process(target=plot_stream, args=(stream_type,i))
            processes.append(p)
            p.start()


if __name__ == "__main__":
    viewer = ViewStreams()
    viewer.start_viewing(1)
