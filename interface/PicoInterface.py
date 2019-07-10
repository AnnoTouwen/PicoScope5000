from PyQt5.QtWidgets import QMainWindow, QApplication, QColorDialog, QWidget, QLabel, QDialog, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout, QLabel
from PyQt5 import QtWidgets
from PyQt5 import uic
from PyQt5.QtCore import QTimer, pyqtSlot, Qt, QSize
from PyQt5.QtGui import QIcon
# from controller.picocontrol import Pico5000Controller
import threading
import time
import pyqtgraph as pg
import pyqtgraph.exporters
import os
import yaml
import random
from time import sleep, time
from datetime import date, datetime
from functools import partial
from pint import UnitRegistry
ur = UnitRegistry()
from interpreter.DelayInterpreter import SRSDG535Interpreter

class Pico5000Interface(QMainWindow):
    def __init__(self, interpreter):
        super(Pico5000Interface, self).__init__(parent=None)  # Adopt QMainWindow as parent
        self.base_folder = os.path.dirname(__file__)
        main_window_file = os.path.join(self.base_folder, 'main_window.ui')
        uic.loadUi(main_window_file, self)
        #self.tabWidget.setStyleSheet("QTabBar::tab::disabled {width: 0; height: 0; margin: 0; padding: 0; border: none;} ")

        self.itp = interpreter # Start interpreter

        self.setWindowTitle("Picoscope5000 MainWindow")
        self.setWindowIcon(QIcon(os.path.join(self.base_folder, 'icon.png')))

        # Shorter definition of buttons
        self.ChannelActive = {'A': self.AActive, 'B': self.BActive, 'C': self.CActive, 'D': self.DActive}
        self.ChannelRange = {'A': self.ARange, 'B': self.BRange, 'C': self.CRange, 'D': self.DRange}
        self.ChannelCoupling = {'A': self.ACoupling, 'B': self.BCoupling, 'C': self.CCoupling, 'D': self.DCoupling}
        self.ChannelName = {'A': self.AName, 'B': self.BName, 'C': self.CName, 'D': self.DName}

        # Delay generator parameters
        self.connectors = ['Ext', 'T0', 'A', 'B', 'AB', 'C', 'D', 'CD']
        self.primary_connectors = ['A', 'B', 'C', 'D']
        self.impedances = ['50 Ohm', 'HighZ']
        self.signalmodes = ['TTL', 'NIM', 'ECL', 'Variable']
        self.triggermodes = ['Internal', 'External', 'Single shot', 'Burst']
        self.Delay = {'A': self.Delay_A, 'B': self.Delay_B, 'C': self.Delay_C, 'D': self.Delay_D}
        #self.Difference = {'A': self.Delay_difference_A, 'B': self.Delay_difference_B, 'C': self.Delay_difference_C, 'D': self.Delay_difference_D}
        self.From = {'A': self.From_A, 'B': self.From_B, 'C': self.From_C, 'D': self.From_D}

        # Define initial parameters
        self.channel_changed = {}
        self.buffer_changed = {}
        self.first_timebase = True
        self.measurement_running = False
        self.measurement_pause = True
        self.continue_after_setting = True
        self.confirm_overwrite_personal = False
        self.channel_colour = {'A': 'b', 'B': 'r', 'C': 'g', 'D': 'y', 'External': 'k'}
        #self.colours = ['r', 'r', 'y', 'g', 'b', 'm']
        self.channels = ['A', 'B', 'C', 'D']
        #self.windows = ['I', 'II']
        f = open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'users.yml'), 'r')
        PreviousUser = yaml.safe_load(f)['PreviousUser']
        f.close()
        self.load_personal_settings(PreviousUser['Name'], PreviousUser['Project']) # Set settings to Default
        self.device_channels = 4
        self.two_channels()

        # Plotparameters and objects
        self.newData = False
        self.current_triggerlevel = pg.InfiniteLine(pos=ur(str(self.current_settings['Trigger']['Level']).replace(' ', '')).m_as('V'), angle=0, pen=pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']], style=Qt.DashLine, width=2), hoverPen=pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']], width=2), movable=True, name='current_triggerlevel')
        self.current_triggerposition = pg.InfiniteLine(pos=(self.current_settings['Trigger']['Position']+1) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'), angle=90, pen=pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']], style=Qt.DashLine, width=2), hoverPen=pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']], width=2), movable=True, name='current_triggerposition', bounds=[0, ur(str(self.current_settings['Time']['Blocklength']).replace(' ', '')).m_as('ns')])
        self.window_start_draw = {}
        self.window_finish_draw = {}
        for window in self.windows:
            self.window_start_draw[window] = pg.InfiniteLine(pos=(int(self.current_settings['Analyse']['Windows'][window]['Start'])) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'), angle=90, pen=pg.mkPen(color = tuple(self.current_settings['Analyse']['Windows'][window]['Colour']), style=Qt.DashLine, width=2), hoverPen=pg.mkPen(color = tuple(self.current_settings['Analyse']['Windows'][window]['Colour']), width=2), movable=True, bounds=[0, (int(self.current_settings['Analyse']['Windows'][window]['Start']) + int(self.current_settings['Analyse']['Windows'][window]['Length'])) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s')], name = 'Window ' + str(window))
            self.window_finish_draw[window] = pg.InfiniteLine(pos=(int(self.current_settings['Analyse']['Windows'][window]['Start']) + int(self.current_settings['Analyse']['Windows'][window]['Length'])) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'), angle=90, pen=pg.mkPen(color = tuple(self.current_settings['Analyse']['Windows'][window]['Colour']), style=Qt.DashLine, width=2), hoverPen=pg.mkPen(color = tuple(self.current_settings['Analyse']['Windows'][window]['Colour']), width=2), movable=True, bounds=[int(self.current_settings['Analyse']['Windows'][window]['Start']) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'), ur(str(self.current_settings['Time']['Blocklength']).replace(' ', '')).m_as('s')])
        self.plot_font = pg.Qt.QtGui.QFont()
        self.change_fontsize()

        self.itp.start_device()
        self.itp.setup_device(self.current_settings['Time']['Resolution'])
        if self.itp.dev.status["openunit"] is not 282 and self.itp.dev.status["openunit"] is not 286:
            self.four_channels()

        # Do a first measurement
        #self.start_thread()

        # Setup Delay generator
        if self.current_settings['Delay']['TriggerMode'] in 'Internal':
            self.TriggerExt.hide()
        else:
            self.TriggerInt.hide()
        self.tabWidget.removeTab(self.tabWidget.indexOf(self.DelayTab))


        # Show start-up message
        self.Messages.setText('Welcome to the PicoScope5000 interface\nPlease consider logging on with your name and project\n')
        if self.itp.dev.status["openunit"] == 286:
            self.Messages.append('Connected to USB2, check for USB3 connection')
        elif self.itp.dev.status["openunit"] == 282:
            self.Messages.append('No external powersupply connected, when working with a PicoScope5444D check the plug and restart for four channel options')

        # Display Delay Generator connector
        if self.current_settings['Delay']['Active'] > 0:
            self.open_delay_connection_window()

        # Interaction with interface
            # User tab
        self.Metadata_input.editingFinished.connect(self.change_importfile)
        self.Fontsize.valueChanged.connect(self.change_fontsize)
        self.Load_personal_settings_button.clicked.connect(self.load_button_pressed)
        self.Save_personal_settings_button.clicked.connect(self.save_personal_button_pressed)
        self.Import_personal_settings_metadata_button.clicked.connect(self.import_button_pressed)

        # Save tab
        self.Directory.editingFinished.connect(self.change_save_directory)
        self.Filename.editingFinished.connect(self.change_save_filename)
        self.Autosave.currentTextChanged.connect(self.change_save_autosave)

        # Time tab
        self.Resolution.currentTextChanged.connect(self.change_resolution)
        self.Samples.editingFinished.connect(self.change_samples)
        self.Blocklength.editingFinished.connect(self.change_blocklength)
        self.TActive.stateChanged.connect(self.change_trigger_active)
        self.TShow.stateChanged.connect(self.change_trigger_show)
        self.TChannel.currentTextChanged.connect(self.change_trigger_channel)
        self.TType.currentTextChanged.connect(self.change_trigger_type)
        self.TLevel.editingFinished.connect(self.change_trigger_level)
        self.TDelay.editingFinished.connect(self.change_trigger_delay)
        self.TPosition.editingFinished.connect(self.change_trigger_position)
        self.Autotrigger.editingFinished.connect(self.change_trigger_auto)

        # Channels tab
        for i in self.channels:
            self.ChannelActive[i].stateChanged.connect(partial(self.change_channel_active, i))
            self.ChannelRange[i].currentTextChanged.connect(partial(self.change_channel_range, i))
            self.ChannelCoupling[i].currentTextChanged.connect(partial(self.change_channel_coupling, i))
            self.ChannelName[i].editingFinished.connect(partial(self.change_channel_name, i))

        # Scope tab
        self.NumberOfMeasurements.editingFinished.connect(self.change_average_nom)
        self.Pause.editingFinished.connect(self.change_average_pause)
        self.ShowPlot.stateChanged.connect(self.change_showplot)
        self.Save_plot_button.clicked.connect(self.save_plot_window)

        # Scan tab
        self.AnalysisActive.stateChanged.connect(self.change_analyse_active)
        #self.AnalysisCalculate.currentTextChanged.connect(self.change_analyse_calculate)
        self.NumberOfScans.editingFinished.connect(self.change_analyse_scans)
        self.ScanPause.editingFinished.connect(self.change_analyse_pause)
        # Windows
        self.WindowSelect.currentTextChanged.connect(self.change_window)
        self.WindowColour.clicked.connect(self.change_window_colour)
        self.WindowShow.stateChanged.connect(self.change_window_show)
        self.WindowChannel.currentTextChanged.connect(self.change_window_channel)
        self.WindowStart.editingFinished.connect(self.change_window_start)
        self.WindowLength.editingFinished.connect(self.change_window_length)
        self.WindowDelete.clicked.connect(self.delete_window)
        # Calculators
        self.CalculatorSelect.currentTextChanged.connect(self.change_calculator)
        self.CalculatorColour.clicked.connect(self.change_calculator_colour)
        self.CalculatorShow.stateChanged.connect(self.change_calculator_show)
        self.FirstWindow.currentTextChanged.connect(self.change_first_window)
        self.Operation.currentTextChanged.connect(self.change_operation)
        self.SecondWindow.currentTextChanged.connect(self.change_second_window)
        self.CalculatorName.editingFinished.connect(self.change_calculator_name)
        self.CalculatorDelete.clicked.connect(self.delete_calculator)
        # Scanplot
        self.ShowScanPlot.stateChanged.connect(self.change_analyse_showplot)
        self.ScanValue.editingFinished.connect(self.change_analyse_scanvalue)
        self.ScanValueDifference.editingFinished.connect(self.change_analyse_scanvaluedifference)
        self.ScanLabel.editingFinished.connect(self.change_analyse_scanlabel)
        self.Save_scan_plot_button.clicked.connect(self.save_scan_plot_window)

        # Device
        self.actionPicoScope5444D.triggered.connect(self.four_channels)
        self.actionPicoScope5244D.triggered.connect(self.two_channels)

        # Main buttons
        self.start_button.clicked.connect(self.start_thread)
        self.continuously_button.clicked.connect(partial(self.start_thread, continuously = True))
        self.pause_button.clicked.connect(self.pause_measurement)
        self.stop_button.clicked.connect(self.stop_measurement)

        # Drag objects in plot
        self.current_triggerlevel.sigDragged.connect(self.change_trigger_level_drag)
        self.current_triggerposition.sigDragged.connect(self.change_trigger_position_drag)
        for window in self.windows:
            self.window_start_draw[window].sigDragged.connect(partial(self.change_window_start_drag, window))
            self.window_finish_draw[window].sigDragged.connect(partial(self.change_window_finish_drag, window))

        # Delay generator
        self.SRS_Connect.triggered.connect(self.open_delay_connection_window)
        self.SRS_Disconnect.triggered.connect(self.disconnect_delay_generator)
        #self.Delay_connection_active.stateChanged.connect(self.delay_setup_connection)
        #self.Delay_connection_port.editingFinished.connect(self.delay_change_port)
        self.Delay_signal_type.currentTextChanged.connect(self.delay_change_signal)
        self.Delay_signal_load.currentTextChanged.connect(self.delay_change_load)
        self.Delay_Ext_trigger_mode.currentTextChanged.connect(partial(self.delay_change_trigger_mode, 'External'))
        self.Delay_trigger_load.currentTextChanged.connect(self.delay_change_trigger_load)
        self.Delay_trigger_edge.currentTextChanged.connect(self.delay_change_trigger_edge)
        self.Delay_trigger_level.editingFinished.connect(self.delay_change_trigger_level)
        self.Delay_Int_trigger_mode.currentTextChanged.connect(partial(self.delay_change_trigger_mode, 'Internal'))
        self.Delay_trigger_rate.editingFinished.connect(self.delay_change_trigger_rate)
        for connector in self.primary_connectors:
            self.Delay[connector].editingFinished.connect(partial(self.delay_change_delay, connector))
            # self.Difference[connector].editingFinished.connect(partial(self.delay_change_difference, connector))
            self.From[connector].currentTextChanged.connect(partial(self.delay_change_from, connector))


# -------------------------------------------------------------------------------

    def two_channels(self):
        if self.device_channels == 4:
            self.current_settings['Channels']['C']['Active'] = 0
            self.current_settings['Channels']['D']['Active'] = 0
            if self.current_settings['Trigger']['Channel'] in ['C', 'D']:
                self.TChannel.setCurrentText('A')
            for window in self.windows:
                if self.current_settings['Analyse']['Windows'][window]['Channel'] in ['C', 'D']:
                    self.current_settings['Analyse']['Windows'][window]['Channel'] = 'A'
                if str(self.WindowChannel.currentText) in ['C', 'D']:
                    self.WindowChannel.setCurrentText('A')
                self.WindowChannel.removeItem(self.WindowChannel.findText('C'))
                self.WindowChannel.removeItem(self.WindowChannel.findText('D'))
            self.ChannelC.hide()
            self.ChannelD.hide()
            self.TChannel.removeItem(self.TChannel.findText('C'))
            self.TChannel.removeItem(self.TChannel.findText('D'))
            self.device_channels = 2
            self.channels = ['A', 'B']
            for i in self.channels:
                self.channel_changed[i] = True

    def four_channels(self):
        if self.device_channels == 2:
            if self.itp.dev.status["openunit"] == 282 or self.itp.dev.status["openunit"] == 286:
                self.Messages.append('Can not power four channels in USB power mode')
            else:
                self.ChannelC.show()
                self.ChannelD.show()
                self.WindowChannel.addItem('C')
                self.WindowChannel.addItem('D')
                self.TChannel.addItem('C')
                self.TChannel.addItem('D')
                self.device_channels = 4
                self.channels = ['A', 'B', 'C', 'D']
                for i in self.channels:
                    self.channel_changed[i] = True

    def start_thread(self, continuously = False):
        if not self.measurement_running:
            self.timer = QTimer() # Start a timer to update the plot
            if self.current_settings['Analyse']['ShowPlot'] == 2:
                self.timer.timeout.connect(self.plot_scan)
            if self.current_settings['Plot']['Show'] == 2:
                self.timer.timeout.connect(self.plot_measurement)
            self.timer.start(1000)  # Time in millieseconds
            #self.start_measurement()
            measurement_thread = threading.Thread(target = partial(self.start_measurement, continuously))
            measurement_thread.daemon = True
            measurement_thread.start()
        else:
            self.Messages.append('Measurement already running')

    def start_measurement(self, continuously):
        #starttime = time()
        self.measurement_running = True
        self.continuously = continuously
        self.date = str(date.today())
        if not os.path.isdir(os.path.join(self.current_settings['Save']['Folder'], self.date)):
            os.makedirs(os.path.join(self.current_settings['Save']['Folder'], self.date))
        self.measurement_name = str(self.Name.text())
        self.measurement_project = str(self.Project.text())
        self.set_measurement_settings()
        self.block_too_slow = False
        scan_too_slow = False
        if not os.path.isdir(self.current_settings['Save']['Folder']):  # If there is no such folder create one
            os.makedirs(self.current_settings['Save']['Folder'])
        #self.Messages.append('Measurement started')
        #print('Time before starting: ', time()- starttime)
        if self.current_settings['Analyse']['Active']: # and self.current_settings['Delay']['Active'] > 0:
            if 'Delay ' in str(self.current_settings['Analyse']['ScanLabel']) and self.current_settings['Delay']['Active'] > 0:
                self.Delay[str(self.current_settings['Analyse']['ScanLabel']).replace('Delay ', '')].setText(str(float(self.current_settings['Analyse']['ScanValue'])) + ' s')
                self.delay_change_delay(str(self.current_settings['Analyse']['ScanLabel']).replace('Delay ', ''))
            self.scannumber = 1
            self.scanfile = os.path.join(self.current_settings['Save']['Folder'], self.date, self.current_settings['Save']['Filename'] + '_' + str(self.date) + '_scan_{}.yml'.format(self.scannumber))
            while os.path.isfile(self.scanfile):
                self.scannumber += 1
                self.scanfile = os.path.join(self.current_settings['Save']['Folder'], self.date, self.current_settings['Save']['Filename'] + '_' + str(self.date) + '_scan_{}.yml'.format(self.scannumber))
            if not self.current_settings['Save']['Autosave'] in 'Never':
                self.binarydirectory = os.path.join(self.current_settings['Save']['Folder'], self.date, self.current_settings['Save']['Filename'] + '_' + str(self.date) + '_scan_{}_scope'.format(self.scannumber))
                if not os.path.isdir(self.binarydirectory):
                    os.makedirs(self.binarydirectory)
            self.itp.reset_scandata(self.calculators)
            self.save_personal_settings(self.measurement_name, self.measurement_project, self.scanfile.replace('.yml', '_metadata.yml'), metadata = True)#os.path.join(self.current_settings['Save']['Folder'], self.current_settings['Save']['Filename'] + '_' + str(self.scan_start_time).replace('.', '_') + '_metadata.yml'), metadata=True)
            if continuously:
                scans = 1000000
            else:
                scans = self.current_settings['Analyse']['Scans']
            #print('Time before really starting: ', time() - starttime)
            self.scan_start_time = time()
            #
            # Loop for every scan
            #
            for self.averagenumber in range(scans):
                self.meaurement_start_time = time()
                self.run_measurement()
                if not self.measurement_running:
                    break
                else:
                    for window in self.windows:
                        self.itp.read_windows(window, int(self.current_settings['Analyse']['Windows'][window]['Start']), int(self.current_settings['Analyse']['Windows'][window]['Start']) + int(self.current_settings['Analyse']['Windows'][window]['Length']), self.current_settings['Analyse']['Windows'][window]['Channel'])
                        # print('Windows read after: ', time() - self.meaurement_start_time)
                    self.itp.compute_scanpoint_scanvalue(float(self.current_settings['Analyse']['ScanValue']) + int(self.averagenumber)*float(self.current_settings['Analyse']['ScanValueDifference']))
                    if 'Delay ' in str(self.current_settings['Analyse']['ScanLabel']) and self.current_settings['Delay']['Active'] > 0:
                        self.Delay[str(self.current_settings['Analyse']['ScanLabel']).replace('Delay ', '')].setText(str(float(self.current_settings['Analyse']['ScanValue']) + int(self.averagenumber)*float(self.current_settings['Analyse']['ScanValueDifference'])) + ' s')
                        self.delay_change_delay(str(self.current_settings['Analyse']['ScanLabel']).replace('Delay ', ''))
                    for calculator in self.calculators:
                        if self.current_settings['Analyse']['Calculators'][calculator]['Show'] == 2:
                            self.itp.compute_scanpoint(int(calculator), int(self.current_settings['Analyse']['Calculators'][calculator]['FirstWindow']), str(self.current_settings['Analyse']['Calculators'][calculator]['Operation']), int(self.current_settings['Analyse']['Calculators'][calculator]['SecondWindow']), [str(self.current_settings['Channels'][self.current_settings['Analyse']['Windows'][int(self.current_settings['Analyse']['Calculators'][calculator]['FirstWindow'])]['Channel']]['Range']), str(self.current_settings['Channels'][self.current_settings['Analyse']['Windows'][int(self.current_settings['Analyse']['Calculators'][calculator]['SecondWindow'])]['Channel']]['Range'])], int(self.current_settings['Time']['maxADC']))
                    #print('Scanpoint computed after: ', time() - self.meaurement_start_time)
                    self.save_scandata(self.scanfile)
                    #print('Scandata saved after: ', time() - self.meaurement_start_time)
                    if self.averagenumber < self.current_settings['Analyse']['Scans']-1 or continuously:
                        if time() - self.meaurement_start_time > ur(self.current_settings['Analyse']['Pause'].replace(' ', '')).m_as('s'):
                            if not scan_too_slow:
                                self.Messages.append('Can not keep up with scanrate, increase Time between scans ({})'.format(str(round(time() - self.meaurement_start_time, 4)) + ' s'))
                                scan_too_slow = True
                        else:
                            while time() - self.meaurement_start_time < ur(self.current_settings['Analyse']['Pause'].replace(' ', '')).m_as('s'):
                                pass
                    else:
                        self.measurement_running = False
        else:
            self.averagenumber = 0
            if not self.current_settings['Save']['Autosave'] in 'Never':
                self.binarydirectory = os.path.join(self.current_settings['Save']['Folder'], self.date, self.current_settings['Save']['Filename'] + '_' + str(self.date) + '_measurement_{}_scope'.format(self.averagenumber+1))
                while os.path.isdir(self.binarydirectory):
                    self.averagenumber += 1
                    self.binarydirectory = os.path.join(self.current_settings['Save']['Folder'], self.date, self.current_settings['Save']['Filename'] + '_' + str(self.date) + '_measurement_{}_scope'.format(self.averagenumber + 1))
                if not os.path.isdir(self.binarydirectory):
                    os.makedirs(self.binarydirectory)
            while self.measurement_running:
                self.meaurement_start_time = time()
                self.run_measurement()
                if not continuously:
                    self.measurement_running = False
        #self.Messages.append('Measurement finished')

    def stop_measurement(self):
        if self.measurement_running:
            self.measurement_running = False
            self.measurement_pause = False
            self.continue_after_setting = False
            self.pause_button.setText('Pause')
            #self.Messages.append('Measurement stopped')

    def pause_measurement(self):
        if self.measurement_running:
            if self.measurement_pause:
                self.measurement_pause = False
                self.pause_button.setText('Pause')
            else:
                self.measurement_pause = True
                self.pause_button.setText('Continue')

    def run_measurement(self):
        self.itp.reset_buffer_sum()
        #print('Measurement time: ', self.meaurement_start_time)
        for self.measurementnumber in range(self.current_settings['Average']['Blocks']):
            while self.measurement_pause:
                if self.continue_after_setting:
                    self.set_measurement_settings()
                    self.continue_after_setting = False
                    self.measurement_pause = False
                else:
                    pass
            if not self.measurement_running:
                break
            else:
                #print('Next block: ', time() - self.meaurement_start_time)
                self.get_block()
                #print('Block obtained after: ', time() - self.meaurement_start_time)
                if self.current_settings['Save']['Autosave'] in 'Every scope':
                    if self.current_settings['Analyse']['Active'] == 2:
                        filename = str(self.current_settings['Save']['Filename']) + '_' + str(self.date) + '_scan_{}_{}_{}.bin'.format(self.scannumber, self.averagenumber+1, self.measurementnumber+1)
                    else:
                        filename = str(self.current_settings['Save']['Filename']) + '_' + str(self.date) + '_measurement_{}_{}.bin'.format(self.averagenumber+1, self.measurementnumber+1)
                    self.itp.save_binary(os.path.join(self.binarydirectory, filename), self.active_channels)
                    message = 'Data saved for ' + self.measurement_project + ' by ' + self.measurement_name + ' to ' + filename
                    #self.Messages.append(message)
                #if self.measurementnumber < self.current_settings['Average']['Blocks']-1:
                delay = (self.measurementnumber + 1)*ur(self.current_settings['Average']['Pause'].replace(' ', '')).m_as('s')
                if time() - self.meaurement_start_time > delay:
                    if not self.block_too_slow:
                        self.Messages.append('Can not keep up with measurementrate, increase Time between measurements ({})'.format(str(round(time() - self.meaurement_start_time, 4)) + ' s'))
                        self.block_too_slow = True
                else:
                    while time() - self.meaurement_start_time < delay:
                        pass
                if self.measurementnumber == self.current_settings['Average']['Blocks'] - 1:
                    self.itp.block_average(self.current_settings['Average']['Blocks'])
                    #print('Averaged over blocks after: ', time() - self.meaurement_start_time)
                    if self.current_settings['Save']['Autosave'] in 'Every scope average':
                        if self.current_settings['Analyse']['Active'] == 2:
                            filename = str(self.current_settings['Save']['Filename']) + '_' + str(self.date) + '_scan_{}_{}.bin'.format(self.scannumber, self.averagenumber + 1)
                        else:
                            filename = str(self.current_settings['Save']['Filename']) + '_' + str(self.date) + '_measurement_{}.bin'.format(self.averagenumber + 1)
                        if self.current_settings['Analyse']['Active'] == 0:
                            self.save_personal_settings(self.measurement_name, self.measurement_project, os.path.join(self.current_settings['Save'][ 'Folder'], self.date, filename.replace('.bin', '_metadata.yml')), metadata=True)
                        if self.current_settings['Save']['Autosave'] not in 'Every scope':
                            self.itp.save_binary(os.path.join(self.binarydirectory, filename), self.active_channels, Average = True)
                            message = 'Data saved for ' + self.measurement_project + ' by ' + self.measurement_name + ' to ' + filename
                            #self.Messages.append(message)
        self.newData = True

    def plot_measurement(self):
        if self.newData:
            try:
                self.scope_legend.scene().removeItem(self.scope_legend)
            except:
                pass
            self.scope_legend = self.plot_window.addLegend()
            try:
                    for channel in self.active_channels:
                        self.itp.interpret_data(self.current_settings['Time']['Samples'], ur(str(self.current_settings['Time']['Timestep'])).m_as('ns'), channel, str(self.current_settings['Channels'][channel]['Range']), 1000)
                    self.plot_data()
            except KeyError:
                pass
            self.newData = False

    def plot_scan(self):
        try:
            self.scan_plot_window.clear()
            try:
                self.scan_legend.scene().removeItem(self.scan_legend)
            except:
                pass
            self.scan_legend = self.scan_plot_window.addLegend()
            for calculator in self.calculators:
                try:
                    self.scan_plot_window.plot(self.itp.scandata['Scanvalue'][:], self.itp.scandata[calculator][:], pen=tuple(self.current_settings['Analyse']['Calculators'][calculator]['Colour']), symbol='s', symbolPen=tuple(self.current_settings['Analyse']['Calculators'][calculator]['Colour']), symbolBrush=tuple(self.current_settings['Analyse']['Calculators'][calculator]['Colour']), name = str(self.current_settings['Analyse']['Calculators'][calculator]['Name']))
                except:
                    pass
        except:
            pass

    def open_plot_window(self):
        self.plot_window = pg.plot(title='Picoscope5000 Scope', icon=os.path.join(self.base_folder, 'icon.png'), background='w')
        #self.plot_window.setWindowIcon(QIcon(os.path.join(self.base_folder, 'icon.png')))
        self.plot_window.showGrid(x=True, y=True)
        self.change_plot_fontsize()
        if not self.measurement_running:
            try:
                #metadatafile = os.path.join(self.current_settings['Save']['Folder'], self.current_settings['Save']['Filename'] + '_' + str(self.meaurement_start_time).replace('.', '_') + '_metadata.yml')
                self.plot_measurement()
            except AttributeError:
                pass

    def close_plot_window(self):
        self.plot_window.win.close()

    def save_plot_window(self):
        if self.current_settings['Analyse']['Active']:
            self.binarydirectory = self.scanfile.replace('.yml', '_scope')
            if not os.path.isdir(self.binarydirectory):
                os.makedirs(self.binarydirectory)
            file = os.path.join(self.binarydirectory, self.current_settings['Save']['Filename'] + '_' + str(self.date) + '_scan_{}'.format(self.scannumber) + '_{}_scope.png'.format(str(self.averagenumber + 1)))#self.scanfile.replace('.yml', '_{}_scope.png'.format(str(self.averagenumber + 1)))
        else:
            self.binarydirectory = os.path.join(self.current_settings['Save']['Folder'], self.date, self.current_settings['Save']['Filename'] + '_' + str(self.date) + '_measurement_{}_scope'.format(self.averagenumber+1))
            if not os.path.isdir(self.binarydirectory):
                os.makedirs(self.binarydirectory)
            file = os.path.join(self.binarydirectory, self.current_settings['Save']['Filename'] + '_' + str(self.date) + '_measurement_{}_scope.png'.format(self.averagenumber + 1))
        exp = pg.exporters.ImageExporter(self.plot_window.plotItem)
        exp.params.param('width').setValue(int(self.plot_window.width() * 3), blockSignal=exp.widthChanged)
        exp.params.param('height').setValue(int(self.plot_window.height() * 3), blockSignal=exp.heightChanged)
        save_plot_thread = threading.Thread(target = exp.export(file))
        save_plot_thread.daemon = True
        save_plot_thread.start()
        #self.Messages.append('Scope plot saved to {}'. format(str(file)))

    def open_scan_plot_window(self):
        self.scan_plot_window = pg.plot(title='Picoscope5000 Scan', background='w')
        #self.scan_plot_window.setWindowIcon(QIcon(os.path.join(self.base_folder, 'icon.png')))
        self.scan_plot_window.showGrid(x=True, y=True)
        self.scan_plot_window.setXRange(float(self.current_settings['Analyse']['ScanValue']), float(self.current_settings['Analyse']['ScanValue']) + float(self.current_settings['Analyse']['ScanValueDifference']) * (int(self.current_settings['Analyse']['Scans']) - 1))
        self.change_scan_plot_fontsize()
        if not self.measurement_running:
            try:
                self.plot_scan()
            except AttributeError:
                pass

    def close_scan_plot_window(self):
        self.scan_plot_window.win.close()

    def save_scan_plot_window(self):
        try:
            exp = pg.exporters.ImageExporter(self.scan_plot_window.plotItem)
            exp.params.param('width').setValue(int(self.scan_plot_window.width()*3), blockSignal=exp.widthChanged)
            exp.params.param('height').setValue(int(self.scan_plot_window.height()*3), blockSignal=exp.heightChanged)
            file = self.scanfile.replace('yml', 'png') #os.path.join(self.current_settings['Save']['Folder'], str(self.current_settings['Save']['Filename']) + '_' + str(self.scan_start_time).replace('.', '_') + '_scan.png')
            save_plot_thread = threading.Thread(target = exp.export(file))
            save_plot_thread.daemon = True
            save_plot_thread.start()
            #self.Messages.append('Scan plot saved to {}'. format(str(file)))
        except AttributeError:
            self.Messages.append('No scanplot available')

    def set_measurement_settings(self):
        #self.measurement_settings = self.current_settings
        self.active_channels = [i for i in self.channels if self.current_settings['Channels'][i]['Active'] == 2]
        for i in self.channels:
            if self.channel_changed[i]:
                self.itp.setup_channel(i, self.current_settings['Channels'][i]['Active'], self.current_settings['Channels'][i]['CouplingType'], self.current_settings['Channels'][i]['Range'])
                #message = 'Channel ' + i + 'set'
                #self.Messages.append(message)
                self.channel_changed[i] = False
        if self.resolution_changed:
            self.itp.set_resolution(self.current_settings['Time']['Resolution'])
            #message = 'Resolution set'
            #self.Messages.append(message)
            self.resolution_changed = False
            self.timewindow_changed = True

        if self.timewindow_changed:
            # self.calculate_timebase()
            self.itp.set_timewindow(self.current_settings['Time']['Samples'], self.current_settings['Time']['Timebase'])
            #message = 'Timewindow set'
            #self.Messages.append(message)
            self.timewindow_changed = False
            for i in self.channels:
                self.buffer_changed[i] = True
            for i in self.channels:
                if self.buffer_changed[i]:
                    if self.current_settings['Channels'][i]['Active'] == 2:
                        self.itp.set_buffer(i, self.current_settings['Time']['Samples'])
                    else:
                        try:
                            del self.itp.buffer[i]
                        except KeyError:
                            pass
                    #message = 'Buffer for channel ' + i + 'set'
                    #self.Messages.append(message)
                    self.buffer_changed[i] = False

        if self.trigger_changed:
            if self.current_settings['Trigger']['Channel'] in 'External':
                self.itp.set_trigger(int(self.current_settings['Trigger']['Active']), self.current_settings['Trigger']['Channel'], self.current_settings['Trigger']['Type'], self.current_settings['Trigger']['Level'], self.current_settings['Trigger']['Delay'], self.current_settings['Trigger']['Auto'])
            else:
                self.itp.set_trigger(int(self.current_settings['Trigger']['Active']), self.current_settings['Trigger']['Channel'], self.current_settings['Trigger']['Type'], self.current_settings['Trigger']['Level'], self.current_settings['Trigger']['Delay'], self.current_settings['Trigger']['Auto'], self.current_settings['Channels'][self.current_settings['Trigger']['Channel']]['Range'])
            #message = 'Trigger set'
            #self.Messages.append(message)
            self.trigger_changed = False
        self.current_settings['Time']['maxADC'] = int(self.itp.maxADC.value)
        self.itp.block = {}

    def get_block(self):
        self.itp.get_block(self.current_settings['Time']['Samples'], self.current_settings['Trigger']['Position'], self.current_settings['Time']['Timebase'])
        self.itp.read_data()
        self.itp.add_to_buffer_sum()

    '''

    def save_binary_old(self, folder, file, active_channels): # overwriteprevention, save_channels,
        
        filename = os.path.join(folder, file+'_binary')
        if not os.path.isdir(folder):  # If there is no such folder create one
            os.makedirs(folder)
        if overwriteprevention in 'Number':
            i = 1
            full_file = filename + '_' + str(i) + '.bin'
            while os.path.isfile(full_file):
                i += 1
                full_file = filename + '_' + str(i) + '.bin'
            filename = full_file
        elif overwriteprevention in 'None':
            filename += '.bin'
        elif overwriteprevention in 'Time':
            filename += '_' + str(self.meaurement_start_time).replace('.', '_') + '.bin'
        
        filename = os.path.join(folder, file + '_' + str(self.meaurement_start_time).replace('.', '_') + '_binary.bin')
        self.itp.save_binary_old(filename, active_channels)

        
    def interpret_data(self, metadatafile, active_channels, blocknumber):
        self.itp.interpret_data(metadatafile, active_channels, blocknumber)
        
        for i in self.channels:
            if self.current_settings['Channels'][i]['Active'] == 2:
                self.itp.interpret_data(i, self.current_settings['Channels'][i]['Range'], blocknumber, self.current_settings['Average']['Blocks'], self.current_settings['Average']['Store'])
        '''
    def plot_data(self):
        try:
            self.plot_window.clear()
        except AttributeError:
            self.change_showplot()
            self.plot_window.clear()
        if self.current_settings['Trigger']['Show'] == 2:
            self.show_trigger(self.current_settings['Trigger']['Level'], self.current_settings['Trigger']['Position'], measurement = True)
            self.show_trigger()
        for window in self.windows:
            if self.current_settings['Analyse']['Windows'][window]['Show'] == 2:
                self.plot_window.addItem(self.window_start_draw[window])
                self.plot_window.addItem(self.window_finish_draw[window])
        for i in self.channels:
            if self.current_settings['Channels'][i]['Active'] == 2:
                try:
                    self.plot_window.plot([j/1000000000 for j in self.itp.block['Time']], [k/1000 for k in self.itp.block[i][:]], pen=self.channel_colour[i], name = self.current_settings['Channels'][i]['Name'])
                except KeyError:
                    pass

    def show_trigger(self, level = False, position = False, measurement = False):
        '''
        if measurement:
            self.measurement_triggerlevel = pg.InfiniteLine(pos = ur(str(level).replace(' ', '')).m_as('V'), angle = 0, pen = pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']], style=Qt.DotLine))
            self.measurement_triggerposition = pg.InfiniteLine(pos = (int(position))*ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'), angle = 90, pen = pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']], style=Qt.DotLine))
            self.plot_window.addItem(self.measurement_triggerlevel)
            self.plot_window.addItem(self.measurement_triggerposition)
        else:
        '''
        self.plot_window.addItem(self.current_triggerlevel)
        self.plot_window.addItem(self.current_triggerposition)

    def remove_trigger(self):
        self.plot_window.removeItem(self.current_triggerlevel)
        self.plot_window.removeItem(self.current_triggerposition)

    def calculate_timebase(self):
        NumberOfActiveChannels = 0
        for i in self.channels:
            if self.current_settings['Channels'][i]['Active'] == 2:
                NumberOfActiveChannels += 1
        blocklength_unit = str(self.current_settings['Time']['Blocklength'])[-2:].replace(' ','')
        Timebase_data = self.itp.calculate_timebase(NumberOfActiveChannels, self.current_settings['Time']['Resolution'], self.current_settings['Time']['Samples'], self.current_settings['Time']['Blocklength'])
        self.current_settings['Time']['Timebase'] = Timebase_data[0]
        self.current_settings['Time']['Timestep'] = str(Timebase_data[1])
        self.current_settings['Time']['Blocklength'] = str(ur(str(int(ur(Timebase_data[2]).m_as('ns'))) + 'ns').m_as(blocklength_unit))+ ' ' + blocklength_unit
        self.Timestep.setText(str(Timebase_data[1]))
        self.Blocklength.setText(self.current_settings['Time']['Blocklength'])
        if Timebase_data[3]:
            self.Messages.append(str(Timebase_data[3]))
        if self.first_timebase:
            self.first_timebase = False
        else:
            self.change_trigger_position()
            for window in self.windows:
                self.change_window_start_drag(window)
                self.change_window_finish_drag(window)

    def load_button_pressed(self):
        self.load_personal_settings(self.Name.text(), self.Project.text())

    def save_personal_button_pressed(self):
        file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'users.yml')
        self.check_personal_settings(self.Name.text(), self.Project.text(), file)
        if self.ready_to_save_personal:
            self.save_personal_settings(str(self.Name.text()), str(self.Project.text()), file)

    def import_button_pressed(self):
        self.load_personal_settings(self.Name.text(), self.Project.text(), metadata=True)

    def load_personal_settings(self, name, project, metadata=False): # Take settings from users.yml file and store in self.current_settings
        base_dir = os.path.dirname(os.path.dirname(__file__))
        if metadata:
            try:
                self.close_plot_window()
            except AttributeError:
                pass
            try:
                self.close_scan_plot_window()
            except AttributeError:
                pass
            users_file = self.Metadata_input.text()
            if not os.path.isfile(users_file):
                self.Messages.append('Metadatafile not found')
                return
        else:
            users_file = os.path.join(base_dir, 'config', 'users.yml')
        f = open(users_file, 'r')
        users = yaml.safe_load(f)
        f.close()
        if name not in users and metadata is not True:
            message = 'No settings stored for ' + name
            self.Messages.append(message)
        elif metadata is not True and project not in users[name]:
            message = 'No settings stored for ' + project + ' by ' + name + ', only '
            for projectname in users[name]:
                message += projectname + ' '
            self.Messages.append(message)
        else:
            try:
                self.ShowPlot.setCheckState(0)
                self.ShowScanPlot.setCheckState(0)
                self.change_showplot()
                self.change_analyse_showplot()
            except:
                pass
            if metadata:
                for i in users:
                    meta_name = i
                    for j in users[meta_name]:
                        meta_project = j
                self.current_settings = users[meta_name][meta_project]
            else:
                self.current_settings = users[name][project]
                self.Name.setText(name)
                self.Project.setText(project)
                if name == 'DefaultUser':
                    self.current_settings['Save']['Folder'] = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'PicoscopeData')
                    self.current_settings['Metadata']['Importfile'] = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'PicoscopeData', 'DefaultData_start_time_metadata.yml')
            self.NumberOfMeasurements.setText(str(self.current_settings['Average']['Blocks']))
            self.Pause.setText(str(self.current_settings['Average']['Pause']))
            self.ShowPlot.setCheckState(int(self.current_settings['Plot']['Show']))

            #self.StoreAll.setCheckState(int(self.current_settings['Average']['Store']))
            self.Directory.setText(str(self.current_settings['Save']['Folder']))
            self.Filename.setText(str(self.current_settings['Save']['Filename']))
            #self.Overwrite_prevention.setCurrentText(str(self.current_settings['Save']['Overwriteprevention']))
            #self.Save_metadata.setCheckState(int(self.current_settings['Save']['Metadata']))
            #self.Save_channels.setCurrentText(str(self.current_settings['Save']['Channels']))
            self.Autosave.setCurrentText(str(self.current_settings['Save']['Autosave']))
            self.Metadata_input.setText(str(self.current_settings['Metadata']['Importfile']))
            self.Fontsize.setValue(int(self.current_settings['User']['Fontsize']))
            for i in self.channels:
                self.ChannelActive[i].setCheckState(self.current_settings['Channels'][i]['Active'])
                self.ChannelRange[i].setCurrentText(str(self.current_settings['Channels'][i]['Range']))
                self.ChannelCoupling[i].setCurrentText(str(self.current_settings['Channels'][i]['CouplingType']))
                self.ChannelName[i].setText(str(self.current_settings['Channels'][i]['Name']))
                '''
                self.ChannelSave[i].setCheckState(int(self.current_settings['Channels'][i]['Save']))
                self.ChannelSave2[i].setCheckState(int(self.current_settings['Channels'][i]['Save']))
                if i == self.current_settings['Trigger']['Channel']:
                    self.ChannelTrigger[i].setCheckState(2)
                else:
                    self.ChannelTrigger[i].setCheckState(0)
                '''
            self.TActive.setCheckState(int(self.current_settings['Trigger']['Active']))
            self.TShow.setCheckState(int(self.current_settings['Trigger']['Show']))
            self.TChannel.setCurrentText(str(self.current_settings['Trigger']['Channel']))
            self.TType.setCurrentText(str(self.current_settings['Trigger']['Type']))
            self.TLevel.setText(str(self.current_settings['Trigger']['Level']))
            self.TDelay.setText(str(self.current_settings['Trigger']['Delay']))
            self.TPosition.setText(str(self.current_settings['Trigger']['Position']))
            self.Autotrigger.setText(str(self.current_settings['Trigger']['Auto']))
            self.Resolution.setCurrentText(str(self.current_settings['Time']['Resolution']))
            self.Samples.setText(str(self.current_settings['Time']['Samples']))
            self.Blocklength.setText(str(self.current_settings['Time']['Blocklength']))
            self.AnalysisActive.setCheckState(int(self.current_settings['Analyse']['Active']))
            self.ShowScanPlot.setCheckState(int(self.current_settings['Analyse']['ShowPlot']))
            #self.AnalysisCalculate.setCurrentText(str(self.current_settings['Analyse']['Calculate']))
            if 'Delay ' in str(self.current_settings['Analyse']['ScanLabel']) and self.current_settings['Delay']['Active'] > 0:
                self.ScanValue.setText(str(self.current_settings['Analyse']['ScanValue']) + ' s')
                self.ScanValueDifference.setText(str(self.current_settings['Analyse']['ScanValueDifference']) + ' s')
            else:
                self.ScanValue.setText(str(self.current_settings['Analyse']['ScanValue']))
                self.ScanValueDifference.setText(str(self.current_settings['Analyse']['ScanValueDifference']))
            self.ScanLabel.setText(str(self.current_settings['Analyse']['ScanLabel']))
            self.NumberOfScans.setText(str(self.current_settings['Analyse']['Scans']))
            self.ScanPause.setText(str(self.current_settings['Analyse']['Pause']))
            self.windows = {window: window for window in self.current_settings['Analyse']['Windows']}
            self.calculators = {calculator: calculator for calculator in self.current_settings['Analyse']['Calculators']}
            for window in self.windows:
                self.WindowSelect.addItem('Window {}'.format(window))
                self.FirstWindow.addItem('Window {}'.format(window))
                self.SecondWindow.addItem('Window {}'.format(window))
            self.current_window = 1
            self.WindowSelect.setCurrentText('Window 1')
            self.WindowColour.setStyleSheet('background-color:rgb({}, {}, {})'.format(self.current_settings['Analyse']['Windows'][self.current_window]['Colour'][0], self.current_settings['Analyse']['Windows'][self.current_window]['Colour'][1], self.current_settings['Analyse']['Windows'][self.current_window]['Colour'][2]))
            self.WindowShow.setCheckState(int(self.current_settings['Analyse']['Windows'][1]['Show']))
            self.WindowChannel.setCurrentText(str(self.current_settings['Analyse']['Windows'][1]['Channel']))
            self.WindowStart.setText(str(self.current_settings['Analyse']['Windows'][1]['Start']))
            self.WindowLength.setText(str(self.current_settings['Analyse']['Windows'][1]['Length']))
            for calculator in self.calculators:
                self.CalculatorSelect.addItem('Calculator {}'.format(calculator))
            self.current_calculator = 1
            self.CalculatorSelect.setCurrentText('Calculator 1')
            self.CalculatorColour.setStyleSheet('background-color:rgb({}, {}, {})'.format(self.current_settings['Analyse']['Calculators'][self.current_calculator]['Colour'][0], self.current_settings['Analyse']['Calculators'][self.current_calculator]['Colour'][1], self.current_settings['Analyse']['Calculators'][self.current_calculator]['Colour'][2]))
            self.FirstWindow.setCurrentText('Window ' + str(self.current_settings['Analyse']['Calculators'][1]['FirstWindow']))
            self.Operation.setCurrentText(str(self.current_settings['Analyse']['Calculators'][1]['Operation']))
            self.SecondWindow.setCurrentText('Window ' + str(self.current_settings['Analyse']['Calculators'][1]['SecondWindow']))
            self.CalculatorName.setText(str(self.current_settings['Analyse']['Calculators'][1]['Name']))
            self.CalculatorShow.setCheckState(int(self.current_settings['Analyse']['Calculators'][1]['Show']))
            # Delay generator settings
            #self.Delay_connection_active.setCheckState(int(self.current_settings['Delay']['Active']))
            #self.Delay_connection_port.setText(str(self.current_settings['Delay']['Port']))
            self.Delay_signal_type.setCurrentText(str(self.current_settings['Delay']['Type']))
            self.Delay_signal_load.setCurrentText(str(self.current_settings['Delay']['Load']))
            self.Delay_Ext_trigger_mode.setCurrentText(str(self.current_settings['Delay']['TriggerMode']))
            self.Delay_trigger_load.setCurrentText(str(self.current_settings['Delay']['TriggerLoad']))
            self.Delay_trigger_edge.setCurrentText(str(self.current_settings['Delay']['TriggerEdge']))
            self.Delay_trigger_level.setText(str(self.current_settings['Delay']['TriggerLevel']))
            self.Delay_Int_trigger_mode.setCurrentText(str(self.current_settings['Delay']['TriggerMode']))
            self.Delay_trigger_rate.setText(str(self.current_settings['Delay']['TriggerRate']))
            for connector in self.primary_connectors:
                self.Delay[connector].setText(str(self.current_settings['Delay']['Connectors'][connector]['Delay']))
                #self.Difference[connector].setText(str(self.current_settings['Delay']['Connectors'][connector]['Difference']))
                self.From[connector].setCurrentText(str(self.current_settings['Delay']['Connectors'][connector]['From']))

            self.resolution_changed = True # Mark that settings are changed
            for i in self.channels:
                self.channel_changed[i] = True
                self.buffer_changed[i] = True
            self.timewindow_changed = True
            self.trigger_changed = True
            self.calculate_timebase() # Recalculate the timebase

            message = 'Settings loaded for ' + project + ' by ' + name
            if metadata == 1:
                message = message + ' from metadata for ' + meta_project + ' by ' + meta_name
            #self.Messages.append(message)
            if int(self.current_settings['Plot']['Show']) == 2:
                self.open_plot_window()
            if int(self.current_settings['Analyse']['ShowPlot']) == 2:
                self.open_scan_plot_window()
        '''
            if self.current_settings['Plot']['Show'] == 2:
                self.change_showplot()

            if self.current_settings['Analyse']['ShowPlot'] == 2:
                self.change_analyse_showplot()
        '''
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True

    def check_personal_settings(self, name, project, file):
        if self.confirm_overwrite_personal:
            self.ready_to_save_personal = True
        else:
            self.ready_to_save_personal = False
            if name in 'DefaultUser':
                self.Messages.append('Not allowed to overwrite Default settings')
            else:
                f = open(file, 'r')
                users = yaml.safe_load(f)
                f.close()
                if name in users:
                    if project in users[name]:
                        message = 'Settings for ' + project + ' by ' + name + ' already saved. Press save again to overwrite with current settings'
                        self.Messages.append(message)
                        self.confirm_overwrite_personal = True
                        save_confirmation_thread = threading.Thread(target=self.wait_for_confirmation, args=(5,))
                        save_confirmation_thread.start()
                    else:
                        self.ready_to_save_personal = True
                else:
                    self.ready_to_save_personal = True

    def wait_for_confirmation(self, time_in_seconds):
        sleep(time_in_seconds)
        self.confirm_overwrite_personal = False

    def autosave_settings(self):
        if str(self.Name.text()) in 'DefaultUser':
            self.save_personal_settings('AutoSaveDefaultUser', str(self.Project.text()), os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'users.yml'))
        else:
            self.save_personal_settings(str(self.Name.text()), str(self.Project.text()), os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'users.yml'))

    def save_personal_settings(self, name, project, file, metadata=False):  # Save settings to users.yml file
        if metadata:
            users = {}
            users[name] = {}
            users[name][project] = self.current_settings
            users[name][project]['Measurement time'] = str(datetime.now())
            f = open(file, 'w')
            yaml.safe_dump(users, f)
            f.close()
            #message = 'Metadata saved for ' + project + ' by ' + name + ' to ' + file
            #self.Messages.append(message)
        else:
            f = open(file, 'r')
            users = yaml.safe_load(f)
            f.close()
            if not name in users:
                users[name] = {}
            users[name][project] = self.current_settings
            users['PreviousUser'] = {'Name': name, 'Project': project}
            f = open(file, 'w')
            yaml.safe_dump(users, f)
            f.close()
            #message = 'Settings saved for ' + project + ' by ' + name
            #self.Messages.append(message)

    def save_scandata(self, filename):
        f = open(filename, 'w')
        yaml.safe_dump(self.itp.scandata, f)
        f.close()

    def closeEvent(self, QCloseEvent): # Stop doing measurements and communication with device
        self.autosave_settings()
        self.itp.stop_device()
        self.itp.close_device()
        super(Pico5000Interface, self).closeEvent(QCloseEvent)
        QApplication.closeAllWindows()
        try:
            self.ditp.set_display('Connection Closed')
            self.ditp.close_connection()
        except:
            pass

    def change_fontsize(self): # Apply Fontsize
        self.current_settings['User']['Fontsize'] = int(self.Fontsize.text())
        font = self.centralwidget.font()
        font.setPointSize(int(self.Fontsize.text()))
        Lfont = self.centralwidget.font()
        Lfont.setPointSize(int(self.Fontsize.text())+8)
        self.centralwidget.setFont(font)
        #self.tabWidget.setFont(font)
        self.start_button.setFont(Lfont)
        self.pause_button.setFont(Lfont)
        self.stop_button.setFont(Lfont)
        self.continuously_button.setFont(Lfont)
        self.change_plot_fontsize()
        self.change_scan_plot_fontsize()
        self.autosave_settings()

    def change_plot_fontsize(self):
        try:
            self.plot_font.setPixelSize(int(self.Fontsize.text())+5) # Apply fontsize to plot
            self.plot_window.getAxis("left").tickFont = self.plot_font
            self.plot_window.getAxis("bottom").tickFont = self.plot_font
            self.plot_window.getAxis("left").setStyle(tickTextOffset=int(self.Fontsize.text()))
            self.plot_window.getAxis("bottom").setStyle(tickTextOffset=int(self.Fontsize.text()))
            fontStyle = {'color': '#999', 'font-size': '{}pt'.format(self.current_settings['User']['Fontsize'])}
            self.plot_window.setLabel('left', 'Voltage', units='V', **fontStyle)
            self.plot_window.setLabel('bottom', 'Time', units='s', **fontStyle)
            for window in self.windows:
                if self.current_settings['Analyse']['Windows'][window]['Show'] == 2:
                    pass
        except AttributeError:
            pass

    def change_scan_plot_fontsize(self):
        try:
            self.plot_font.setPixelSize(int(self.Fontsize.text())+5) # Apply fontsize to plot
            self.scan_plot_window.getAxis("left").tickFont = self.plot_font
            self.scan_plot_window.getAxis("bottom").tickFont = self.plot_font
            self.scan_plot_window.getAxis("left").setStyle(tickTextOffset=int(self.Fontsize.text()))
            self.scan_plot_window.getAxis("bottom").setStyle(tickTextOffset=int(self.Fontsize.text()))
            fontStyle = {'color': '#999', 'font-size': '{}pt'.format(self.current_settings['User']['Fontsize'])}
            self.scan_plot_window.setLabel('left', 'Calculator', units='V', **fontStyle)
            if 'Delay ' in self.current_settings['Analyse']['ScanLabel'] and self.current_settings['Delay']['Active'] > 0:
                self.scan_plot_window.setLabel('bottom', self.current_settings['Analyse']['ScanLabel'], units = 's', **fontStyle)
            else:
                self.scan_plot_window.setLabel('bottom', self.current_settings['Analyse']['ScanLabel'], **fontStyle)
        except AttributeError:
            pass

    def change_resolution(self):
        NumberOfActiveChannels = 0
        for i in self.channels:
            if self.current_settings['Channels'][i]['Active'] == 2:
                NumberOfActiveChannels += 1
        if str(self.Resolution.currentText()) in '8BIT' and NumberOfActiveChannels > 1 and self.current_settings['Time']['Timebase'] == 0:
            self.Messages.append('Lower number of active channels or raise timestepsize for 8BIT resolution')
            self.Resolution.setCurrentText(str(self.current_settings['Time']['Resolution']))
        elif str(self.Resolution.currentText()) in '12BIT' and NumberOfActiveChannels > 1 and self.current_settings['Time']['Timebase'] == 1:
            self.Messages.append('Lower number of active channels or raise timestepsize for 12BIT resolution')
            self.Resolution.setCurrentText(str(self.current_settings['Time']['Resolution']))
        elif str(self.Resolution.currentText()) in '15BIT' and NumberOfActiveChannels > 2:
            self.Messages.append('Lower number of active channels for 15BIT resolution')
            self.Resolution.setCurrentText(str(self.current_settings['Time']['Resolution']))
        elif str(self.Resolution.currentText()) in '16BIT' and NumberOfActiveChannels > 1:
            self.Messages.append('Lower number of active channels for 16BIT resolution')
            self.Resolution.setCurrentText(str(self.current_settings['Time']['Resolution']))
        else:
            self.current_settings['Time']['Resolution'] = str(self.Resolution.currentText())
            self.calculate_timebase()
            self.resolution_changed = True
            if self.measurement_running:
                self.measurement_pause = True
                self.continue_after_setting = True
            self.autosave_settings()

    def change_samples(self):
        old_number_of_samples = self.current_settings['Time']['Samples']
        try:
            if int(self.Samples.text()) <= 1:
                self.Samples.setText(str(self.current_settings['Time']['Samples']))
                self.Messages.append('Samples must be larger than 1')
                return
            self.current_settings['Time']['Samples'] = int(self.Samples.text())
        except ValueError:
            self.Samples.setText(str(self.current_settings['Time']['Samples']))
            self.Messages.append('Samples must be an integer')
            return
        self.calculate_timebase()
        if self.current_settings['Trigger']['Position'] > self.current_settings['Time']['Samples']:
            self.TPosition.setText(str(int(self.current_settings['Trigger']['Position']*self.current_settings['Time']['Samples']/old_number_of_samples)))
        for window in self.windows:
            if int(self.current_settings['Analyse']['Windows'][window]['Start']) + int(self.current_settings['Analyse']['Windows'][window]['Length']) > int(self.current_settings['Time']['Samples']):
                self.WindowLength[window].setText(str(int(int(self.current_settings['Analyse']['Windows'][window]['Length']) * int(self.current_settings['Time']['Samples']) / int(old_number_of_samples))))
            if int(self.current_settings['Analyse']['Windows'][window]['Start']) > int(self.current_settings['Time']['Samples']):
                self.WindowStart[window].setText(str(int(int(self.current_settings['Analyse']['Windows'][window]['Start'])*int(self.current_settings['Time']['Samples'])/int(old_number_of_samples))))
        self.timewindow_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True
        self.autosave_settings()

    def change_blocklength(self):
        try:
            unitcheck = ur(str(self.Blocklength.text())).m_as('s')
            if unitcheck < 0:
                self.Blocklength.setText(str(self.current_settings['Time']['Blocklength']))
                self.Messages.append('Blocklength must be positive')
                return
            self.current_settings['Time']['Blocklength'] = str(self.Blocklength.text())
        except:
            self.Blocklength.setText(str(self.current_settings['Time']['Blocklength']))
            self.Messages.append('Blocklength must have time units')
            return
        self.calculate_timebase()
        self.timewindow_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True
        self.autosave_settings()

    def change_trigger_show(self):
        self.current_settings['Trigger']['Show'] = int(self.TShow.checkState())
        if self.current_settings['Trigger']['Show'] == 2:
            self.show_trigger()
            try:
                self.show_trigger(self.current_settings['Trigger']['Level'], self.current_settings['Trigger']['Position'], measurement = True)
            except NameError:
                pass
        else:
            self.remove_trigger()
        try:
            self.close_plot_window()
            self.open_plot_window()
        except:
            pass
        self.autosave_settings()

    def change_trigger_active(self):
        self.current_settings['Trigger']['Active'] = int(self.TActive.checkState())
        self.trigger_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True
        self.autosave_settings()

    def change_trigger_channel(self):
        self.current_settings['Trigger']['Channel'] = str(self.TChannel.currentText())
        self.current_triggerlevel.setPen(pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']], style=Qt.DashLine, width=2))
        self.current_triggerposition.setPen(pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']], style=Qt.DashLine, width=2))
        self.current_triggerlevel.setHoverPen(pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']], width=2))
        self.current_triggerposition.setHoverPen(pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']], width=2))
        if self.current_settings['Trigger']['Channel'] in 'External':
            if ur(str(self.current_settings['Trigger']['Level'])).m_as('V') > 5:
                self.current_settings['Trigger']['Level'] = str(5) + ' V'
                self.change_trigger_level()
            elif ur(str(self.current_settings['Trigger']['Level'])).m_as('V') < -5:
                self.current_settings['Trigger']['Level'] = str(-5) + ' V'
                self.change_trigger_level()
        self.trigger_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True
        self.autosave_settings()

    def change_trigger_type(self):
        self.current_settings['Trigger']['Type'] = str(self.TType.currentText())
        self.trigger_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True
        self.autosave_settings()

    def change_trigger_level_drag(self):
        level = self.current_triggerlevel.value()
        if abs(level) < 1:
            self.current_settings['Trigger']['Level'] = str(round(level*1000, 2)) + ' mV'
        else:
            self.current_settings['Trigger']['Level'] = str(round(level, 2)) + ' V'
        if self.current_settings['Trigger']['Channel'] in 'External':
            if level > 5:
                self.current_settings['Trigger']['Level'] = str(5) + ' V'
                self.current_triggerlevel.setValue(5)
            elif level < -5:
                self.current_settings['Trigger']['Level'] = str(-5) + ' V'
                self.current_triggerlevel.setValue(-5)
        self.TLevel.setText(str(self.current_settings['Trigger']['Level']))
        self.trigger_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True
        self.autosave_settings()

    def change_trigger_level(self):
        try:
            unitcheck = ur(str(self.TLevel.text())).m_as('V')
            self.current_settings['Trigger']['Level'] = str(self.TLevel.text())
        except:
            self.TLevel.setText(str(self.current_settings['Trigger']['Level']))
            self.Messages.append('Trigger level must have voltage units')
            return
        if self.current_settings['Trigger']['Channel'] in 'External':
            if ur(str(self.TLevel.text())).m_as('V') > 5:
                self.TLevel.setText(str(5) + ' V')
            elif ur(str(self.TLevel.text())).m_as('V') < -5:
                self.TLevel.setText(str(-5) + ' V')
        self.current_settings['Trigger']['Level'] = str(self.TLevel.text())
        self.current_triggerlevel.setValue(ur(str(self.current_settings['Trigger']['Level']).replace(' ', '')).m_as('V'))
        self.trigger_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True
        self.autosave_settings()

    def change_trigger_delay(self):
        try:
            if int(self.TDelay.text()) < 0:
                self.TDelay.setText(str(self.current_settings['Trigger']['Delay']))
                self.Messages.append('Samples Delayed must be positive')
                return
            self.current_settings['Trigger']['Delay'] = int(self.TDelay.text())
        except ValueError:
            self.TDelay.setText(str(self.current_settings['Trigger']['Delay']))
            self.Messages.append('Samples Delayed must be an integer')
            return
        self.trigger_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True
        self.autosave_settings()

    def change_trigger_position_drag(self):
        self.current_settings['Trigger']['Position'] = int(round(self.current_triggerposition.value()/ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s')))
        self.TPosition.setText(str(self.current_settings['Trigger']['Position']))
        self.trigger_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True
        self.autosave_settings()

    def change_trigger_position(self):
        try:
            if abs(int(self.TPosition.text())) > int(self.current_settings['Time']['Samples']):
                self.TPosition.setText(str(self.current_settings['Trigger']['Position']))
                self.Messages.append('Sample Position must be less than Samples')
            if int(self.TPosition.text()) < 0:
                self.TPosition.setText(str(int(self.current_settings['Time']['Samples']) + int(self.TPosition.text())))
            self.current_settings['Trigger']['Position'] = int(self.TPosition.text())
        except ValueError:
            self.TPosition.setText(str(self.current_settings['Trigger']['Position']))
            self.Messages.append('Sample Position must be an integer')
            return
        self.current_triggerposition.setValue((self.current_settings['Trigger']['Position'])*ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'))
        self.trigger_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True
        self.autosave_settings()

    def change_trigger_auto(self):
        try:
            if self.Autotrigger.text() not in '0':
                unitcheck = ur(str(self.Autotrigger.text())).m_as('s')
                if unitcheck < 0:
                    self.Autotrigger.setText(str(self.current_settings['Trigger']['Auto']))
                    self.Messages.append('Autotrigger after must be positive')
                    return
                self.current_settings['Trigger']['Auto'] = str(self.Autotrigger.text())
        except:
            self.Autotrigger.setText(str(self.current_settings['Trigger']['Auto']))
            self.Messages.append('Autotrigger after must have time units')
            return
        if ur(self.current_settings['Trigger']['Auto'].replace(' ', '')).m_as('ms') < 1 and ur(self.current_settings['Trigger']['Auto'].replace(' ', '')).m_as('ms') is not 0:
            self.Messages.append('Autotrigger time can not be set less than 1 ms. To switch off the autotrigger set Autotrigger time to zero')
            self.current_settings['Trigger']['Auto'] = '1 ms'
            self.Autotrigger.setText('1 ms')
        else:
            self.current_settings['Trigger']['Auto'] = str(self.Autotrigger.text())
        self.trigger_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True
        self.autosave_settings()

    def change_channel_active(self, channel):
        self.current_settings['Channels'][channel]['Active'] = int(self.ChannelActive[channel].checkState())
        self.channel_changed[channel] = True
        self.buffer_changed[channel] = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True
        self.autosave_settings()

    def change_channel_range(self, channel):
        self.current_settings['Channels'][channel]['Range'] = str(self.ChannelRange[channel].currentText())
        self.channel_changed[channel] = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True
        self.autosave_settings()

    def change_channel_coupling(self, channel):
        self.current_settings['Channels'][channel]['Coupling'] = str(self.ChannelCoupling[channel].currentText())
        self.channel_changed[channel] = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True
        self.autosave_settings()

    def change_channel_name(self, channel):
        self.current_settings['Channels'][channel]['Name'] = str(self.ChannelName[channel].text())
        self.autosave_settings()

    def change_average_nom(self):
        try:
            if int(self.NumberOfMeasurements.text()) < 1:
                self.NumberOfMeasurements.setText(str(self.current_settings['Average']['Blocks']))
                self.Messages.append('Number of measurements must be positive')
                return
            self.current_settings['Average']['Blocks'] = int(self.NumberOfMeasurements.text())
        except ValueError:
            self.NumberOfMeasurements.setText(str(self.current_settings['Average']['Blocks']))
            self.Messages.append('Number of measurements must be an integer')
            return
        self.autosave_settings()

    def change_average_pause(self):
        try:
            unitcheck = ur(str(self.Pause.text())).m_as('s')
            if unitcheck < 0:
                self.Pause.setText(str(self.current_settings['Average']['Pause']))
                self.Messages.append('Time between measurements must be positive')
                return
            self.current_settings['Average']['Pause'] = str(self.Pause.text())
        except:
            self.Pause.setText(str(self.current_settings['Average']['Pause']))
            self.Messages.append('Time between measurements must have time units')
            return
        self.autosave_settings()

    def change_showplot(self):
        self.current_settings['Plot']['Show'] = int(self.ShowPlot.checkState())
        if self.current_settings['Plot']['Show'] == 2:
            self.open_plot_window()
            if self.current_settings['Trigger']['Active'] == 2:
                self.plot_window.addItem(self.current_triggerlevel)
                self.plot_window.addItem(self.current_triggerposition)
            for window in self.windows:
                if self.current_settings['Analyse']['Windows'][window]['Show'] == 2:
                    self.plot_window.addItem(self.window_start_draw[window])
                    self.plot_window.addItem(self.window_start_draw[window])
        else:
            self.close_plot_window()
            #self.layout.removeWidget(self.plot_window)
        self.autosave_settings()

    def change_importfile(self):
        self.current_settings['Metadata']['Importfile'] = str(self.Metadata_input.text())
        self.autosave_settings()

    def change_save_directory(self):
        self.current_settings['Save']['Folder'] = str(self.Directory.text())
        self.autosave_settings()

    def change_save_filename(self):
        self.current_settings['Save']['Filename'] = str(self.Filename.text())
        self.autosave_settings()

    def change_save_autosave(self):
        self.current_settings['Save']['Autosave'] = str(self.Autosave.currentText())
        self.autosave_settings()

    def change_analyse_active(self):
        self.current_settings['Analyse']['Active'] = int(self.AnalysisActive.checkState())
        if self.measurement_running:
            self.measurement_running =  False
            self.start_thread(self.continuously)
        self.autosave_settings()

    def change_analyse_showplot(self):
        self.current_settings['Analyse']['ShowPlot'] = int(self.ShowScanPlot.checkState())
        if self.current_settings['Analyse']['ShowPlot'] == 2:
            self.open_scan_plot_window()
            #self.scandatapoint = {}
        else:
            self.close_scan_plot_window()
        self.autosave_settings()

    #def change_analyse_calculate(self):
    #    self.current_settings['Analyse']['Calculate'] = str(self.AnalysisCalculate.currentText())
    #    self.autosave_settings()

    def change_analyse_scanvalue(self):
        try:
            if self.current_settings['Delay']['Active'] > 0 and 'Delay ' in self.current_settings['Analyse']['ScanLabel']:
                self.current_settings['Analyse']['ScanValue'] = float(ur(str(self.ScanValue.text())).m_as('s'))
            else:
                self.current_settings['Analyse']['ScanValue'] = float(self.ScanValue.text())
        except:
            self.ScanValue.setText(str(self.current_settings['Analyse']['ScanValue']))
            self.Messages.append('Invalid Scanpoint startvalue')
            return
        if self.current_settings['Analyse']['ShowPlot'] == 2:
            self.scan_plot_window.setXRange(float(self.current_settings['Analyse']['ScanValue']), float(self.current_settings['Analyse']['ScanValue'])+float(self.current_settings['Analyse']['ScanValueDifference'])*(int(self.current_settings['Analyse']['Scans'])-1))
        self.autosave_settings()

    def change_analyse_scanvaluedifference(self):
        try:
            if self.current_settings['Delay']['Active'] > 0 and 'Delay ' in self.current_settings['Analyse']['ScanLabel']:
                self.current_settings['Analyse']['ScanValueDifference'] = float(ur(str(self.ScanValueDifference.text())).m_as('s'))
            else:
                self.current_settings['Analyse']['ScanValueDifference'] = float(self.ScanValueDifference.text())
        except:
            self.ScanValueDifference.setText(str(self.current_settings['Analyse']['ScanValueDifference']))
            self.Messages.append('Invalid Scanpoint value difference')
            return
        if self.current_settings['Analyse']['ShowPlot'] == 2:
            self.scan_plot_window.setXRange(float(self.current_settings['Analyse']['ScanValue']), float(self.current_settings['Analyse']['ScanValue'])+float(self.current_settings['Analyse']['ScanValueDifference'])*(int(self.current_settings['Analyse']['Scans'])-1))
        self.autosave_settings()

    def change_analyse_scanlabel(self):
        self.current_settings['Analyse']['ScanLabel'] = str(self.ScanLabel.text())
        if self.current_settings['Delay']['Active'] > 2 and 'Delay ' in self.current_settings['Analyse']['ScanLabel']:
            self.ScanValue.setText(self.current_settings['Delay']['Connectors'][str(self.current_settings['Analyse']['ScanLabel'].replace('Delay ', ''))]['Delay'])
            self.current_settings['Analyse']['ScanValue'] = float(ur(str(self.current_settings['Delay']['Connectors'][str(self.current_settings['Analyse']['ScanLabel'].replace('Delay ', ''))]['Delay'])).m_as('s'))
            self.ScanValueDifference.setText(str(self.current_settings['Analyse']['ScanValueDifference']) + ' s')
            if self.current_settings['Analyse']['ShowPlot'] == 2:
                self.scan_plot_window.setLabel('bottom', self.current_settings['Analyse']['ScanLabel'], units = 's')
        else:
            if self.current_settings['Analyse']['ShowPlot'] == 2:
                self.scan_plot_window.setLabel('bottom', self.current_settings['Analyse']['ScanLabel'], units='')
        self.autosave_settings()

    def change_analyse_calculate(self):
        self.current_settings['Analyse']['Calculate'] = str(self.AnalysisCalculate.currentText())
        self.autosave_settings()

    def change_analyse_scans(self):
        try:
            if int(self.NumberOfScans.text()) < 1:
                self.NumberOfScans.setText(str(self.current_settings['Analyse']['Scans']))
                self.Messages.append('Number of scanpoints must be positive')
                return
            self.current_settings['Analyse']['Scans'] = int(self.NumberOfScans.text())
        except ValueError:
            self.NumberOfScans.setText(str(self.current_settings['Analyse']['Scans']))
            self.Messages.append('Number of scanpoints must be an integer')
            return
        if self.current_settings['Analyse']['ShowPlot'] == 2:
            self.scan_plot_window.setXRange(float(self.current_settings['Analyse']['ScanValue']), float(self.current_settings['Analyse']['ScanValue'])+float(self.current_settings['Analyse']['ScanValueDifference'])*(int(self.current_settings['Analyse']['Scans'])-1))
        self.autosave_settings()

    def change_analyse_pause(self):
        try:
            unitcheck = ur(str(self.ScanPause.text())).m_as('s')
            if unitcheck < 0:
                self.ScanPause.setText(str(self.current_settings['Analyse']['Pause']))
                self.Messages.append('Time between scanpoints must be positive')
                return
            self.current_settings['Analyse']['Pause'] = str(self.ScanPause.text())
        except:
            self.ScanPause.setText(str(self.current_settings['Analyse']['Pause']))
            self.Messages.append('Time between scanpoints must have time units')
            return
        self.autosave_settings()

    def change_window(self):
        if str(self.WindowSelect.currentText()) in 'Add Window':
            self.current_window = 3
            while self.current_window in self.windows:
                self.current_window += 1
            self.windows[self.current_window] = [self.current_window]
            self.current_settings['Analyse']['Windows'][self.current_window] = {}
            self.current_settings['Analyse']['Windows'][self.current_window]['Colour'] = [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)]
            self.current_settings['Analyse']['Windows'][self.current_window]['Start'] = str(self.WindowStart.text())
            self.current_settings['Analyse']['Windows'][self.current_window]['Length'] = str(self.WindowLength.text())
            self.window_start_draw[self.current_window] = pg.InfiniteLine(pos=(int(self.current_settings['Analyse']['Windows'][self.current_window]['Start'])) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'), angle=90, pen=pg.mkPen(color = tuple(self.current_settings['Analyse']['Windows'][self.current_window]['Colour']), style=Qt.DashLine, width=2), hoverPen=pg.mkPen(color = tuple(self.current_settings['Analyse']['Windows'][self.current_window]['Colour']), width=2), movable=True, bounds=[0, (int(self.current_settings['Analyse']['Windows'][self.current_window]['Start']) + int(self.current_settings['Analyse']['Windows'][self.current_window]['Length'])) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s')], name = 'Window ' + str(self.current_window))
            self.window_finish_draw[self.current_window] = pg.InfiniteLine(pos=(int(self.current_settings['Analyse']['Windows'][self.current_window]['Start']) + int(self.current_settings['Analyse']['Windows'][self.current_window]['Length'])) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'), angle=90, pen=pg.mkPen(color = tuple(self.current_settings['Analyse']['Windows'][self.current_window]['Colour']), style=Qt.DashLine, width=2), hoverPen=pg.mkPen(color = tuple(self.current_settings['Analyse']['Windows'][self.current_window]['Colour']), width=2), movable=True, bounds=[int(self.current_settings['Analyse']['Windows'][self.current_window]['Start']) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'), ur(str(self.current_settings['Time']['Blocklength']).replace(' ', '')).m_as('s')])
            self.change_window_show()
            self.change_window_channel()
            self.WindowSelect.addItem('Window {}'.format(self.current_window))
            self.FirstWindow.addItem('Window {}'.format(self.current_window))
            self.SecondWindow.addItem('Window {}'.format(self.current_window))
            self.WindowSelect.setCurrentText('Window {}'.format(self.current_window))
            self.window_start_draw[self.current_window].sigDragged.connect(partial(self.change_window_start_drag, self.current_window))
            self.window_finish_draw[self.current_window].sigDragged.connect(partial(self.change_window_finish_drag, self.current_window))
        else:
            self.current_window = int(str(self.WindowSelect.currentText()).replace('Window ', ''))
            self.WindowColour.setStyleSheet('background-color:rgb({}, {}, {})'.format(self.current_settings['Analyse']['Windows'][self.current_window]['Colour'][0], self.current_settings['Analyse']['Windows'][self.current_window]['Colour'][1], self.current_settings['Analyse']['Windows'][self.current_window]['Colour'][2]))
            self.WindowShow.setCheckState(int(self.current_settings['Analyse']['Windows'][self.current_window]['Show']))
            self.WindowChannel.setCurrentText(str(self.current_settings['Analyse']['Windows'][self.current_window]['Channel']))
            self.WindowStart.setText(str(self.current_settings['Analyse']['Windows'][self.current_window]['Start']))
            self.WindowLength.setText(str(self.current_settings['Analyse']['Windows'][self.current_window]['Length']))
        self.autosave_settings()

    def delete_window(self):
        if self.current_window in [1 ,2]:
            self.Messages.append('Not permitted to delete Window 1 and Window 2')
        else:
            self.plot_window.removeItem(self.window_start_draw[self.current_window])
            self.plot_window.removeItem(self.window_finish_draw[self.current_window])
            self.windows.pop(self.current_window)
            self.current_settings['Analyse']['Windows'].pop(self.current_window)
            for calculator in self.calculators:
                if self.current_settings['Analyse']['Calculators'][calculator]['FirstWindow'] == self.current_window:
                    self.current_settings['Analyse']['Calculators'][calculator]['FirstWindow'] = 1
                    if calculator == self.current_calculator:
                        self.FirstWindow.setCurrentText('Window 1')
                    self.Messages.append('First window for Calculator {} set to Window 1'.format(calculator))
                if self.current_settings['Analyse']['Calculators'][calculator]['SecondWindow'] == self.current_window:
                    self.current_settings['Analyse']['Calculators'][calculator]['SecondWindow'] = 1
                    if calculator == self.current_calculator:
                        self.SecondWindow.setCurrentText('Window 1')
                    self.Messages.append('Second window for Calculator {} set to Window 1'.format(calculator))
            self.FirstWindow.removeItem(self.FirstWindow.findText('Window {}'.format(self.current_window)))
            self.SecondWindow.removeItem(self.SecondWindow.findText('Window {}'.format(self.current_window)))
            self.WindowSelect.removeItem(self.WindowSelect.findText('Window {}'.format(self.current_window)))
            self.WindowSelect.setCurrentText('Window 1')
            self.current_window = 1
        self.autosave_settings()

    def change_window_colour(self):
        self.current_settings['Analyse']['Windows'][self.current_window]['Colour'] = (QColorDialog.getColor()).getRgb()[:3]
        self.WindowColour.setStyleSheet('background-color:rgb({}, {}, {})'.format(self.current_settings['Analyse']['Windows'][self.current_window]['Colour'][0], self.current_settings['Analyse']['Windows'][self.current_window]['Colour'][1], self.current_settings['Analyse']['Windows'][self.current_window]['Colour'][2]))
        self.window_start_draw[self.current_window].setPen(pg.mkPen(color = tuple(self.current_settings['Analyse']['Windows'][self.current_window]['Colour']), style=Qt.DashLine, width=2))
        self.window_finish_draw[self.current_window].setPen(pg.mkPen(color = tuple(self.current_settings['Analyse']['Windows'][self.current_window]['Colour']), style=Qt.DashLine, width=2))
        self.window_start_draw[self.current_window].setHoverPen(pg.mkPen(color = tuple(self.current_settings['Analyse']['Windows'][self.current_window]['Colour']), width=2))
        self.window_finish_draw[self.current_window].setHoverPen(pg.mkPen(color = tuple(self.current_settings['Analyse']['Windows'][self.current_window]['Colour']), width=2))
        self.autosave_settings()

    def change_window_show(self):
        self.current_settings['Analyse']['Windows'][self.current_window]['Show'] = int(self.WindowShow.checkState())
        if self.current_settings['Analyse']['Windows'][self.current_window]['Show'] == 2:
            self.plot_window.addItem(self.window_start_draw[self.current_window])
            self.plot_window.addItem(self.window_finish_draw[self.current_window])
        else:
            self.plot_window.removeItem(self.window_start_draw[self.current_window])
            self.plot_window.removeItem(self.window_finish_draw[self.current_window])
        self.autosave_settings()

    def change_window_channel(self):
        self.current_settings['Analyse']['Windows'][self.current_window]['Channel'] = str(self.WindowChannel.currentText())
        self.autosave_settings()

    #def change_window_window(self, window):
    #    self.current_settings['Analyse']['Windows'][window]['Window'] = str(self.WindowWindow[window].currentText())
    #    self.autosave_settings()

    def change_window_start_drag(self, window):
        self.WindowSelect.setCurrentText('Window {}'.format(window))
        self.change_window()
        # print(self.current_settings['Time']['Timestep'])
        # print(ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'))
        self.current_settings['Analyse']['Windows'][window]['Start'] = int(round(self.window_start_draw[window].value()/ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s')))
        self.current_settings['Analyse']['Windows'][window]['Length'] = int(round(self.window_finish_draw[window].value()/ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'))-int(self.current_settings['Analyse']['Windows'][window]['Start']))
        if window == self.current_window:
            self.WindowStart.setText(str(self.current_settings['Analyse']['Windows'][window]['Start']))
            self.WindowLength.setText(str(self.current_settings['Analyse']['Windows'][window]['Length']))
        self.window_start_draw[window].setBounds([0, int(self.current_settings['Analyse']['Windows'][window]['Start'] + self.current_settings['Analyse']['Windows'][window]['Length']) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s')])
        self.window_finish_draw[window].setBounds([int(self.current_settings['Analyse']['Windows'][window]['Start']) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'), ur(str(self.current_settings['Time']['Blocklength']).replace(' ', '')).m_as('s')])
        self.autosave_settings()

    def change_window_start(self):
        try:
            if int(str(self.WindowStart.text())) < 0:
                self.WindowStart.setText(str(self.current_settings['Analyse']['Windows'][self.current_window]['Start']))
                self.Messages.append('Window start must be positive')
                return
            if int(str(self.WindowStart.text())) + int(self.current_settings['Analyse']['Windows'][self.current_window]['Length']) > int(self.current_settings['Time']['Samples'])-1:
                self.WindowStart.setText(str(self.current_settings['Analyse']['Windows'][self.current_window]['Start']))
                self.Messages.append('Window start too high')
                return
            self.current_settings['Analyse']['Windows'][self.current_window]['Start'] = str(self.WindowStart.text())
        except ValueError:
            self.WindowStart.setText(str(self.current_settings['Analyse']['Windows'][self.current_window]['Start']))
            self.Messages.append('Window start must be an integer')
            return
        self.window_start_draw[self.current_window].setBounds([0, (int(self.current_settings['Analyse']['Windows'][self.current_window]['Start']) + int(self.current_settings['Analyse']['Windows'][self.current_window]['Length'])) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s')])
        self.window_finish_draw[self.current_window].setBounds([int(self.current_settings['Analyse']['Windows'][self.current_window]['Start']) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'), ur(str(self.current_settings['Time']['Blocklength']).replace(' ', '')).m_as('s')])
        self.window_finish_draw[self.current_window].setValue((int(self.current_settings['Analyse']['Windows'][self.current_window]['Start']) + int(self.current_settings['Analyse']['Windows'][self.current_window]['Length']))*ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'))
        self.window_start_draw[self.current_window].setValue(int(self.current_settings['Analyse']['Windows'][self.current_window]['Start'])*ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'))
        self.autosave_settings()

    def change_window_finish_drag(self, window):
        self.WindowSelect.setCurrentText('Window {}'.format(window))
        self.change_window()
        self.current_settings['Analyse']['Windows'][window]['Length'] = int(round(self.window_finish_draw[window].value()/ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'))-int(self.current_settings['Analyse']['Windows'][window]['Start']))
        if window == self.current_window:
            self.WindowLength.setText(str(self.current_settings['Analyse']['Windows'][window]['Length']))
        self.window_start_draw[window].setBounds([0, (int(self.current_settings['Analyse']['Windows'][window]['Start']) + int(self.current_settings['Analyse']['Windows'][window]['Length'])) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s')])
        self.autosave_settings()

    def change_window_length(self):
        try:
            if int(str(self.WindowLength.text())) < 0:
                self.WindowLength.setText(str(self.current_settings['Analyse']['Windows'][self.current_window]['Length']))
                self.Messages.append('Window length must be positive')
                return
            if int(str(self.WindowStart.text())) + int(self.current_settings['Analyse']['Windows'][self.current_window]['Start']) > int(self.current_settings['Time']['Samples'])-1:
                self.WindowLength.setText(str(self.current_settings['Analyse']['Windows'][self.current_window]['Length']))
                self.Messages.append('Window length too high')
                return
            self.current_settings['Analyse']['Windows'][self.current_window]['Length'] = str(self.WindowLength.text())
        except ValueError:
            self.WindowLength.setText(str(self.current_settings['Analyse']['Windows'][self.current_window]['Length']))
            self.Messages.append('Window length must be an integer')
            return
        self.window_finish_draw[self.current_window].setValue((int(self.current_settings['Analyse']['Windows'][self.current_window]['Start']) + int(self.current_settings['Analyse']['Windows'][self.current_window]['Length']))*ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'))
        self.window_start_draw[self.current_window].setBounds([0, (int(self.current_settings['Analyse']['Windows'][self.current_window]['Start']) + int(self.current_settings['Analyse']['Windows'][self.current_window]['Length'])) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s')])
        self.autosave_settings()

    def change_calculator(self):
        if str(self.CalculatorSelect.currentText()) in 'Add Calculator':
            self.current_calculator = 2
            while self.current_calculator in self.calculators:
                self.current_calculator += 1
            self.calculators[self.current_calculator] = [self.current_calculator]
            self.current_settings['Analyse']['Calculators'][self.current_calculator] = {}
            self.change_calculator_show()
            self.change_first_window()
            self.change_operation()
            self.change_second_window()
            self.current_settings['Analyse']['Calculators'][self.current_calculator]['Colour'] = [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)]
            self.current_settings['Analyse']['Calculators'][self.current_calculator]['Name'] = 'Calculator ' + str(self.current_calculator)
            self.CalculatorSelect.addItem('Calculator {}'.format(self.current_calculator))
            self.CalculatorSelect.setCurrentText('Calculator {}'.format(self.current_calculator))
        else:
            self.current_calculator = int(str(self.CalculatorSelect.currentText()).replace('Calculator ', ''))
            self.CalculatorColour.setStyleSheet('background-color:rgb({}, {}, {})'.format(self.current_settings['Analyse']['Calculators'][self.current_calculator]['Colour'][0], self.current_settings['Analyse']['Calculators'][self.current_calculator]['Colour'][1], self.current_settings['Analyse']['Calculators'][self.current_calculator]['Colour'][2]))
            self.CalculatorShow.setCheckState(int(self.current_settings['Analyse']['Calculators'][self.current_calculator]['Show']))
            self.FirstWindow.setCurrentText('Window ' + str(self.current_settings['Analyse']['Calculators'][self.current_calculator]['FirstWindow']))
            self.Operation.setCurrentText(str(self.current_settings['Analyse']['Calculators'][self.current_calculator]['Operation']))
            self.SecondWindow.setCurrentText('Window ' + str(self.current_settings['Analyse']['Calculators'][self.current_calculator]['SecondWindow']))
            self.CalculatorName.setText(self.current_settings['Analyse']['Calculators'][self.current_calculator]['Name'])
        self.autosave_settings()

    def change_calculator_colour(self):
        self.current_settings['Analyse']['Calculators'][self.current_calculator]['Colour'] = (QColorDialog.getColor()).getRgb()[:3]
        self.CalculatorColour.setStyleSheet('background-color:rgb({}, {}, {})'.format(self.current_settings['Analyse']['Calculators'][self.current_calculator]['Colour'][0], self.current_settings['Analyse']['Calculators'][self.current_calculator]['Colour'][1], self.current_settings['Analyse']['Calculators'][self.current_calculator]['Colour'][2]))
        self.autosave_settings()

    def change_calculator_show(self):
        self.current_settings['Analyse']['Calculators'][self.current_calculator]['Show'] = int(self.CalculatorShow.checkState())
        self.autosave_settings()

    def change_first_window(self):
        self.current_settings['Analyse']['Calculators'][self.current_calculator]['FirstWindow'] = int(str(self.FirstWindow.currentText()).replace('Window ', ''))
        self.autosave_settings()

    def change_operation(self):
        self.current_settings['Analyse']['Calculators'][self.current_calculator]['Operation'] = str(self.Operation.currentText())
        self.autosave_settings()

    def change_second_window(self):
        self.current_settings['Analyse']['Calculators'][self.current_calculator]['SecondWindow'] = int(str(self.SecondWindow.currentText()).replace('Window ', ''))
        self.autosave_settings()

    def change_calculator_name(self):
        self.current_settings['Analyse']['Calculators'][self.current_calculator]['Name'] = str(self.CalculatorName.text())
        self.autosave_settings()

    def delete_calculator(self):
        if self.current_calculator == 1:
            self.Messages.append('Not permitted to delete Calculator 1')
        else:
            self.calculators.pop(self.current_calculator)
            self.current_settings['Analyse']['Calculators'].pop(self.current_calculator)
            self.CalculatorSelect.removeItem(self.CalculatorSelect.findText('Calculator {}'.format(self.current_calculator)))
            self.CalculatorSelect.setCurrentText('Calculator 1')
            self.current_calculator = 1
        self.autosave_settings()

    # Delay generator
    def open_delay_connection_window(self):
        self.tabWidget.addTab(self.DelayTab, "Delay")
        self.tabWidget.setCurrentIndex(self.tabWidget.indexOf(self.DelayTab))
        #uic.loadUi(os.path.join(self.base_folder, 'delay_connect.ui'), self)
        self.confirm = QDialog()
        #self.confirm.setFixedSize(500, 75)
        self.confirm.setWindowTitle('Delay Generator Connector')
        self.confirm.setWindowIcon(QIcon(os.path.join(self.base_folder, 'icon.png')))
        self.confirm.setWindowFlags(Qt.WindowTitleHint)

        font = self.confirm.font()
        font.setPointSize(int(self.current_settings['User']['Fontsize']))
        self.confirm.setFont(font)

        self.delay_confirm_portL = QLabel('Port:', self)
        self.delay_confirm_port = QLineEdit(self)
        self.delay_confirm_port.setText(str(self.current_settings['Delay']['Port']))
        self.hbox = QHBoxLayout()
        self.hbox.addWidget(self.delay_confirm_portL)
        self.hbox.addWidget(self.delay_confirm_port)

        self.vbox = QVBoxLayout()
        #self.delay_confirm_question = QLabel('How do you want to connect the Delay Generator?', self)
        #self.vbox.addWidget(self.delay_confirm_question)
        self.vbox.addLayout(self.hbox)


        self.hbox2 = QHBoxLayout()
        self.delay_confirm_connect = QPushButton('Connect (Keep device settings)', self)
        self.delay_confirm_connect_and_control = QPushButton('Connect and control (Apply interface settings)', self)
        self.delay_confirm_cancel = QPushButton('Cancel', self)
        self.hbox2.addWidget(self.delay_confirm_connect)
        self.hbox2.addWidget(self.delay_confirm_connect_and_control)
        self.hbox2.addWidget(self.delay_confirm_cancel)

        self.vbox2 = QVBoxLayout()
        self.vbox2.addLayout(self.hbox2)

        self.vbox.addLayout(self.vbox2)

        self.confirm.setLayout(self.vbox)

        self.confirm.show()

        self.delay_confirm_connect.clicked.connect(self.connect_delay_generator)
        self.delay_confirm_connect_and_control.clicked.connect(self.connect_and_control_delay_generator)
        self.delay_confirm_cancel.clicked.connect(self.cancel_delay_generator)
        self.delay_confirm_port.editingFinished.connect(self.delay_change_port)

        self.autosave_settings()

    def cancel_delay_generator(self):
        if self.current_settings['Delay']['Active'] < 2:
            self.tabWidget.removeTab(self.tabWidget.indexOf(self.DelayTab))
        self.confirm.close()
        self.autosave_settings()

    def connect_delay_generator(self):
        self.tabWidget.removeTab(self.tabWidget.indexOf(self.DelayTab))
        self.ditp = SRSDG535Interpreter()
        self.ditp.start_control()
        try:
            self.ditp.setup_connection(self.current_settings['Delay']['Port'])
            self.ditp.set_display('Remote Access Mode')
            self.Messages.append('Connected to Delay Generator via ' + self.current_settings['Delay']['Port'])
            self.current_settings['Delay']['Active'] = 1
        except:
            self.Messages.append('Delay Generator not responding, check the connection and port')
            self.current_settings['Delay']['Active'] = 0
        self.confirm.close()
        self.autosave_settings()

    def connect_and_control_delay_generator(self):
        self.ditp = SRSDG535Interpreter()
        self.ditp.start_control()
        try:
            self.ditp.setup_connection(self.current_settings['Delay']['Port'])
            self.ditp.set_display('Remote Control Mode')
            for connector in self.connectors:
                if connector not in 'Ext':
                    self.ditp.set_output_mode(connector, str(self.current_settings['Delay']['Type']))
                    self.ditp.set_termination_impedance(connector, str(self.current_settings['Delay']['Load']))
            self.ditp.set_trigger_mode(self.current_settings['Delay']['TriggerMode'])
            if self.current_settings['Delay']['TriggerMode'] in 'Internal':
                self.ditp.set_int_trigger_rate(str(self.current_settings['Delay']['TriggerRate']))
            else:
                self.ditp.set_ext_trigger_impedance(str(self.current_settings['Delay']['TriggerLoad']))
                self.ditp.set_ext_trigger_slope(str(self.current_settings['Delay']['TriggerEdge']))
                self.ditp.set_ext_trigger_level(str(self.current_settings['Delay']['TriggerLevel']))
            for connector in self.primary_connectors:
                self.ditp.set_delay_time(connector, str(self.current_settings['Delay']['Connectors'][connector]['From']), str(self.current_settings['Delay']['Connectors'][connector]['Delay']))
            self.Messages.append('Connected to Delay Generator via ' + self.current_settings['Delay']['Port'] + ' and applied interface settings')
            self.current_settings['Delay']['Active'] = 2
        except:
            self.Messages.append('Delay Generator not responding, check the connection and port')
            self.current_settings['Delay']['Active'] = 1
            self.tabWidget.removeTab(self.tabWidget.indexOf(self.DelayTab))
        self.confirm.close()
        self.autosave_settings()

    def disconnect_delay_generator(self):
        try:
            self.ditp.set_display('Connection Closed')
            self.ditp.close_connection()
            self.Messages.append('Disconnected Delay Generator')
        except:
            pass
        self.tabWidget.removeTab(self.tabWidget.indexOf(self.DelayTab))
        self.autosave_settings()

    def delay_change_port(self):
        self.current_settings['Delay']['Port'] = str(self.delay_confirm_port.text())
        self.autosave_settings()

    def delay_change_signal(self):
        self.current_settings['Delay']['Type'] = str(self.Delay_signal_type.currentText())
        if self.current_settings['Delay']['Active'] > 0:
            for connector in self.connectors:
                if connector not in 'Ext':
                    self.ditp.set_output_mode(connector, str(self.current_settings['Delay']['Type']))
        self.autosave_settings()

    def delay_change_load(self):
        self.current_settings['Delay']['Load'] = str(self.Delay_signal_load.currentText())
        if self.current_settings['Delay']['Active'] > 0:
            for connector in self.connectors:
                if connector not in 'Ext':
                    self.ditp.set_termination_impedance(connector, str(self.current_settings['Delay']['Load']))
        self.autosave_settings()

    def delay_change_trigger_mode(self, current):
        if current in 'Internal':
            self.current_settings['Delay']['TriggerMode'] = 'External'
            self.Delay_Ext_trigger_mode.setCurrentText('External')
            self.TriggerExt.show()
            self.TriggerInt.hide()
            if self.current_settings['Delay']['Active'] > 0:
                self.ditp.set_trigger_mode(self.current_settings['Delay']['TriggerMode'])
                self.ditp.set_ext_trigger_impedance(str(self.current_settings['Delay']['TriggerLoad']))
                self.ditp.set_ext_trigger_slope(str(self.current_settings['Delay']['TriggerEdge']))
                self.ditp.set_ext_trigger_level(str(self.current_settings['Delay']['TriggerLevel']))
        else:
            self.current_settings['Delay']['TriggerMode'] = 'Internal'
            self.Delay_Int_trigger_mode.setCurrentText('Internal')
            self.TriggerInt.show()
            self.TriggerExt.hide()
            if self.current_settings['Delay']['Active'] > 0:
                self.ditp.set_trigger_mode(self.current_settings['Delay']['TriggerMode'])
                self.ditp.set_int_trigger_rate(str(self.current_settings['Delay']['TriggerRate']))
        self.autosave_settings()

    def delay_change_trigger_load(self):
        self.current_settings['Delay']['TriggerLoad'] = str(self.Delay_trigger_load.currentText())
        if self.current_settings['Delay']['Active'] > 0:
            self.ditp.set_ext_trigger_impedance(str(self.current_settings['Delay']['TriggerLoad']))
        self.autosave_settings()

    def delay_change_trigger_edge(self):
        self.current_settings['Delay']['TriggerEdge'] = str(self.Delay_trigger_edge.currentText())
        if self.current_settings['Delay']['Active'] > 0:
            self.ditp.set_ext_trigger_slope(str(self.current_settings['Delay']['TriggerEdge']))
        self.autosave_settings()

    def delay_change_trigger_level(self):
        try:
            unitcheck = ur(str(self.Delay_trigger_rate.text())).m_as('V')
            self.current_settings['Delay']['TriggerLevel'] = str(self.Delay_trigger_level.text())
        except:
            self.Delay_trigger_level.setText(str(self.current_settings['Delay']['TriggerLevel']))
            self.Messages.append('Trigger level must have voltage units')
            return
        if self.current_settings['Delay']['Active'] > 0:
            self.ditp.set_ext_trigger_level(str(self.current_settings['Delay']['TriggerLevel']))
        self.autosave_settings()

    def delay_change_trigger_rate(self):
        try:
            unitcheck = ur(str(self.Delay_trigger_rate.text())).m_as('Hz')
            if unitcheck < 0:
                self.Delay_trigger_rate.setText(str(self.current_settings['Delay']['TriggerRate']))
                self.Messages.append('Trigger rate must be positive')
                return
            self.current_settings['Delay']['TriggerRate'] = str(self.Delay_trigger_rate.text())
        except:
            self.Delay_trigger_rate.setText(str(self.current_settings['Delay']['TriggerRate']))
            self.Messages.append('Trigger rate must have frequency units')
            return
        if self.current_settings['Delay']['Active'] > 0:
            self.ditp.set_int_trigger_rate(str(self.current_settings['Delay']['TriggerRate']))
        self.autosave_settings()

    def delay_change_delay(self, connector):
        try:
            unitcheck = ur(str(self.self.Delay[connector].text())).m_as('s')
            if unitcheck < 0:
                self.self.Delay[connector].setText(str(self.current_settings['Delay']['Connectors'][connector]['Delay']))
                self.Messages.append('Trigger rate must be positive')
                return
            self.current_settings['Delay']['Connectors'][connector]['Delay'] = str(self.Delay[connector].text())
        except:
            self.self.Delay[connector].setText(str(self.current_settings['Delay']['Connectors'][connector]['Delay']))
            self.Messages.append('Delay must have time units')
            return
        self.current_settings['Delay']['Connectors'][connector]['Delay'] = str(self.Delay[connector].text())
        if self.current_settings['Delay']['Active'] > 0:
            self.ditp.set_delay_time(connector, str(self.current_settings['Delay']['Connectors'][connector]['From']), str(self.current_settings['Delay']['Connectors'][connector]['Delay']))
        self.autosave_settings()

    def delay_change_from(self, connector):
        self.current_settings['Delay']['Connectors'][connector]['From'] = str(self.From[connector].currentText())
        if self.current_settings['Delay']['Active'] > 0:
            self.ditp.set_delay_time(connector, str(self.current_settings['Delay']['Connectors'][connector]['From']), str(self.current_settings['Delay']['Connectors'][connector]['Delay']))
        self.autosave_settings()

