import ctypes
#import numpy as np
from picosdk.ps5000a import ps5000a as ps
from picosdk.functions import adc2mV, assert_pico_ok, mV2adc

from time import sleep, time

class Pico5000Controller:
    def __init__(self):
        # Create chandle and status ready for use
        self.chandle = ctypes.c_int16() # Make a 16 bit number which will be used to recognize the device
        #self.channels = {}
        self.status = {}

    def setup_device(self, resolution):
        # Open 5000 series PicoScope
        # Returns handle to chandle for use in future API functions
        device_resolution = ps.PS5000A_DEVICE_RESOLUTION[resolution]
        self.status["openunit"] = ps.ps5000aOpenUnit(ctypes.byref(self.chandle), None, device_resolution)
        try:
            assert_pico_ok(self.status["openunit"]) # Check if the openstatus is ok (=0)
        except: # PicoNotOkError:
            self.change_powersupply(self.status["openunit"])
        #assert_pico_ok(self.status["maximumValue"])
        # find maximum ADC count value
        # handle = self.chandle
        # pointer to value = ctypes.byref(maxADC)
        self.maxADC = ctypes.c_int16()
        #self.status["maximumValue"] = ps.ps5000aMaximumValue(self.chandle, ctypes.byref(self.maxADC))

    def change_powersupply(self, state):
        if state == 286:  # USB3_0_DEVICE_NON_USB3_0_PORT (Does this work?)
            self.status["changePowerSource"] = ps.ps5000aChangePowerSource(self.chandle, state)  # Change powersource to USB2
        elif state == 282:  # POWER_SUPPLY_NOT_CONNECTED
            self.status["changePowerSource"] = ps.ps5000aChangePowerSource(self.chandle, state)  # Change powersource to USB3
        else:
            self.status["changePowerSource"] = state
        assert_pico_ok(self.status["changePowerSource"])  # Check whether the powerchange was successful

    def set_resolution(self, resolution): # Change resolution
        device_resolution = ps.PS5000A_DEVICE_RESOLUTION[resolution]
        self.status["setResolution"] = ps.ps5000aSetDeviceResolution(self.chandle, device_resolution)
        self.status["maximumValue"] = ps.ps5000aMaximumValue(self.chandle, ctypes.byref(self.maxADC))

    def setup_channel(self, channel, channelID, Active, CouplingType, Range):
        #self.channels[channel] = channel_info
        self.status["setCh{}".format(channel)] = ps.ps5000aSetChannel(self.chandle, channelID, Active, CouplingType, Range, 0)

    def setup_trigger(self, Enable, channelID, LevelADC, Type, Delay, Auto):
        # Set up single trigger
        # handle = self.chandle
        # enabled = 1
        # direction = PS5000A_RISING = 2
        self.status["trigger"] = ps.ps5000aSetSimpleTrigger(self.chandle, Enable, channelID, LevelADC, Type, Delay, Auto)

    def set_timewindow(self, Samples, Timebase):
        # Get timebase information
        # handle = self.chandle
        # noSamples = maxSamples
        # pointer to timeIntervalNanoseconds = ctypes.byref(timeIntervalns)
        # pointer to maxSamples = ctypes.byref(returnedMaxSamples)
        # segment index = 0
        self.timeIntervalns = ctypes.c_float()
        returnedMaxSamples = ctypes.c_int32() # bits used to store data in this timebase?
        self.status["getTimebase2"] = ps.ps5000aGetTimebase2(self.chandle, Timebase, Samples, ctypes.byref(self.timeIntervalns), ctypes.byref(returnedMaxSamples), 0) # segmentIndex = 0, used for segmented memory

    def get_block(self, Samples, SamplesBeforeTrigger, Timebase):
        # Run block capture
        # handle = self.chandle
        # number of pre-trigger samples = preTriggerSamples
        # number of post-trigger samples = PostTriggerSamples
        # timebase = 8 = 80 ns (see Programmer's guide for mre information on timebases)
        # time indisposed ms = None (not needed in the example)
        # segment index = 0
        # lpReady = None (using ps5000aIsReady rather than ps5000aBlockReady)
        # pParameter = None
        '''
        starttime = time()
        self.status["runBlock"] = ps.ps5000aRunStreaming(self.chandle, ctypes.byref(ctypes.c_int32(100)), 2, SamplesBeforeTrigger, Samples-SamplesBeforeTrigger, 1, 0, 1, 0) #self.status["runBlock"] = ps.ps5000aRunBlock(self.chandle, SamplesBeforeTrigger, Samples-SamplesBeforeTrigger, Timebase, None, 0, None, None) # trigger['PreSamp'], trigger['PostSamp']
        print('Time to send a runblock command is: ', time() - starttime, ' s')
        self.status["isReady"] = ps.ps5000aGetStreamingLatestValues(self.chandle, ps.ps5000aStreamingReady(self.chandle, Samples, 0, ), ctypes.byref(ctypes.c_void_p())
        '''
        starttime = time()
        self.status["runBlock"] = ps.ps5000aRunBlock(self.chandle, SamplesBeforeTrigger, Samples-SamplesBeforeTrigger, Timebase, None, 0, None, None) # trigger['PreSamp'], trigger['PostSamp']
        print('Time to send a runblock command is: ', time() - starttime, ' s')
        # Check for data collection to finish using ps5000aIsReady
        ready = ctypes.c_int16(0)
        check = ctypes.c_int16(0)
        while ready.value == check.value:
            self.status["isReady"] = ps.ps5000aIsReady(self.chandle, ctypes.byref(ready))  # As soon as the sampling is done ready is set to 1
        print('Time to get a block of data is: ', time() - starttime, ' s')


    def set_buffer(self, channel, channelID, buffer, Samples):
        self.status["setDataBuffers{}".format(channel)] = ps.ps5000aSetDataBuffers(self.chandle, channelID, ctypes.byref(buffer['Max']), ctypes.byref(buffer['Min']), Samples, 0, 0)

    def read_data(self, cmaxSamples, overflow):
        # Retried data from scope to buffers assigned above (at the computer)
        # handle = self.chandle
        # start index = 0
        # pointer to number of samples = ctypes.byref(cmaxSamples)
        # downsample ratio = 0
        # downsample ratio mode = PS5000A_RATIO_MODE_NONE
        # pointer to overflow = ctypes.byref(overflow))
        self.status["getValues"] = ps.ps5000aGetValues(self.chandle, 0, ctypes.byref(cmaxSamples), 0, 0, 0, ctypes.byref(overflow))

    def stop(self):
        # Stop the scope
        # handle = chandle
        self.status["stop"] = ps.ps5000aStop(self.chandle)
        assert_pico_ok(self.status["stop"])

    def close(self):
        # Close unit Disconnect the scope
        # handle = chandle
        self.status["close"]=ps.ps5000aCloseUnit(self.chandle)
        assert_pico_ok(self.status["close"])

    def print_status(self):
        # display status returns
        self.send_message(self.status)

    def send_message(self, message):
        print(message)


'''
if __name__ == '__main__':
    import matplotlib.pyplot as plt

    channels = {'A': {'Range': '20V', 'CouplingType': 'DC'}, 'B': {'Range': '2V', 'CouplingType': 'DC'}} # REMEMBER: milliV as MV
    trigger = {'Channel': 'A', 'PreSamp': 25, 'PostSamp': 25, 'Level': 200, 'Auto': 10, 'Delay': 0} # 'PreSamp': number of samples before, 'PostSamp': number of samples after, 'Level': ADC of level, 'Auto': time in microseconds, 'Delay': time after triggerevent before trigger in number of samples
    timebase = 8  # Timestepsize = 80 ns (see Programmer's guide for more information on timebases)
    pico = Pico5000Controller("PS5000A_DR_12BIT", channels, trigger, timebase)
    pico.setup_device()
    pico.set_buffer()
    pico.get_block()
    pico.read_data()
    # plot data from channel A and B
    plt.plot(pico.time, pico.adc2mVChAMax[:])
    plt.plot(pico.time, pico.adc2mVChBMax[:])
    plt.xlabel('Time (ns)')
    plt.ylabel('Voltage (mV)')
    plt.show()

    pico.stop()
    pico.close()
    pico.print_status()
'''
