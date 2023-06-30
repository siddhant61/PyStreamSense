# -*- coding: utf-8 -*-
# vispy: gallery 2
# Copyright (c) 2015, Vispy Development Team.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.

"""
Multiple real-time digital signals with GLSL-based clipping.
"""

import math
import logging
import numpy as np
from pylsl import resolve_byprop, StreamInlet, resolve_streams
from seaborn import color_palette
from mne.filter import create_filter
from vispy import gloo, app, visuals
from scipy.signal import lfilter, lfilter_zi
from muselsl.constants import LSL_SCAN_TIMEOUT

VERT_SHADER = """
#version 120
// y coordinate of the position.
attribute float a_position;
// row, col, and time index.
attribute vec3 a_index;
varying vec3 v_index;
// 2D scaling factor (zooming).
uniform vec2 u_scale;
// Size of the table.
uniform vec2 u_size;
// Number of samples per signal.
uniform float u_n;
// Color.
attribute vec3 a_color;
varying vec4 v_color;
// Varying variables used for clipping in the fragment shader.
varying vec2 v_position;
varying vec4 v_ab;
void main() {
    float n_rows = u_size.x;
    float n_cols = u_size.y;
    // Compute the x coordinate from the time index.
    float x = -1 + 2*a_index.z / (u_n-1);
    vec2 position = vec2(x - (1 - 1 / u_scale.x), a_position);
    // Find the affine transformation for the subplots.
    vec2 a = vec2(1./n_cols, 1./n_rows)*.9;
    vec2 b = vec2(-1 + 2*(a_index.x+.5) / n_cols,
                    -1 + 2*(a_index.y+.5) / n_rows);
    // Apply the static subplot transformation + scaling.
    gl_Position = vec4(a*u_scale*position+b, 0.0, 1.0);
    v_color = vec4(a_color, 1.);
    v_index = a_index;
    // For clipping test in the fragment shader.
    v_position = gl_Position.xy;
    v_ab = vec4(a, b);
}
"""

FRAG_SHADER = """
#version 120
varying vec4 v_color;
varying vec3 v_index;
varying vec2 v_position;
varying vec4 v_ab;
void main() {
    gl_FragColor = v_color;
    // Discard the fragments between the signals (emulate glMultiDrawArrays).
    if ((fract(v_index.x) > 0.) || (fract(v_index.y) > 0.))
        discard;
    // Clipping test.
    vec2 test = abs((v_position.xy-v_ab.zw)/v_ab.xy);
    if ((test.x > 1))
        discard;
}
"""

def find_streams(stream_type):
    streams = resolve_streams(LSL_SCAN_TIMEOUT)
    streams = [stream for stream in streams if stream.type() == stream_type]
    active_streams = []
    for stream in streams:
        inlet = StreamInlet(stream)
        sample = inlet.pull_sample(timeout=0.0)
        if sample[0] is not None:
            active_streams.append(stream)
    return active_streams


def plot_stream(stream_type, n):
    IDENTIFIER = 'PLOT STREAM'
    streams = resolve_streams(LSL_SCAN_TIMEOUT)
    streams = [stream for stream in streams if stream.type() == stream_type]
    active_streams = []
    for stream in streams:
        inlet = StreamInlet(stream)
        sample = inlet.pull_sample(timeout=0.1)
        print(stream.name(), sample)
        if sample is not None:
            active_streams.append(stream)
    print(active_streams)
    streams = active_streams
    print(IDENTIFIER, streams)
    print(IDENTIFIER, n)

    # TODO: This looks like it might have helped in properly resolving the elements here, but nonetheless I am running
    #   into an issue, as unfortunately vispy throws me an error. But I believe the work can already be continued
    #   on Windows (and Linux can be fixed subsequently). Here's the stacktrace I get:
    #       MuseS - 4626
    #       _EEG([-971.19140625, -935.05859375, -970.703125, -928.7109375, 0.0], 1688139245.919858)
    #       [ < pylsl.pylsl.StreamInfo
    #       object
    #       at
    #       0x7f3df995f250 >]
    #       Starting
    #       stream
    #       Nr.
    #       0
    #       for < pylsl.pylsl.StreamInfo object at 0x7f3df995f250 >
    #       MuseS - 4626
    #       _EEG([-1000.0, -1000.0, -1000.0, 332.03125, 0.0], 1688139251.4507198)
    #       [ < pylsl.pylsl.StreamInfo
    #       object
    #       at
    #       0x7f3dcce64810 >]
    #       PLOT
    #       STREAM[ < pylsl.pylsl.StreamInfo
    #       object
    #       at
    #       0x7f3dcce64810 >]
    #       PLOT
    #       STREAM
    #       0
    #       Setting
    #       up
    #       band -
    #       pass
    #       filter
    #       from
    #       3 - 40
    #       Hz
    #       FIR
    #       filter
    #       parameters
    #       ---------------------
    #       Designing
    #       a
    #       one -
    #       pass, zero - phase, non - causal
    #       bandpass
    #       filter:
    #       - Windowed
    #       time - domain
    #       design(firwin)
    #       method
    #       - Hamming
    #       window
    #       with 0.0194 passband ripple and 53 dB stopband attenuation
    #       - Lower
    #       passband
    #       edge: 3.00
    #       - Lower
    #       transition
    #       bandwidth: 2.00
    #       Hz(-6
    #       dB
    #       cutoff
    #       frequency: 2.00
    #       Hz)
    #       - Upper
    #       passband
    #       edge: 40.00
    #       Hz
    #       - Upper
    #       transition
    #       bandwidth: 10.00
    #       Hz(-6
    #       dB
    #       cutoff
    #       frequency: 45.00
    #       Hz)
    #       - Filter
    #       length: 423
    #       samples(1.652
    #       s)
    #       WARNING: Traceback(most
    #       recent
    #       call
    #       last):
    #       File
    #       "/home/christoph/Desktop/Workflow/Work_2023/Thesis_Sid/Code/PyStreamSense/viewer/view_streams.py", line
    #       63, in < module >
    #       viewer.start_viewing(1)
    #   File
    #   "/home/christoph/Desktop/Workflow/Work_2023/Thesis_Sid/Code/PyStreamSense/viewer/view_streams.py", line
    #   58, in start_viewing
    #   p.start()
    #   File
    #   "/home/christoph/anaconda3/envs/learning_studies/lib/python3.11/multiprocessing/process.py", line
    #   121, in start
    #   self._popen = self._Popen(self)
    #   File
    #   "/home/christoph/anaconda3/envs/learning_studies/lib/python3.11/multiprocessing/context.py", line
    #   224, in _Popen
    #   return _default_context.get_context().Process._Popen(process_obj)
    #   File
    #   "/home/christoph/anaconda3/envs/learning_studies/lib/python3.11/multiprocessing/context.py", line
    #   281, in _Popen
    #   return Popen(process_obj)
    #   File
    #   "/home/christoph/anaconda3/envs/learning_studies/lib/python3.11/multiprocessing/popen_fork.py", line
    #   19, in __init__
    #   self._launch(process_obj)
    #   File
    #   "/home/christoph/anaconda3/envs/learning_studies/lib/python3.11/multiprocessing/popen_fork.py", line
    #   71, in _launch
    #   code = process_obj._bootstrap(parent_sentinel=child_r)
    #   File
    #   "/home/christoph/anaconda3/envs/learning_studies/lib/python3.11/multiprocessing/process.py", line
    #   314, in _bootstrap
    #   self.run()
    #   File
    #   "/home/christoph/anaconda3/envs/learning_studies/lib/python3.11/multiprocessing/process.py", line
    #   108, in run
    #   self._target(*self._args, **self._kwargs)
    #   File
    #   "/home/christoph/Desktop/Workflow/Work_2023/Thesis_Sid/Code/PyStreamSense/viewer/plot_streams.py", line
    #   110, in plot_stream
    #   app.run()
    #   File
    #   "/home/christoph/anaconda3/envs/learning_studies/lib/python3.11/site-packages/vispy/app/_default_app.py", line
    #   60, in run
    #   return default_app.run()
    #   File
    #   "/home/christoph/anaconda3/envs/learning_studies/lib/python3.11/site-packages/vispy/app/application.py", line
    #   160, in run
    #   return self._backend._vispy_run()
    #   File
    #   "/home/christoph/anaconda3/envs/learning_studies/lib/python3.11/site-packages/vispy/app/backends/_egl.py", line
    #   110, in _vispy_run
    #   self._vispy_process_events()
    #   File
    #   "/home/christoph/anaconda3/envs/learning_studies/lib/python3.11/site-packages/vispy/app/backends/_egl.py", line
    #   105, in _vispy_process_events
    #   win._on_draw()
    #   File
    #   "/home/christoph/anaconda3/envs/learning_studies/lib/python3.11/site-packages/vispy/app/backends/_egl.py", line
    #   242, in _on_draw
    #   self._vispy_canvas.events.draw(region=None)  # (0, 0, w, h))
    #   File
    #   "/home/christoph/anaconda3/envs/learning_studies/lib/python3.11/site-packages/vispy/util/event.py", line
    #   453, in __call__
    #   self._invoke_callback(cb, event)
    #   File
    #   "/home/christoph/anaconda3/envs/learning_studies/lib/python3.11/site-packages/vispy/util/event.py", line
    #   471, in _invoke_callback
    #   _handle_exception(self.ignore_callback_errors,
    #   << caught
    #   exception
    #   here: >>
    #   File
    #   "/home/christoph/anaconda3/envs/learning_studies/lib/python3.11/site-packages/vispy/util/event.py", line
    #   469, in _invoke_callback
    #   cb(event)
    #   File
    #   "/home/christoph/Desktop/Workflow/Work_2023/Thesis_Sid/Code/PyStreamSense/viewer/plot_streams.py", line
    #   284, in on_draw
    #   [t.draw()
    #   for t in self.names + self.quality]
    #   File "/home/christoph/Desktop/Workflow/Work_2023/Thesis_Sid/Code/PyStreamSense/viewer/plot_streams.py", line 284, in < listcomp >
    #   [t.draw() for t in self.names + self.quality]
    #   ^ ^ ^ ^ ^ ^ ^ ^
    #   File "/home/christoph/anaconda3/envs/learning_studies/lib/python3.11/site-packages/vispy/visuals/visual.py", line 442, in draw
    #   if self._prepare_draw(view=self) is False:
    #       ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^
    #   File
    #   "/home/christoph/anaconda3/envs/learning_studies/lib/python3.11/site-packages/vispy/visuals/text/text.py", line
    #   594, in _prepare_draw
    #   n_pix = (self._font_size / 72.) * transforms.dpi  # logical pix
    #   ~~~~~~~~~~~~~~~~~~~~~~ ^ ~~~~~~~~~~~~~~~~~
    #   TypeError: unsupported
    #   operand
    #   type(s)
    #   for *: 'float' and 'NoneType'

    if n < len(streams):
        stream = streams[n]
        inlet = StreamInlet(stream)
        name = stream.name()
        logging.info(f"Start acquiring data for stream '{name}'.")
        Canvas(inlet, name)
        app.run()
    else:
        logging.warning("Invalid stream index.")

class Canvas(app.Canvas):

    def __init__(self, lsl_inlet, name, scale=500, filt=True):

        app.Canvas.__init__(self, title=f'{name} - Use your wheel to zoom!',
                            keys='interactive')

        self.inlet = lsl_inlet
        info = self.inlet.info()
        description = info.desc()

        window = 10
        self.sfreq = info.nominal_srate()
        n_samples = int(self.sfreq * window)
        self.n_chans = info.channel_count()

        ch = description.child('channels').first_child()
        ch_names = [ch.child_value('label')]

        for i in range(self.n_chans):
            ch = ch.next_sibling()
            ch_names.append(ch.child_value('label'))

        # Number of cols and rows in the table.
        n_rows = self.n_chans
        n_cols = 1

        # Number of signals.
        m = n_rows * n_cols

        # Number of samples per signal.
        n = n_samples

        # Various signal amplitudes.
        amplitudes = np.zeros((m, n)).astype(np.float32)
        # gamma = np.ones((m, n)).astype(np.float32)
        # Generate the signals as a (m, n) array.
        y = amplitudes

        color = color_palette("RdBu_r", n_rows)

        color = np.repeat(color, n, axis=0).astype(np.float32)
        # Signal 2D index of each vertex (row and col) and x-index (sample index
        # within each signal).
        index = np.c_[np.repeat(np.repeat(np.arange(n_cols), n_rows), n),
                      np.repeat(np.tile(np.arange(n_rows), n_cols), n),
                      np.tile(np.arange(n), m)].astype(np.float32)

        self.program = gloo.Program(VERT_SHADER, FRAG_SHADER)
        self.program['a_position'] = y.reshape(-1, 1)
        self.program['a_color'] = color
        self.program['a_index'] = index
        self.program['u_scale'] = (1., 1.)
        self.program['u_size'] = (n_rows, n_cols)
        self.program['u_n'] = n

        # text
        self.font_size = 48.
        self.names = []
        self.quality = []
        for ii in range(self.n_chans):
            text = visuals.TextVisual(ch_names[ii], bold=True, color='white')
            self.names.append(text)
            text = visuals.TextVisual('', bold=True, color='white')
            self.quality.append(text)

        self.quality_colors = color_palette("RdYlGn", 11)[::-1]

        self.scale = scale
        self.n_samples = n_samples
        self.filt = filt
        self.af = [1.0]

        self.data_f = np.zeros((n_samples, self.n_chans))
        self.data = np.zeros((n_samples, self.n_chans))

        self.bf = create_filter(self.data_f.T, self.sfreq, 3, 40.,
                                method='fir')

        zi = lfilter_zi(self.bf, self.af)
        self.filt_state = np.tile(zi, (self.n_chans, 1)).transpose()

        self._timer = app.Timer('auto', connect=self.on_timer, start=True)
        gloo.set_viewport(0, 0, *self.physical_size)
        gloo.set_state(clear_color='black', blend=True,
                       blend_func=('src_alpha', 'one_minus_src_alpha'))

        self.show()

    def on_key_press(self, event):

        # toggle filtering
        if event.key.name == 'D':
            self.filt = not self.filt

        # increase time scale
        if event.key.name in ['+', '-']:
            if event.key.name == '+':
                dx = -0.05
            else:
                dx = 0.05
            scale_x, scale_y = self.program['u_scale']
            scale_x_new, scale_y_new = (scale_x * math.exp(1.0 * dx),
                                        scale_y * math.exp(0.0 * dx))
            self.program['u_scale'] = (
                max(1, scale_x_new), max(1, scale_y_new))
            self.update()

    def on_mouse_wheel(self, event):
        dx = np.sign(event.delta[1]) * .05
        scale_x, scale_y = self.program['u_scale']
        scale_x_new, scale_y_new = (scale_x * math.exp(0.0 * dx),
                                    scale_y * math.exp(2.0 * dx))
        self.program['u_scale'] = (max(1, scale_x_new), max(0.01, scale_y_new))
        self.update()

    def on_timer(self, event):
        """Add some data at the end of each signal (real-time signals)."""

        samples, timestamps = self.inlet.pull_chunk(timeout=0.0,
                                                    max_samples=100)
        if timestamps:
            samples = np.array(samples)[:, ::-1]

            self.data = np.vstack([self.data, samples])
            self.data = self.data[-self.n_samples:]
            filt_samples, self.filt_state = lfilter(self.bf, self.af, samples,
                                                    axis=0, zi=self.filt_state)
            self.data_f = np.vstack([self.data_f, filt_samples])
            self.data_f = self.data_f[-self.n_samples:]

            if self.filt:
                plot_data = self.data_f / self.scale
            elif not self.filt:
                plot_data = (self.data - self.data.mean(axis=0)) / self.scale

            sd = np.std(plot_data[-int(self.sfreq):],
                        axis=0)[::-1] * self.scale
            co = np.int32(np.tanh((sd - 30) / 15) * 5 + 5)
            for ii in range(self.n_chans):
                self.quality[ii].text = '%.2f' % (sd[ii])
                self.quality[ii].color = self.quality_colors[co[ii]]
                self.quality[ii].font_size = 12 + co[ii]

                self.names[ii].font_size = 12 + co[ii]
                self.names[ii].color = self.quality_colors[co[ii]]

            self.program['a_position'].set_data(
                plot_data.T.ravel().astype(np.float32))
            self.update()

    def on_resize(self, event):
        # Set canvas viewport and reconfigure visual transforms to match.
        vp = (0, 0, self.physical_size[0], self.physical_size[1])
        self.context.set_viewport(*vp)

        for ii, t in enumerate(self.names):
            t.transforms.configure(canvas=self, viewport=vp)
            t.pos = (self.size[0] * 0.025,
                     ((ii + 0.5) / self.n_chans) * self.size[1])

        for ii, t in enumerate(self.quality):
            t.transforms.configure(canvas=self, viewport=vp)
            t.pos = (self.size[0] * 0.975,
                     ((ii + 0.5) / self.n_chans) * self.size[1])

    def on_draw(self, event):
        gloo.clear()
        gloo.set_viewport(0, 0, *self.physical_size)
        self.program.draw('line_strip')
        [t.draw() for t in self.names + self.quality]


