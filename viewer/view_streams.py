import logging
from threading import Timer

from pylsl import resolve_streams, StreamInlet
from multiprocessing import Process
from collections import Counter
from viewer.plot_streams import plot_stream
from muselsl.constants import LSL_SCAN_TIMEOUT
from vispy import gloo, app, visuals

view_logger = logging.getLogger(__name__)

class ViewStreams:
    def __init__(self):
        self.eeg_streams = []
        self.acc_streams = []
        self.bvp_streams = []
        self.gsr_streams = []
        self.eeg_stream_count = 0

        view_logger.info("Initiating Viewer Instance.")

    # def find_streams(self, stream_type):
    #     streams = resolve_streams(LSL_SCAN_TIMEOUT)
    #     streams = [stream for stream in streams if stream.type() == stream_type]
    #     active_streams = []
    #     for stream in streams:
    #         inlet = StreamInlet(stream)
    #         sample = inlet.pull_chunk(timeout=0.0)
    #         print(stream.name(),sample)
    #         if sample is not None:
    #             active_streams.append(stream)
    #     print(active_streams)
    #     return active_streams

    def find_streams(self, stream_type):
        all_streams = resolve_streams(LSL_SCAN_TIMEOUT)
        all_streams = [stream for stream in all_streams if stream.type() == stream_type]
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

        return streams.values()

    def start_viewing(self, choice, duration=60):

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
            view_logger.info((f"No {stream_type} streams found."))
            return

        canvases = []  # list to hold all the Canvas objects

        for i, stream in enumerate(streams):
            canvas = plot_stream(stream_type, i)
            if canvas is not None:
                canvases.append(canvas)

        if canvases:
            def close_plots():  # Function to close the plots after a duration
                for canvas in canvases:
                    canvas.stop()  # Stop the timer in each canvas
                    canvas.close()  # Close each canvas

            t = Timer(duration, close_plots)  # Start a timer to close the plots
            t.start()

            app.run()  # run the app after all the Canvas objects have been created


if __name__ == "__main__":
    viewer = ViewStreams()
    viewer.start_viewing(1)
