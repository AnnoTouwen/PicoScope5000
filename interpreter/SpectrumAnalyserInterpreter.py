# -*- coding: utf-8 -*-
"""
Created on Thu Nov 19 14:05:24 2020

@author: mmj350
"""
import socket   # for sockets
import sys  # for exit
import time # for sleep
import datetime
import matplotlib.pyplot as plt
import numpy as np
import timeit
import struct
from pint import UnitRegistry
ur = UnitRegistry()
from time import sleep
# from controller.DelayControl import SRSDG535Controller
from simple_pid import PID
from SpectrumAnalyserControl import spectrumAnalyserControl
# interpreter
class spectrumAnalyserInterpreter:

    # Start connection and control
    def __init__(self):
        self.start_control()

    def start_control(self):
        self.control = spectrumAnalyserControl()

    
    # Frequency settings
    def freqSpan(self, freq):
        return self.control.sendCommand(':FREQuency:SPAN '+str(freq)+' MHz')

    def startFreq(self, freq):
        return self.control.sendCommand(':FREQuency:STARt '+str(freq)+' MHz')
    
    def stopFreq(self, freq):
        return self.control.sendCommand(':FREQuency:STOP '+str(freq)+' MHz')


    # Amplitude settings
    def refLevel(self, level):
        return self.control.sendCommand(':DISPlay:WINDow:TRACe:Y:RLEVel '+str(level)+' DBM')

    def attenuator(self, attendB):
        return self.control.sendCommand(':POWer:ATTenuation '+str(attendB))
    
    def preAmp(self, OnOff):
        return self.control.sendCommand(':POWer:GAIN '+OnOff)#"OFF"

    def amplitudeUnits(self, amplUnits):
        return self.control.sendCommand(':UNIT:POWer '+amplUnits)#"DBM"

    def amplScaleType(self, scaleType):
        return self.control.sendCommand(':DISPlay:WINDow:TRACe:Y:SPACing '+scaleType)#"LOGarithmic"

    def scaleDiv(self, ScaledB):
        return self.control.sendCommand(':DISPlay:WINDow:TRACe:Y:PDIVision '+str(ScaledB)+' dB')

    def RFinputImpedance(self, Ohm):
        return self.control.sendCommand('CORRection:IMPedance '+Ohm)#"OHM50"


    # Bandwidth settings
    def resBandwidth(self, resolution, units):
        return self.control.sendCommand(':BWIDth '+str(resolution)+' '+units)#str(1), "MHz"

    def videoBandWidth(self, resolution, units): #set VBW = 0.1 RBW for noise reduction.
        return self.control.sendCommand(':BWIDth:VIDeo '+str(resolution)+' '+units)#str(1), "MHz"


    # Trace settings
    def traceMode(self, mode):
        return self.control.sendCommand(':TRAC1:MODE '+mode)#"AVERage","WRITe"

    def getTraceData(self):
        return self.control.sendCommand(':TRACe:DATA? 1')

    def traceDataFormat(self,dataFormat):
        return self.control.sendCommand(':FORMat '+dataFormat) #ASCii or REAL
    

    # Average settings
    def averageNumber(self, aveNumber):
        return self.control.sendCommand(':AVERage:TRACe1:COUNt '+str(aveNumber))#3

    def averageRestart(self):
        return self.control.sendCommand(':AVERage:TRAC1:CLEar')
    

    # Sweep settings
    def sweepTimeState(self, mode):
        return self.control.sendCommand(':SWEep:TIME:AUTO '+mode)#"ON"

    def sweepMode(self, mode):
        return self.control.sendCommand(':SWEep:MODE '+mode)#"AUTO"

    def sweepSpeed(self, setting):
        return self.control.sendCommand(':SWEep:SPEed '+setting)#"NORMal"


    # Trigger settings
    def triggerType(self, mode):
        return self.control.sendCommand(':TRIGger:SOURce '+mode)#"EXTernal"

    def triggerEdge(self, posNeg):
        return self.control.sendCommand(':TRIGger:RFBurst:SLOPe '+posNeg)#"POSitive"


    # Marker settings
    def markerOnOff(self, onOff):
        return self.control.sendCommand(':CALCulate:MARK1:STATe '+onOff)#"OFF"

    def markerAllOff(self):
        return self.control.sendCommand(':CALCulate:MARKer:AOFF')


    # Peak settings
    def peakSearchMode(self, minMax):
        return self.control.sendCommand(':CALCulate:MARKer:PEAK:SEARch:MODE '+minMax)#"MAXimum"

    def peakThreshold(self,threshold):
        return self.control.sendCommand(':CALCulate:MARKer:PEAK:THReshold '+str(threshold))#"-50"

    def peakExcursion(self,excursionLevel):
        return self.control.sendCommand(':CALCulate:MARKer:PEAK:EXCursion '+str(excursionLevel))#"10" 

    def peakTableOnOff(self,onOff):
        return self.control.sendCommand(':CALCulate:MARKer:PEAK:TABLe '+onOff)#"ON"

    # Set f repetition rate manually
    def setFrep(self, freq):
        self.f_rep = freq*1e6 #freq is in MHz, f_rep in Hz
        return "Frep set"
    
    
    #  Receive peak data
    def getPeakTableData(self):
        return self.control.sendCommand(':CALCulate:PEAK:TABLe?')   


    ####### Edit data
    def peakDataBytesToStr(self,peakListBytes):
        peakListStr = peakListBytes.decode('UTF-8')
        peakListSplit = peakListStr.split(';')
        return peakListSplit
    
    def get_peakList(self,freqTableL):
        freqL = []
        dBL = []
        for peakNum in range(len(freqTableL)):
##            print("peakNum",peakNum)
            try:
                peak = freqTableL[peakNum]
##                print("peak",peak)
                peakSplit = peak.split(',')
##                print("peakSplit[0]",peakSplit)
                try:
                    peakSplit[0] = peakSplit[0].replace(":","") #Sometimes the first frequency has a : in front of the number, which makes that float() not works. Like ":+249 MHz"
                except:
                    pass
##                print("2e peakSplit[0]",peakSplit[0])
                freq = float(peakSplit[0])# In Hz, not in MHz!*1e-6 #In MHz
##                print("freq",freq)
                dB = float(peakSplit[1])

                freqL.append(freq)
                dBL.append(dB)
            except:
                pass
        return freqL, dBL


    def sortPeakList(self,list_freq_dB):
        freqList = list_freq_dB[0]
        dBList = list_freq_dB[1]
        
        sortedFreqL = [x for _,x in sorted(zip(dBList,freqList),reverse = True)]
        sorteddBL = sorted(dBList,reverse = True)
        return sortedFreqL,sorteddBL

    def get_f_rep(self,freq_dB_sorted,f_rep_guess):
        try: 
            freqList = freq_dB_sorted[0]
            dBList = freq_dB_sorted[1]
            
            if freqList[0] < 1.01*f_rep_guess and freqList[0] > 0.99*f_rep_guess and dBList[0] >-20:
                f_rep = freqList[0]
                return f_rep
        except:
            pass
            

    def get_beat_freq(self,freq_dB_sorted,f_rep):

        # could be no frequencies detected, therefore try
        try: 
            freqList = freq_dB_sorted[0][1:] #take out f_rep
            dBList = freq_dB_sorted[1][1:]

            if len(freqList)>4: #take out possible noise peaks. More than 4 beat note frequencies is unlikely. Sometimes 2 frequencies are detected for a single beat note, therefore more than 2 is desired.
                freqList = freqList[:4] 
                dBList = dBList[:4]

            # If more than 2 peaks are detected for 2 beat notes, find lowest difference between f_rep
            # beat1+beat2 = 2 f_rep
            diffL = []
            beat1L = []
            beat2L = []
            for beat1 in freqList: # find difference
                for beat2 in freqList:
                    if beat1 == beat2: #leaf out comparision with itself
                        continue
                    if beat1 + beat2 < 2*0.995*f_rep or beat1 + beat2 > 2*1.005*f_rep: # leaf out a combination with possible noise. Else, if no beat note is detected, two noise peaks end up as the lowest error from f_rep, while they should not be sign at all
                        continue
                    diffFrep = abs( beat1+beat2-2*f_rep ) # Find difference. Should be as low as possible
                    diffL.append(diffFrep)
                    beat1L.append(beat1)
                    beat2L.append(beat2)
            indexMinDiff = diffL.index(min(diffL)) # select lowest
            beatNote1 = beat1L[indexMinDiff]
            beatNote2 = beat2L[indexMinDiff]
##            print("diffL",diffL)    
##            
##            print("beatNote1",beatNote1)
##            print("beatNote2",beatNote2)

            meanBeatNote = abs(beatNote1-beatNote2)/2 # detected frequency is difference of two beat notes
            return meanBeatNote
        except:
            pass

    def alwaysGetFreq(self):
        for trial in range(100): #try maximal 100 times to get a frequency, else return nan.
            try:
                peakListBytes = interpreter.getPeakTableData() #get raw peak data spectrum analyser

                # return single beat note frequency
                peakListSplit = interpreter.peakDataBytesToStr(peakListBytes)
                freq_dB_L = interpreter.get_peakList(peakListSplit)
                sorted_freq_dB_L = interpreter.sortPeakList(freq_dB_L)
##                f_rep_meas = interpreter.get_f_rep(sorted_freq_dB_L,249.2e6) #f_rep can be set manually more preciesly than measuring
                freq = interpreter.get_beat_freq(sorted_freq_dB_L,249.2e6)

                if isinstance(freq,float) == True: #freq can be a frequency or a failed return. 
                    return freq
                else:
                    continue
            except:
                continue
        return "nan"



    

    def traceBytesToData(self,traceData):
        traceStr = traceData.decode('UTF-8')
        print("traceStr",traceStr)
        traceStrSplit = traceStr.split(';')
##        print(traceStrSplit)
        j_List = []
        for i in traceStrSplit:
    ##        print("i",i)
    ##        print(i[0:10])
            try:
    ##            print("TRACE A",traceStrSplit)
##                i.replace("A","")
                kommaSplit = i.split(",")
                if len(kommaSplit)<10:
                    continue
                
    ##            print("split i , ",kommaSplit)
                j_List = []
                for j in kommaSplit:
                   
                    try:
                        j_List.append(float(j))
                    except:
                        pass
            except:
                pass

            ##            print("j_List",j_List)
    ##            print("len j_List",len(j_List))
        xfTrace = np.linspace(249.2/2,249.2+249.2/2,(len(j_List)+2))[1:-1]
    ##    print("xfTrace",xfTrace)
    ##            i.replace("Aa","")
    ##            print("clean i",i)
    ##    return peakListSplit
        plt.plot(xfTrace,j_List)
        plt.xlabel("Frequency (MHz)")
        plt.ylabel("Amplitude (dB)")
    ##    xfTrace = 
        plt.show()




if __name__ == '__main__':
    # make connection
    interpreter = spectrumAnalyserInterpreter()

    interpreter.peakExcursion(10)
    interpreter.peakTableOnOff("ON")

    # set frequency
    interpreter.startFreq(249.2/2)
    interpreter.stopFreq(249.2+249.2/2)

    # set amplitude
    interpreter.refLevel(-10)
    interpreter.attenuator(20)
    interpreter.preAmp("OFF")
    interpreter.amplitudeUnits("DBM") #hard copy
    interpreter.amplScaleType("LOGarithmic") #hard copy
    interpreter.scaleDiv(6)
    interpreter.RFinputImpedance("OHM50")

    # set bandwidth
    interpreter.resBandwidth(1, "MHz")
    interpreter.videoBandWidth(0.1, "MHz") #set VBW = 0.1 RBW for noise reduction. Test with beat notes

    # set trace
    interpreter.traceMode("WRITe")#

##    interpreter.averageNumber(3)

    # set sweep
    interpreter.sweepTimeState("ON")
    interpreter.sweepSpeed("NORMal")#ACCUracy
    interpreter.sweepMode("AUTO")

    # set trigger
    interpreter.triggerType("EXTernal") #options: free running: IMMediate, on the video signal: VIDeo, external: EXTernal
    interpreter.triggerEdge("POSitive")

    # turn marker off
    interpreter.markerAllOff()

    # set peak settings
    
    interpreter.peakSearchMode("MAXimum")
    interpreter.peakThreshold(-60)

    # set f repetition rate manually (and more precise than measuring)
    interpreter.setFrep(249.2)

    

    freqStop = 15 # MHz

    timeL = []
    freqL = []

    freqRealL = []
    freqRealL2 = []
    
    dfdtL = []
    try:
        freq0 = interpreter.alwaysGetFreq()*1e-6
    except:
        print("No clear beat note")
        
    t0 = timeit.default_timer()
    print("t0",t0)
    flip = 0
    flip2 = 0
    deltaF = 30
    dfdt = 0.1 #MHz/s
##    dt = 1 # sec
    direction = 1
    direction2 = -1
    t_flip = 1000#
    t_check_flip = t0

    f_rep = 249.2 #MHz
    
    waitFlipTime = 2/dfdt

    for i in range(300): #loop to simulate scan of picoscope
        try:
 
            Scantime = timeit.default_timer() #time of (frequency) measurement

            # set flip time
            if Scantime > t_check_flip: # check if scantime is high enough to consider new flip time
                
                if freq0 + deltaF >f_rep/2: #only valid if projected freq is beyond rep rate mirror
                    if Scantime < t0+waitFlipTime and direction == -1: # avoid flip at start scan if freq is close to mirror but moving away
                        print("no flip, continue down",Scantime)
                        pass
                    t_flip = Scantime + (f_rep/2-freq0)/deltaF/(dfdt) # project new flip time
                    t_check_flip = t_flip + waitFlipTime #avoid directly after flip new flip projection, so add wait time
                    print("t_flip",t_flip)
                    
                if freq0 - deltaF <0:
                    if Scantime < t0+waitFlipTime and direction == 1:
                        print("no flip, continue up",Scantime)
                        pass
                    t_flip = Scantime + freq0/deltaF/(dfdt)
                    t_check_flip = t_flip + waitFlipTime
                    print("t_flip",t_flip)
                    
##            print("i,tflip",i,t_flip)

            # if Scantime > flip time, flip beat note direction
            if Scantime > t_flip:
                if freq0>f_rep/2 - freqStop or freq0 < freqStop:
                    
                    direction *= -1
                    flip += 1
                    direction2 *= -1
                    flip2 += 1
                    print("t_flip,Scantime",t_flip,Scantime)
                    t_flip = Scantime+ waitFlipTime #avoid directly after flip new flip projection, so add wait time

            # measure frequency
            freq = interpreter.alwaysGetFreq()*1e-6

            # determine frequency continuing beyond f_rep. Two versions necessary, because direction f_beat independent on frequency scan direction
            if direction == 1:
                freqReal = freq + int(flip/2)*f_rep
            if direction == -1:
                freqReal = f_rep-freq + int(flip/2)*f_rep

            if direction2 == 1:
                freqReal2 = freq + int((flip2+2)/2)*f_rep
            if direction2 == -1:
                freqReal2 = f_rep-freq + int((flip2+1)/2)*f_rep

            # save data to list for plotting
            timeL.append(Scantime)
            freqL.append(freq)
            freqRealL.append(freqReal)
            freqRealL2.append(freqReal2)


            
                       

##            t = Scantime
            freq0 = freq

##        
        

            time.sleep(0.1)

        except:
            continue
    print("timeL",timeL)
    print(np.mean(np.diff(timeL)))
    plt.plot(timeL,freqL,'.')
##    plt.xlabel("time (s)")
##    plt.ylabel("peak frequency (MHz)")
##    plt.show()

    plt.plot(timeL,freqRealL,'.')
    plt.plot(timeL,freqRealL2,'.')
##    plt.plot(timeLsel[1:],dfdtL,'.')
    plt.xlabel("time (s)")
    plt.ylabel("peak frequency (MHz)")
    plt.show()
##    interpreter.traceDataFormat("ASCii")#REAL
##    time.sleep(1)
##    traceBytes = interpreter.getTraceData()
##    interpreter.traceBytesToData(traceBytes)

##traceStr = interpreter.peakDataBytesToStr(traceBytes)
##print(xtime,freq) 
##print("trace",traceStr)
####print(trace
##print(traceStr[0].split(','))
    


##    floatL = []
##    timeL = []
##    for n in range(100):
####        print("n",n)
##        xtime = timeit.default_timer()
##        freq_frep = interpreter.alwaysGetFreq()
##        freq = freq_frep[0]
##
##        timeL.append(xtime)
##        floatL.append(freq)
##
##
##        time.sleep(0.065)
##
##    print("len(floatL)",len(floatL))
##    print("timeL",timeL)
##
##    plt.plot(timeL,np.array(floatL)*1e-6,'.')
##    plt.xlabel("time (s)")
##    plt.ylabel("peak frequency (MHz)")
##    plt.show()



### test to measure dfdt

##            dt = xtime-t0
##        t0 = xtime
##        df = freq - freq0
##        freq0 = freq
##
##        dfdt = df/dt
##        
##
##        if freq > freqStop and freq < 124.6-freqStop:
##            timeLsel.append(xtime)
##            freqLsel.append(freq)
##            try:
##                dfdtMean = (freqLsel[-1]-freqLsel[0]) / (timeLsel[-1]-timeLsel[0] )
##                print("dfdtMean",dfdtMean)
##                dfdtL.append(dfdtMean)
##            except:
##                pass
##            
##        print(xtime,"freq",freq)
