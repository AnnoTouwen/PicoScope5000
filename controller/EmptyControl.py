import ctypes
import random
from picosdk.ps5000a import ps5000a as ps
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc

from time import sleep, time

class EmptyController:
    def __init__(self):
        self.status = {}
        self.chandle = ctypes.c_int16(12345)

    def setup_device(self, resolution):
        self.status["openunit"] = 12345
        self.maxADC = ctypes.c_int16(2**int(resolution.replace('PS5000A_DR_', '').replace('BIT', '')))

    def change_powersupply(self, state):
        self.status["changePowerSource"] = 0

    def set_resolution(self, resolution): # Change resolution
        self.status["setResolution"] = 0
        self.status["maximumValue"] = 0
        self.maxADC = ctypes.c_int16(2**int(resolution.replace('PS5000A_DR_', '').replace('BIT', '')))

    def setup_channel(self, channel, channelID, Active, CouplingType, Range):
        self.status["setCh{}".format(channel)] = 0

    def setup_trigger(self, Enable, channelID, LevelADC, Type, Delay, Auto):
        self.status["trigger"] = 0

    def set_timewindow(self, Samples, Timebase):
        self.status["getTimebase2"] = 0
        self.timeIntervalns = ctypes.c_float(12345)
        self.status["getTimebase2"] = 0

    def get_block(self, Samples, SamplesBeforeTrigger, Timebase):
        self.status["runBlock"] = 0
        self.status["isReady"] = 0
        data = (ctypes.c_int * Samples)()
        for i in range(Samples):
            data[i] = random.randint(0, 100)#int(self.maxADC))
        self.buffer['Max'] = data
        self.buffer['Min'] = data

    def set_buffer(self, channel, channelID, buffer, Samples):
        self.status["setDataBuffers{}".format(channel)] = 0
        self.buffer = buffer

    def read_data(self, cmaxSamples, overflow):
        self.status["getValues"] = 0

    def set_generator_voltage(self, offsetVoltage):
        self.status["setSigGenBuiltInV2"] = 0

    def stop(self):
        self.status["stop"] = 0

    def close(self):
        self.status["close"] = 0

    def print_status(self):
        pass

    def send_message(self, message):
        print(message)



if __name__ == '__main__':
    import matplotlib.pyplot as plt

    channels = {'A': {'Range': '20V', 'CouplingType': 'DC'}, 'B': {'Range': '2V', 'CouplingType': 'DC'}} # REMEMBER: milliV as MV
    trigger = {'Channel': 'A', 'PreSamp': 25, 'PostSamp': 975, 'Level': 200, 'Auto': 10, 'Delay': 0} # 'PreSamp': number of samples before, 'PostSamp': number of samples after, 'Level': ADC of level, 'Auto': time in microseconds, 'Delay': time after triggerevent before trigger in number of samples
    timebase = 8  # Timestepsize = 80 ns (see Programmer's guide for more information on timebases)
    Samples = trigger['PreSamp'] + trigger['PostSamp']
    buffer = ctypes.c_int16 * Samples
    overflow = ctypes.c_int16()
    cmaxSamples = ctypes.c_int32(Samples)

    pico = Pico5000Controller()
    pico.setup_device("PS5000A_DR_12BIT")
    pico.set_buffer('A', "PS5000A_CHANNEL_A", buffer, Samples)
    pico.get_block(Samples, trigger['PreSamp'], timebase)
    pico.read_data(cmaxSamples, overflow)
    # plot data from channel A and B
    plt.plot(pico.time, pico.adc2mVChAMax[:])
    plt.plot(pico.time, pico.adc2mVChBMax[:])
    plt.xlabel('Time (ns)')
    plt.ylabel('Voltage (mV)')
    plt.show()

    pico.stop()
    pico.close()
    pico.print_status()

