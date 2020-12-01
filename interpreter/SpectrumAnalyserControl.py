# -*- coding: utf-8 -*-
"""
Created on Thu Nov 19 14:05:49 2020

@author: mmj350
"""

import socket   # for sockets
import sys  # for exit
import time # for sleep
import datetime
# import matplotlib.pyplot as plt
import numpy as np
import timeit

class spectrumAnalyserControl:
    def __init__(self):
        self.SocketConnect()
    
    def SocketConnect(self):
        remote_ip = "169.254.188.72"#"10.11.13.32"  # should match the instrument’s IP address
        port = 5024 # the port number of the instrument service
        try:
            #create an AF_INET, STREAM socket (TCP)
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print("created socket")
        except socket.error:
            print ('Failed to create socket.')
            sys.exit();
        try:
            #Connect to remote server
            print("try connecting")
            self.s.connect((remote_ip , port))
            print("connect")
            info = self.s.recv(4096)
            print (info)
        except socket.error:
            print ('failed to connect to ip ' + remote_ip)
    
    def sendCommand(self,cmd):
        reply = self.SocketQuery(self.s,str.encode(cmd))
        return reply
 
    def SocketQuery(self, Sock, cmd):
        try :
            #Send cmd string
            Sock.sendall(cmd)
    ##        print(cmd)
            time.sleep(0.001)
        except socket.error:
            #Send failed
            print ('Send failed')
            sys.exit()
        reply = Sock.recv(4096)
        return reply 
