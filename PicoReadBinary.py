import yaml
from picosdk.functions import adc2mV
from picosdk.ps5000a import ps5000a as ps
import struct
import numpy as np
import ctypes
from pint import UnitRegistry
ur = UnitRegistry()

def load_settings(metadatafile):
    #metadatafile = file.replace('binary', 'metadata').replace('bin', 'yml')
    f = open(metadatafile, 'r')
    metadata = yaml.load(f)
    f.close()
    for Name in metadata:
        for Project in metadata[Name]:
            Settings = metadata[Name][Project]
    return Settings, Name, Project

def time_ns(metadatafile):
    Settings = load_settings(metadatafile)[0]
    return np.linspace(0, (Settings['Time']['Samples']-1) * ur(str(Settings['Time']['Timestep']).replace(' ', '')).m_as('ns'), Settings['Time']['Samples'])

def block_mV(metadatafile, channel, blocknumber = False):
    channels = ['A', 'B', 'C', 'D']
    Settings = load_settings(metadatafile)[0]
    Active_channels = [i for i in channels if Settings['Channels'][i]['Active'] == 2]
    block = (ctypes.c_int16 * Settings['Time']['Samples'])()
    if blocknumber:
        datafile = metadatafile.replace('metadata.yml', 'binary_{}.bin'.format(blocknumber))
    else:
        datafile = metadatafile.replace('metadata.yml', 'binary.bin')
    if channel in Active_channels:
        f = open(datafile, 'br')
        #f.seek(2 * Settings['Time']['Samples'] * channels.index(channel), 0)
        #block = f.read(Settings['Time']['Samples'])
        channel_skip = int(2*Settings['Time']['Samples']*channels.index(channel))
        for i in range(Settings['Time']['Samples']):
            f.seek(channel_skip+2*i, 0)
            block[i] = int.from_bytes(f.read(2), byteorder='little', signed=True)#f.read(2)#int(2*Settings['Time']['Samples']))#int.from_bytes(f.read(2), byteorder='little', signed=True)
        f.close
        return adc2mV(block, ps.PS5000A_RANGE["PS5000A_{}".format(Settings['Channels'][channel]['Range'].replace(' ', '').replace('m', 'M'))], ctypes.c_int16(Settings['Time']['maxADC']))
    else:
        raise Exception('Channel {} not in {}, only {}'.format(channel, datafile, Active_channels))

def scan_V(metadatafile):
    Settings = load_settings(metadatafile)[0]
    scandatafile = metadatafile.replace('metadata', 'scan')
    f = open(scandatafile, 'r')
    scandata = yaml.load(f)
    f.close()
    return {'Window average difference': scandata[1], Settings['Analyse']['ScanLabel']: scandata[0]}

if __name__ == '__main__':
    import os
    import matplotlib.pyplot as plt
    file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'PicoscopeData', 'DefaultData_1553874800_6982172_metadata.yml')
    '''
    time = time_ns(file)
    channels = ['A', 'B', 'C', 'D']
    color = {'A': 'b', 'B': 'r', 'C': 'g', 'D': 'y'}
    for channel in channels:
        try:
            plt.plot(time, block_mV(file, channel), color[channel])
        except:
            pass
    plt.xlabel('Time (ns)')
    plt.ylabel('Voltage (mV)')
    plt.show()
    '''
    settings = load_settings(file)[0]
    scandata = scan_V(file)
    plt.plot(scandata[str(settings['Analyse']['ScanLabel'])], scandata['Window average difference'])
    plt.xlabel(str(settings['Analyse']['ScanLabel']))
    plt.ylabel('Window average difference (V)')
    plt.show()


