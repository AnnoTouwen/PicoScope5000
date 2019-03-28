#import os
import yaml
import ctypes
from pint import UnitRegistry
import numpy as np
from time import sleep
from controller.PicoControl import Pico5000Controller
from picosdk.ps5000a import ps5000a as ps
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc
import PicoReadBinary as prb
import struct

ur = UnitRegistry()
PS5000A_CHANNEL_FLAGS = {'A': 1, 'B': 2, 'C': 4, 'D': 8}
class Pico5000Interpreter:
    def __init__(self):
        self.buffer = {}
        self.scandata = {}

    '''
    def load_settings(self, filename):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        users_file = os.path.join(base_dir, 'config', filename)
        f = open(users_file, 'r')
        self.user = yaml.load(f)['DEFAULT']['DEFAULT_PROJECT']
        f.close()
    
    def import_settings(self, settings):
        self.user = settings
    '''

    def start_device(self):
        self.dev = Pico5000Controller()

    def setup_device(self, resolution):
        self.dev.setup_device('PS5000A_DR_'+resolution)


    def set_resolution(self, Resolution):
        self.dev.set_resolution('PS5000A_DR_'+Resolution)
        assert_pico_ok(self.dev.status["setResolution"])
        assert_pico_ok(self.dev.status["maximumValue"])
        self.maxADC = self.dev.maxADC

    def calculate_timebase(self, NumberOfActiveChannels, Resolution, Samples, Blocklength):
        message = False
        if Resolution in ['8BIT', '14BIT', '15BIT']:
            Timebase = round(ur(Blocklength.replace(' ', '')).m_as('ns')/(Samples-1) / 8 + 2)
            Timestep = str(8*(Timebase-2))+' ns'
            if Timebase > 2**32-1:
                Timebase = 2**32-1
                message = 'Timestep set to maximum'
                Timestep = str(8 * (Timebase - 2)) + ' ns'
        else:
            Timebase = round(ur(Blocklength.replace(' ', '')).m_as('ns')/(Samples-1) / 16 + 3)
            Timestep = str(16 * (Timebase - 3)) + ' ns'
            if Timebase > 2**32-2:
                Timebase = 2**32-2
                message = 'Timestep set to maximum'
                Timestep = str(16 * (Timebase - 3)) + ' ns'
        if Timebase < 5:
            nsstep = round(ur(Blocklength.replace(' ', '')).m_as('ns') / (Samples-1))
            if Resolution in '8BIT':
                if nsstep < 2:
                    if NumberOfActiveChannels < 2:
                        Timebase = 0
                        message = 'Timestep set to minimum'
                        Timestep = '1 ns'
                    else:
                        Timebase = 1
                        message = 'Timestep set to minimum'
                        Timestep = '2 ns'
                elif nsstep < 3:
                    Timebase = 1
                    Timestep = '2 ns'
                elif nsstep < 6:
                    Timebase = 2
                    Timestep = '4 ns'
            if Resolution in '12BIT':
                if nsstep < 3:
                    if NumberOfActiveChannels < 2:
                        Timebase = 1
                        message = 'Timestep set to minimum'
                        Timestep = '2 ns'
                    else:
                        Timebase = 2
                        message = 'Timestep set to minimum'
                        Timestep = '4 ns'
                elif nsstep < 6:
                    Timebase = 2
                    Timestep = '4 ns'
            if Resolution in '14BIT':
                Timebase = 3
                message = 'Timestep set to minimum'
                Timestep = '8 ns'
            if Resolution in '15BIT':
                if NumberOfActiveChannels < 3:
                    Timebase = 3
                    message = 'Timestep set to minimum'
                    Timestep = '8 ns'
                else:
                    Timebase = 4
                    message = 'Timestep set to minimum'
                    Timestep = '16 ns'
            if Resolution in '16BIT':
                if NumberOfActiveChannels < 2:
                    Timebase = 4
                    message = 'Timestep set to minimum'
                    Timestep = '16 ns'
                else:
                    Timebase = 5
                    message = 'Timestep set to minimum'
                    Timestep = '32 ns'
        return (Timebase, Timestep, str(ur(Timestep.replace(' ', ''))*(Samples-1)), message)

    def setup_channel(self, channel, Active, CouplingType, Range):
        # Setup the channels
        '''
        self.user['Channels'][channel]['ID'] = ps.PS5000A_CHANNEL["PS5000A_CHANNEL_{}".format(channel)] # ID was channel
        self.user['Channels'][channel]['CT'] = ps.PS5000A_COUPLING["PS5000A_{}".format(self.user['Channels'][channel]['CouplingType'])] # CT was coupling_type
        self.user['Channels'][channel]['RG'] = ps.PS5000A_RANGE["PS5000A_{}".format(self.user['Channels'][channel]['Range'].replace(' ', '').replace('m', 'M'))] # RG was ch<label channel>Range
        '''
        self.dev.setup_channel(channel, ps.PS5000A_CHANNEL["PS5000A_CHANNEL_{}".format(channel)], int(Active/2), ps.PS5000A_COUPLING["PS5000A_{}".format(CouplingType)], ps.PS5000A_RANGE["PS5000A_{}".format(Range.replace(' ', '').replace('m', 'M'))])
        assert_pico_ok(self.dev.status["setCh{}".format(channel)])

    def set_trigger(self, active, channel, Type, Level, Delay, Auto, Range = 0):
        if channel in 'External':
            LevelADC = int(mV2adc(ur(Level.replace(' ', '')).m_as('mV'), ps.PS5000A_RANGE["PS5000A_5V"], ctypes.c_int16(32767)))
            self.dev.setup_trigger(active, ps.PS5000A_CHANNEL["PS5000A_EXTERNAL"], LevelADC, ps.PS5000A_THRESHOLD_DIRECTION["PS5000A_{}".format(Type.upper())], Delay, int(ur(Auto.replace(' ', '')).m_as('ms')))
        else:
            LevelADC = int(mV2adc(ur(Level.replace(' ', '')).m_as('mV'), ps.PS5000A_RANGE["PS5000A_{}".format(Range.replace(' ', '').replace('m', 'M'))], self.dev.maxADC))
            self.dev.setup_trigger(active, ps.PS5000A_CHANNEL["PS5000A_CHANNEL_{}".format(channel)], LevelADC, ps.PS5000A_THRESHOLD_DIRECTION["PS5000A_{}".format(Type.upper())], Delay, int(ur(Auto.replace(' ', '')).m_as('ms')))
        assert_pico_ok(self.dev.status["trigger"])

    def set_timewindow(self, Samples, Timebase):
        # self.user['Trigger']['maxSamples'] = 50 # self.user['Trigger']['PreSamp'] + self.user['Trigger']['PostSamp']
        self.dev.set_timewindow(Samples, Timebase)
        assert_pico_ok(self.dev.status["getTimebase2"])

    def set_buffer(self, channel, Samples):
        # Create buffers ready for assigning pointers for data collection
        self.buffer[channel] = {}
        self.buffer[channel]['Max'] = (ctypes.c_int16 * Samples)()
        self.buffer[channel]['Min'] = (ctypes.c_int16 * Samples)()
        self.dev.set_buffer(channel, ps.PS5000A_CHANNEL["PS5000A_CHANNEL_{}".format(channel)], self.buffer[channel], Samples)
        assert_pico_ok(self.dev.status["setDataBuffers{}".format(channel)])

        # create overflow location
        self.overflow = ctypes.c_int16()
        # create converted type self.maxSamples
        self.cmaxSamples = ctypes.c_int32(Samples)

    def get_block(self, Samples, SamplesBeforeTrigger, Timebase):
        self.dev.get_block(Samples, SamplesBeforeTrigger, Timebase)
        assert_pico_ok(self.dev.status["runBlock"])

    def read_data(self):
        self.dev.read_data(self.cmaxSamples, self.overflow)
        assert_pico_ok(self.dev.status["getValues"])

    def save_binary(self, file, active_channels, Average = False):
        f = open(file, 'wb')
        for channel in active_channels:
            if Average:
                f.write(self.buffer[channel]['Average'])
            else:
                f.write(self.buffer[channel]['Max'])
        f.close()
    '''
    def Add_scanpoint(self, datafile, metadatafile, scanvalue, windowIstart, windowIlength, windowIchannel, windowIwindow, windowIIstart, windowIIlength, windowIIchannel, windowIIwindow, scandatanumber=False):
        f = open(metadatafile, 'r')
        metadata = yaml.load(f)
        f.close()
        for Name in metadata:
            for Project in metadata[Name]:
                Settings = metadata[Name][Project]
        windowstart = [windowIstart, windowIIstart]
        windowlength = [windowIlength, windowIIlength]
        windowchannel = [windowIchannel, windowIIchannel]
        windowwindow = [windowIwindow, windowIIwindow]
        channels = ['A', 'B', 'C', 'D']
        datachannels = [i for i in channels if Settings['Channels'][i]['Save'] == 2]
        windowdata = []
        windowdataaverage = []
        for window in range(2):
            windowdata.append((ctypes.c_int16 * windowlength[window])())
            if windowchannel[window] in datachannels:
                f = open(datafile, 'br')
                channel_skip = int(2 * Settings['Time']['Samples'] * channels.index(windowchannel[window])+windowstart[window])
                for i in range(windowlength[window]):
                    f.seek(channel_skip + 2 * i, 0)
                    windowdata[window][i] = int.from_bytes(f.read(2), byteorder='little', signed=True)
                f.close
            else:
                return 'Channel {} not in file, only {}'.format(windowchannel[window], datachannels)
            if windowwindow[window] in 'FWHM':
                return 'FWHM not yet available'
            windowdataaverage.append(0)
            for i in range(windowlength[window]):
                windowdataaverage[window] += windowdata[window][i]
            print(windowdataaverage[window])
            windowdataaverage[window] = windowdataaverage[window]/windowlength[window]*ur(Settings['Channels'][windowchannel[window]]['Range'].replace(' ', '')).m_as('mV')/int(Settings['Time']['maxADC'])
        if not scandatanumber:
            scandatanumber = 0
            while str(scandatanumber) in self.scandata:
                scandatanumber += 1
        self.scandata[str(scandatanumber)] = {'Scanvalue': scanvalue, 'Average_mV': windowdataaverage[0] - windowdataaverage[1], 'Binarydatafile': datafile}
        return int(scandatanumber)
    '''

    def reset_buffer_sum(self):
        for channel in self.buffer:
            try:
                del self.buffer[channel]['Sum']
            except KeyError:
                pass

    def add_to_buffer_sum(self):
        for channel in self.buffer:
            try:
                self.buffer[channel]['Sum'] = [self.buffer[channel]['Sum'][i] + self.buffer[channel]['Max'][i] for i in range(len(self.buffer[channel]['Max']))]
            except KeyError:
                self.buffer[channel]['Sum'] = [self.buffer[channel]['Max'][i] for i in range(len(self.buffer[channel]['Max']))]

    def block_average(self, Samples, numberofblocks):
        for channel in self.buffer:
            self.buffer[channel]['Average'] = (ctypes.c_int16 * Samples)()
            for i in range(Samples):
                self.buffer[channel]['Average'][i] = round(self.buffer[channel]['Sum'][i]/numberofblocks)

    def read_windows(self, start_window, stop_window, channel):
        self.windowAverage = [0, 0]
        for window in [0, 1]:
            samples_in_window = stop_window[window] - start_window[window] + 1
            for i in np.linspace(start_window[window]-1, stop_window[window]-1, samples_in_window):
                self.windowAverage[window] += self.buffer[channel[window]]['Average'][int(i)]
            self.windowAverage[window] = self.windowAverage[window]/samples_in_window

    def reset_scandata(self):
        self.scandata = [[], []]

    def compute_scanpoint(self, scanvalue, mode, range, maxADC):
        self.scandata[0].append(scanvalue)
        if mode in 'Window I - Window II':
            self.scandata[1].append(self.windowAverage[0]/maxADC*ur(range[0]).m_as('V')-self.windowAverage[1]/maxADC*ur(range[1]).m_as('V'))
        elif mode in 'Window II - Window I':
            self.scandata[1].append(self.windowAverage[1]/maxADC*ur(range[1]).m_as('V')-self.windowAverage[0]/maxADC*ur(range[0]).m_as('V'))

    def interpret_data(self, Samples, timestep, channel, Range, Average = True):
        # Create time data
        if not 'Time' in self.block:
            self.block['Time'] = np.linspace(0, Samples * timestep, Samples)
        # convert ADC counts data to mV
        if Average:
            self.block[channel] = adc2mV(self.buffer[channel]['Average'], ps.PS5000A_RANGE["PS5000A_{}".format(Range.replace(' ', '').replace('m', 'M'))], self.dev.maxADC)
        else:
            self.block[channel] = adc2mV(self.buffer[channel]['Max'], ps.PS5000A_RANGE["PS5000A_{}".format(Range.replace(' ', '').replace('m', 'M'))], self.dev.maxADC)

    '''
    def save_data(self, file, channels):
        print(file)
        f = open(file, 'w')
        line = 'Time (ns) '
        for i in channels:
            line += 'Channel {} (mV) '.format(i)
        line += '\n'
        f.write(line)
        for j in range(len(self.block['Time'])):
            line = '{}'.format(str(int(self.block['Time'][j])))
            for i in channels:
                line += ' {}'.format(str(self.block[i]['Average'][j]))
            line += '\n'
            f.write(line)

        
        line = '{}\n'.format(str(self.block['Time'][:]))
        f.write(line)
        for blocks in channels:
            line = '{}\n'.format(str(self.block[blocks]['Average'][:]))
            f.write(line)
        
        f.close()
    '''

    def send_message(self, message):
        print(message)

    def stop_device(self):
        self.dev.stop()

    def close_device(self):
        self.dev.close()

