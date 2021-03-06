import yaml
from picosdk.functions import adc2mV
from picosdk.ps5000a import ps5000a as ps
import struct
import numpy as np
import ctypes
from pint import UnitRegistry
import warnings
ur = UnitRegistry()
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg

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

def block_mV(metadatafile, channel, measurementnumber = False, blocknumber = False):
    channels = ['A', 'B', 'C', 'D']
    Settings = load_settings(metadatafile)[0]
    Active_channels = [i for i in channels if Settings['Channels'][i]['Active'] == 2]
    block = (ctypes.c_int16 * Settings['Time']['Samples'])()
    print("join",os.path.join(metadatafile.replace('metadata.yml', 'scope')))
    print("split", os.path.split(metadatafile)[1].replace('_metadata.yml', '.bin'))
    print("join and split",os.path.join(metadatafile.replace('metadata.yml', 'scope'), os.path.split(metadatafile)[1].replace('_metadata.yml', '.bin')))
    print("goed", os.path.join(metadatafile).replace('_metadata.yml', '.bin'))#) #(metadatafile.replace('metadata.yml', 'scope'), os.path.split
    datafile = os.path.join(metadatafile.replace('metadata.yml', 'scope'), os.path.split(metadatafile)[1].replace('_metadata.yml', '.bin'))#os.path.join(metadatafile.replace('metadata.yml', 'scope'), os.path.split(metadatafile)[1].replace('_metadata.yml', '.bin'))
    if measurementnumber:
        datafile = datafile.replace('.bin', '_{}.bin'.format(measurementnumber))
    if blocknumber:
        datafile = datafile.replace('.bin', '_{}.bin'.format(blocknumber))
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
        raise KeyError('Channel {} not in {}, only {}'.format(channel, datafile, Active_channels))

def scan_V(metadatafile):
    Settings = load_settings(metadatafile)[0]
    scandatafile = metadatafile.replace('_metadata', '')
    f = open(scandatafile, 'r')
    scandata = yaml.load(f)
    f.close()
    return scandata

if __name__ == '__main__':
    import os
    import matplotlib.pyplot as plt

    
    app = QtGui.QApplication([])

    win = pg.GraphicsWindow(title="Basic plotting examples")
    win.resize(1000,500)
    win.setWindowTitle('pyqtgraph example: Plotting')

    p1 = win.addPlot(title="Basic array plotting")

    file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'PicoscopeData_4_channels', '2020-06-11', 'DataAbsorption_2020-06-11_scan_40_metadata.yml')

    time = time_ns(file)*1e-9
    channels = ['A', 'B', 'C', 'D']
    color = {'A': 'b', 'B': 'r', 'C': 'g', 'D': 'y'}
    for channel in channels:
        try:
            plt.plot(time, block_mV(file, channel, measurementnumber = 69, blocknumber = False), color[channel], label = channel)
            p1.plot(time,block_mV(file, channel, measurementnumber = 69, blocknumber = False),pen=color[channel], name=channel)
        except KeyError:
            pass
    p1.addLegend()
    p1.setLabel('bottom', "Time" , units='s')
    p1.setLabel('left', "Voltage", units='V')
    
##    plt.legend()
##    plt.xlabel('Time (ns)')
##    plt.ylabel('Voltage (mV)')
##    plt.show()

    if __name__ == '__main__':
        import sys
        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QApplication.instance().exec_()
##
##    # Plot calculator over scanvalue
##    settings = load_settings(file)[0]
##    scandata = scan_V(file)
##    for calculator in scandata:#settings['Analyse']['Calculators']:
##        if not str(calculator) in 'Scanvalue' and not str(calculator) in 'Scantime':
##            try:
##                plt.plot(scandata['Scanvalue'], scandata[calculator], color = tuple([x/255 for x in settings['Analyse']['Calculators'][calculator]['Colour']]), label = settings['Analyse']['Calculators'][calculator][ 'Name'])
##            except:
##                warnings.warn('No metadata saved for Calculator {}'.format(calculator))
##                plt.plot(scandata['Scanvalue'], scandata[calculator], label = 'Calculator {}'.format(calculator))
##    plt.legend()
##    plt.xlabel(str(settings['Analyse']['ScanLabel']))
##    plt.ylabel('Calculator (V)')
##    plt.show()
##
##    # Plot calculator over time
##    for calculator in scandata:#settings['Analyse']['Calculators']:
##        if not str(calculator) in 'Scanvalue' and not str(calculator) in 'Scantime':
##            try:
##                plt.plot(scandata['Scantime'], scandata[calculator], color = tuple([x/255 for x in settings['Analyse']['Calculators'][calculator]['Colour']]), label = settings['Analyse']['Calculators'][calculator][ 'Name'])
##            except:
##                warnings.warn('No metadata saved for Calculator {}'.format(calculator))
##                plt.plot(scandata['Scantime'], scandata[calculator], label = 'Calculator {}'.format(calculator))
##    plt.legend()
##    plt.xlabel(str(settings['Analyse']['ScanLabel']))
##    plt.ylabel('Time (s)')
##    plt.show()


