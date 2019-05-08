from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5 import uic
from PyQt5.QtCore import QTimer, pyqtSlot, Qt
from PyQt5.QtGui import QIcon
# from controller.picocontrol import Pico5000Controller
import threading
import time
import pyqtgraph as pg
import pyqtgraph.exporters
import os
import yaml
from time import sleep, time
from functools import partial
from pint import UnitRegistry
ur = UnitRegistry()



class Pico5000Interface(QMainWindow):
    def __init__(self, interpreter):
        super(Pico5000Interface, self).__init__(parent=None)  # Adopt QMainWindow as parent
        self.base_folder = os.path.dirname(__file__)
        main_window_file = os.path.join(self.base_folder, 'main_window.ui')
        uic.loadUi(main_window_file, self)

        self.itp = interpreter # Start interpreter

        self.setWindowTitle("Picoscope5000 MainWindow")
        self.setWindowIcon(QIcon(os.path.join(self.base_folder, 'icon.png')))

        # Shorter definition of buttons
        self.ChannelActive = {'A': self.AActive, 'B': self.BActive, 'C': self.CActive, 'D': self.DActive}
        self.ChannelRange = {'A': self.ARange, 'B': self.BRange, 'C': self.CRange, 'D': self.DRange}
        self.ChannelCoupling = {'A': self.ACoupling, 'B': self.BCoupling, 'C': self.CCoupling, 'D': self.DCoupling}
        self.WindowActive = {'I': self.ActiveWI, 'II': self.ActiveWII}
        self.WindowChannel = {'I': self.ChannelWI, 'II': self.ChannelWII}
        self.WindowStart = {'I': self.StartWI, 'II': self.StartWII}
        self.WindowLength = {'I': self.LengthWI, 'II': self.LengthWII}

        # Define initial parameters
        self.channel_changed = {}
        self.buffer_changed = {}
        self.first_timebase = True
        self.measurement_running = False
        self.measurement_pause = True
        self.continue_after_setting = True
        self.confirm_overwrite_personal = False
        self.channel_colour = {'A': 'b', 'B': 'r', 'C': 'g', 'D': 'y', 'External': 'k'}
        self.window_colour = {'I': 'c', 'II': 'm'}
        self.channels = ['A', 'B'] #, 'C', 'D']
        self.windows = ['I', 'II']
        self.load_personal_settings('DefaultUser', 'DefaultProject') # Set settings to Default
        self.device_channels = 4
        #self.two_channels()
            # Plotparameters and objects
        self.current_triggerlevel = pg.InfiniteLine(pos=ur(str(self.current_settings['Trigger']['Level']).replace(' ', '')).m_as('V'), angle=0, pen=pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']], style=Qt.DashLine), hoverPen=pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']]), movable=True, name='current_triggerlevel')
        self.current_triggerposition = pg.InfiniteLine(pos=(self.current_settings['Trigger']['Position']+1) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'), angle=90, pen=pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']], style=Qt.DashLine), hoverPen=pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']]), movable=True, name='current_triggerposition', bounds=[0, ur(str(self.current_settings['Time']['Blocklength']).replace(' ', '')).m_as('ns')])
        self.window_start_draw = {}
        self.window_finish_draw = {}
        for window in self.windows:
            self.window_start_draw[window] = pg.InfiniteLine(pos=(self.current_settings['Analyse']['Windows'][window]['Start']) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'), angle=90, pen=pg.mkPen(self.window_colour[window], style=Qt.DashLine), hoverPen=pg.mkPen(self.window_colour[window]), movable=True, bounds=[0, int(self.current_settings['Analyse']['Windows'][window]['Start'] + self.current_settings['Analyse']['Windows'][window]['Length']) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s')], label='Window ' + window + ' start')
            self.window_finish_draw[window] = pg.InfiniteLine(pos=(self.current_settings['Analyse']['Windows'][window]['Start'] + self.current_settings['Analyse']['Windows'][window]['Length']) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'), angle=90, pen=pg.mkPen(self.window_colour[window], style=Qt.DashLine), hoverPen=pg.mkPen(self.window_colour[window]), movable=True, bounds=[int(self.current_settings['Analyse']['Windows'][window]['Start']) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'), ur(str(self.current_settings['Time']['Blocklength']).replace(' ', '')).m_as('s')], label='Window ' + window + ' end')
        self.plot_font = pg.Qt.QtGui.QFont()
        self.change_fontsize()

        self.itp.start_device()
        self.itp.setup_device(self.current_settings['Time']['Resolution'])
        if self.itp.dev.status["openunit"] == 282 or self.itp.dev.status["openunit"] == 286:
            self.two_channels()

        # Do a first measurement
        self.start_thread()

        # Show start-up message
        self.Messages.setText('Welcome to the PicoScope5000 interface\nPlease consider logging on with your name and project\n')
        if self.itp.dev.status["openunit"] == 286:
            self.Messages.append('Connected to USB2, check for USB3 connection')
        elif self.itp.dev.status["openunit"] == 282:
            self.Messages.append('No external powersupply connected, when working with a PicoScope5444D check the plug and restart for four channel options')

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

            # Measurement tab
        self.NumberOfMeasurements.editingFinished.connect(self.change_average_nom)
        self.Pause.editingFinished.connect(self.change_average_pause)
        self.ShowPlot.stateChanged.connect(self.change_showplot)
        self.Save_plot_button.clicked.connect(self.save_plot_window)

            # Analysis tab
        self.AnalysisActive.stateChanged.connect(self.change_analyse_active)
        self.AnalysisCalculate.currentTextChanged.connect(self.change_analyse_calculate)
        self.NumberOfScans.editingFinished.connect(self.change_analyse_scans)
        self.ScanPause.editingFinished.connect(self.change_analyse_pause)
        for i in self.windows:
            self.WindowActive[i].stateChanged.connect(partial(self.change_window_active, i))
            self.WindowChannel[i].currentTextChanged.connect(partial(self.change_window_channel, i))
            # self.WindowCalculate[i].currentTextChanged.connect(partial(self.change_window_calculate, i))
            # self.WindowWindow[i].currentTextChanged.connect(partial(self.change_window_window, i))
            self.WindowStart[i].editingFinished.connect(partial(self.change_window_start, i))
            self.WindowLength[i].editingFinished.connect(partial(self.change_window_length, i))
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

# -------------------------------------------------------------------------------

    def two_channels(self):
        if self.device_channels == 4:
            self.current_settings['Channels']['C']['Active'] = 0
            self.current_settings['Channels']['D']['Active'] = 0
            if self.current_settings['Trigger']['Channel'] in ['C', 'D']:
                self.TChannel.setCurrentText('A')
            for window in self.windows:
                if self.current_settings['Analyse']['Windows'][window]['Channel'] in ['C', 'D']:
                    self.WindowChannel[window].setCurrentText('A')
                self.WindowChannel[window].removeItem(self.WindowChannel[window].findText('C'))
                self.WindowChannel[window].removeItem(self.WindowChannel[window].findText('D'))
            self.ChannelC.hide()
            self.ChannelD.hide()
            self.TChannel.removeItem(self.TChannel.findText('C'))
            self.TChannel.removeItem(self.TChannel.findText('D'))
            self.device_channels = 2
            self.channels = ['A', 'B']

    def four_channels(self):
        if self.device_channels == 2:
            if self.itp.dev.status["openunit"] == 282 or self.itp.dev.status["openunit"] == 286:
                self.Messages.append('Can not power four channels in USB power mode')
            else:
                self.ChannelC.show()
                self.ChannelD.show()
                for window in self.windows:
                    self.WindowChannel[window].addItem('C')
                    self.WindowChannel[window].addItem('D')
                self.TChannel.addItem('C')
                self.TChannel.addItem('D')
                self.device_channels = 4
                self.channels = ['A', 'B', 'C', 'D']

    def start_thread(self, continuously = False):
        if not self.measurement_running:
            self.timer = QTimer() # Start a timer to update the plot
            if self.current_settings['Analyse']['ShowPlot'] == 2:
                self.timer.timeout.connect(self.plot_scan)
            if self.current_settings['Plot']['Show'] == 2:
                self.timer.timeout.connect(self.plot_measurement)
            self.timer.start(500)  # Time in millieseconds
            #self.start_measurement()
            measurement_thread = threading.Thread(target = partial(self.start_measurement, continuously))
            measurement_thread.daemon = True
            measurement_thread.start()
        else:
            self.Messages.append('Measurement already running')

    def start_measurement(self, continuously):
        self.measurement_running = True
        self.continuously = continuously
        self.measurement_name = str(self.Name.text())
        self.measurement_project = str(self.Project.text())
        self.set_measurement_settings()
        self.block_too_slow = False
        scan_too_slow = False
        if not os.path.isdir(self.current_settings['Save']['Folder']):  # If there is no such folder create one
            os.makedirs(self.current_settings['Save']['Folder'])
        #self.Messages.append('Measurement started')
        if self.current_settings['Analyse']['Active']:
            self.itp.reset_scandata()
            self.scan_start_time = time()
            self.save_personal_settings(self.measurement_name, self.measurement_project, os.path.join(self.current_settings['Save']['Folder'], self.current_settings['Save']['Filename'] + '_' + str(self.scan_start_time).replace('.', '_') + '_metadata.yml'), metadata=True)
            if continuously:
                scans = 1000000
            else:
                scans = self.current_settings['Analyse']['Scans']
            for scan in range(scans):
                self.meaurement_start_time = time()
                self.run_measurement()
                if not self.measurement_running:
                    break
                else:
                    self.itp.read_windows([int(self.current_settings['Analyse']['Windows']['I']['Start']), int(self.current_settings['Analyse']['Windows']['II']['Start'])], [int(self.current_settings['Analyse']['Windows']['I']['Start']) + int(self.current_settings['Analyse']['Windows']['I']['Length']), int(self.current_settings['Analyse']['Windows']['II']['Start']) + int(self.current_settings['Analyse']['Windows']['II']['Length'])],[self.current_settings['Analyse']['Windows']['I']['Channel'], self.current_settings['Analyse']['Windows']['II']['Channel']] )
                    #print('Windows read after: ', time() - self.meaurement_start_time)
                    self.itp.compute_scanpoint(float(self.current_settings['Analyse']['ScanValue']) + int(scan)*float(self.current_settings['Analyse']['ScanValueDifference']), str(self.current_settings['Analyse']['Calculate']), [str(self.current_settings['Channels'][self.current_settings['Analyse']['Windows']['I']['Channel']]['Range']), str(self.current_settings['Channels'][self.current_settings['Analyse']['Windows']['II']['Channel']]['Range'])], int(self.current_settings['Time']['maxADC']))
                    #print('Scanpoint computed after: ', time() - self.meaurement_start_time)
                    self.save_scandata(os.path.join(self.current_settings['Save']['Folder'], self.current_settings['Save']['Filename'] + '_' + str(self.scan_start_time).replace('.', '_') + '_scan.yml'))
                    #print('Scandata saved after: ', time() - self.meaurement_start_time)
                    if scan < self.current_settings['Analyse']['Scans']-1 or continuously:
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
            for i in range(self.current_settings['Average']['Blocks']):
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
                        filename = os.path.join(self.current_settings['Save']['Folder'], self.current_settings['Save']['Filename'] + '_' + str(self.meaurement_start_time).replace('.', '_') + '_binary_' + str(i+1) + '.bin')
                        self.itp.save_binary(filename, self.active_channels)
                        message = 'Data saved for ' + self.measurement_project + ' by ' + self.measurement_name + ' to ' + filename
                        #self.Messages.append(message)
                    if i < self.current_settings['Average']['Blocks']-1:
                        delay = (i + 1)*ur(self.current_settings['Average']['Pause'].replace(' ', '')).m_as('s')
                        if time() - self.meaurement_start_time > delay:
                            if not self.block_too_slow:
                                self.Messages.append('Can not keep up with measurementrate, increase Time between measurements ({})'.format(str(round(time() - self.meaurement_start_time, 4)) + ' s'))
                                self.block_too_slow = True
                        else:
                            while time() - self.meaurement_start_time < delay:
                                pass
                    else:
                        self.itp.block_average(self.current_settings['Time']['Samples'], self.current_settings['Average']['Blocks'])
                        #print('Averaged over blocks after: ', time() - self.meaurement_start_time)
                        if self.current_settings['Save']['Autosave'] in 'Every scope average':
                            self.save_personal_settings(self.measurement_name, self.measurement_project, os.path.join(self.current_settings['Save']['Folder'], self.current_settings['Save']['Filename'] + '_' + str(self.meaurement_start_time).replace('.', '_') + '_metadata.yml'), metadata=True)
                            if self.current_settings['Save']['Autosave'] not in 'Every scope':
                                filename = os.path.join(self.current_settings['Save']['Folder'], self.current_settings['Save']['Filename'] + '_' + str(self.meaurement_start_time).replace('.','_') + '_binary.bin')
                                self.itp.save_binary(filename, self.active_channels, Average = True)
                                message = 'Data saved for ' + self.measurement_project + ' by ' + self.measurement_name + ' to ' + filename
                                #self.Messages.append(message)

    def plot_measurement(self):
        try:
            for channel in self.active_channels:
                self.itp.interpret_data(self.current_settings['Time']['Samples'], ur(str(self.current_settings['Time']['Timestep'])).m_as('ns'), channel, str(self.current_settings['Channels'][channel]['Range']))
            self.plot_data()
        except KeyError:
            pass

    def plot_scan(self):
        try:
            self.scan_plot_window.clear()
            self.scan_plot_window.plot(self.itp.scandata[0][:], self.itp.scandata[1][:], pen='b', symbol='s')
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
        exp = pg.exporters.ImageExporter(self.plot_window.plotItem)
        exp.params.param('width').setValue(int(self.plot_window.width()*3), blockSignal=exp.widthChanged)
        exp.params.param('height').setValue(int(self.plot_window.height()*3), blockSignal=exp.heightChanged)
        file = os.path.join(self.current_settings['Save']['Folder'], str(self.current_settings['Save']['Filename']) + '_' + str(self.meaurement_start_time).replace('.', '_') + '_scope.png')
        save_plot_thread = threading.Thread(target = exp.export(file))
        save_plot_thread.daemon = True
        save_plot_thread.start()
        #self.Messages.append('Scope plot saved to {}'. format(str(file)))

    def open_scan_plot_window(self):
        self.scan_plot_window = pg.plot(title='Picoscope5000 Scan', background='w')
        #self.scan_plot_window.setWindowIcon(QIcon(os.path.join(self.base_folder, 'icon.png')))
        self.scan_plot_window.showGrid(x=True, y=True)
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
            file = os.path.join(self.current_settings['Save']['Folder'], str(self.current_settings['Save']['Filename']) + '_' + str(self.scan_start_time).replace('.', '_') + '_scan.png')
            save_plot_thread = threading.Thread(target = exp.export(file))
            save_plot_thread.daemon = True
            save_plot_thread.start()
            #self.Messages.append('Scan plot saved to {}'. format(str(file)))
        except AttributeError:
            self.Messages.append('No scan plot available')

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
                    self.plot_window.plot([j/1000000000 for j in self.itp.block['Time']], [k/1000 for k in self.itp.block[i][:]], pen=self.channel_colour[i])
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
        #self.plot_window.removeItem(self.measurement_triggerlevel)
        #self.plot_window.removeItem(self.measurement_triggerposition)

    def calculate_timebase(self):
        NumberOfActiveChannels = 0
        for i in self.channels:
            if self.current_settings['Channels'][i]['Active'] == 2:
                NumberOfActiveChannels += 1
        Timebase_data = self.itp.calculate_timebase(NumberOfActiveChannels, self.current_settings['Time']['Resolution'], self.current_settings['Time']['Samples'], self.current_settings['Time']['Blocklength'])
        self.current_settings['Time']['Timebase'] = Timebase_data[0]
        self.current_settings['Time']['Timestep'] = str(Timebase_data[1])
        self.current_settings['Time']['Blocklength'] = str(Timebase_data[2])
        self.Timestep.setText(str(Timebase_data[1]))
        self.Blocklength.setText(Timebase_data[2])
        if Timebase_data[3]:
            self.Messages.append(str(Timebase_data[3]))
        if self.first_timebase:
            self.first_timebase = False
        else:
            self.change_trigger_position()
            for window in self.windows:
                self.change_window_start(window)
                self.change_window_length(window)

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
        users = yaml.load(f)
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
            self.AnalysisCalculate.setCurrentText(str(self.current_settings['Analyse']['Calculate']))
            self.ScanValue.setText(str(self.current_settings['Analyse']['ScanValue']))
            self.ScanValueDifference.setText(str(self.current_settings['Analyse']['ScanValueDifference']))
            self.ScanLabel.setText(str(self.current_settings['Analyse']['ScanLabel']))
            self.NumberOfScans.setText(str(self.current_settings['Analyse']['Scans']))
            self.ScanPause.setText(str(self.current_settings['Analyse']['Pause']))
            for i in self.windows:
                self.WindowActive[i].setCheckState(int(self.current_settings['Analyse']['Windows'][i]['Show']))
                self.WindowChannel[i].setCurrentText(str(self.current_settings['Analyse']['Windows'][i]['Channel']))
                #self.WindowCalculate[i].setCurrentText(str(self.current_settings['Analyse']['Windows'][i]['Calculate']))
                #self.WindowWindow[i].setCurrentText(str(self.current_settings['Analyse']['Windows'][i]['Window']))
                self.WindowStart[i].setText(str(self.current_settings['Analyse']['Windows'][i]['Start']))
                self.WindowLength[i].setText(str(self.current_settings['Analyse']['Windows'][i]['Length']))

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
                users = yaml.load(f)
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

    def save_personal_settings(self, name, project, file, metadata=False):  # Save settings to users.yml file
        if metadata:
            users = {}
            users[name] = {}
            users[name][project] = self.current_settings
            f = open(file, 'w')
            yaml.dump(users, f)
            f.close()
            #message = 'Metadata saved for ' + project + ' by ' + name + ' to ' + file
            #self.Messages.append(message)
        else:
            f = open(file, 'r')
            users = yaml.load(f)
            f.close()
            if not name in users:
                users[name] = {}
            users[name][project] = self.current_settings
            f = open(file, 'w')
            yaml.dump(users, f)
            f.close()
            #message = 'Settings saved for ' + project + ' by ' + name
            #self.Messages.append(message)

    def save_scandata(self, filename):
        f = open(filename, 'w')
        yaml.dump(self.itp.scandata, f)
        f.close()

    def closeEvent(self, QCloseEvent): # Stop doing measurements and communication with device
        self.itp.stop_device()
        self.itp.close_device()
        super(Pico5000Interface, self).closeEvent(QCloseEvent)
        QApplication.closeAllWindows()

    def change_fontsize(self): # Apply Fontsize
        self.current_settings['User']['Fontsize'] = self.Fontsize.text()
        font = self.centralwidget.font()
        font.setPointSize(int(self.Fontsize.text()))
        Lfont = self.centralwidget.font()
        Lfont.setPointSize(int(self.Fontsize.text())+8)
        self.centralwidget.setFont(font)
        self.start_button.setFont(Lfont)
        self.pause_button.setFont(Lfont)
        self.stop_button.setFont(Lfont)
        self.continuously_button.setFont(Lfont)
        self.change_plot_fontsize()
        self.change_scan_plot_fontsize()

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
            self.scan_plot_window.setLabel('left', 'Window average difference', units='V', **fontStyle)
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

    def change_samples(self):
        old_number_of_samples = self.current_settings['Time']['Samples']
        self.current_settings['Time']['Samples'] = int(self.Samples.text())
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

    def change_blocklength(self):
        self.current_settings['Time']['Blocklength'] = str(self.Blocklength.text())
        self.calculate_timebase()
        self.timewindow_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True

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

    def change_trigger_active(self):
        self.current_settings['Trigger']['Active'] = int(self.TActive.checkState())
        self.trigger_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True

    def change_trigger_channel(self):
        self.current_settings['Trigger']['Channel'] = str(self.TChannel.currentText())
        self.current_triggerlevel.setPen(pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']], style=Qt.DashLine))
        self.current_triggerposition.setPen(pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']], style=Qt.DashLine))
        self.current_triggerlevel.setHoverPen(pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']]))
        self.current_triggerposition.setHoverPen(pg.mkPen(self.channel_colour[self.current_settings['Trigger']['Channel']]))
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

    def change_trigger_type(self):
        self.current_settings['Trigger']['Type'] = str(self.TType.currentText())
        self.trigger_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True

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

    def change_trigger_level(self):
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

    def change_trigger_delay(self):
        self.current_settings['Trigger']['Delay'] = int(self.TDelay.text())
        self.trigger_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True

    def change_trigger_position_drag(self):
        self.current_settings['Trigger']['Position'] = int(round(self.current_triggerposition.value()/ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s')))
        self.TPosition.setText(str(self.current_settings['Trigger']['Position']))
        self.trigger_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True

    def change_trigger_position(self):
        self.current_settings['Trigger']['Position'] = int(self.TPosition.text())
        self.current_triggerposition.setValue((self.current_settings['Trigger']['Position'])*ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'))
        self.trigger_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True

    def change_trigger_auto(self):
        if ur(self.current_settings['Trigger']['Auto'].replace(' ', '')).m_as('ms') < 1 and ur(self.current_settings['Trigger']['Auto'].replace(' ', '')).m_as('ms') is not 0:
            self.Messages.append('Autotriggertime can not be set less than 1 ms. To switch off the autotrigger set time to zero')
            self.current_settings['Trigger']['Auto'] = '1 ms'
            self.Autotrigger.setText('1 ms')
        else:
            self.current_settings['Trigger']['Auto'] = str(self.Autotrigger.text())
        self.trigger_changed = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True

    def change_channel_active(self, channel):
        self.current_settings['Channels'][channel]['Active'] = int(self.ChannelActive[channel].checkState())
        self.channel_changed[channel] = True
        self.buffer_changed[channel] = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True

    def change_channel_range(self, channel):
        self.current_settings['Channels'][channel]['Range'] = str(self.ChannelRange[channel].currentText())
        self.channel_changed[channel] = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True

    def change_channel_coupling(self, channel):
        self.current_settings['Channels'][channel]['Coupling'] = str(self.ChannelCoupling[channel].currentText())
        self.channel_changed[channel] = True
        if self.measurement_running:
            self.measurement_pause = True
            self.continue_after_setting = True

    def change_average_nom(self):
        self.current_settings['Average']['Blocks'] = int(self.NumberOfMeasurements.text())

    def change_average_pause(self):
        self.current_settings['Average']['Pause'] = str(self.Pause.text())

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

    def change_importfile(self):
        self.current_settings['Metadata']['Importfile'] = str(self.Metadata_input.text())

    def change_save_directory(self):
        self.current_settings['Save']['Folder'] = str(self.Directory.text())

    def change_save_filename(self):
        self.current_settings['Save']['Filename'] = str(self.Filename.text())

    def change_save_autosave(self):
        self.current_settings['Save']['Autosave'] = str(self.Autosave.currentText())

    def change_analyse_active(self):
        self.current_settings['Analyse']['Active'] = int(self.AnalysisActive.checkState())
        if self.measurement_running:
            self.measurement_running =  False
            self.start_thread(self.continuously)

    def change_analyse_showplot(self):
        self.current_settings['Analyse']['ShowPlot'] = int(self.ShowScanPlot.checkState())
        if self.current_settings['Analyse']['ShowPlot'] == 2:
            self.open_scan_plot_window()
            #self.scandatapoint = {}
        else:
            self.close_scan_plot_window()

    def change_analyse_calculate(self):
        self.current_settings['Analyse']['Calculate'] = str(self.AnalysisCalculate.currentText())

    def change_analyse_scanvalue(self):
        self.current_settings['Analyse']['ScanValue'] = float(self.ScanValue.text())
        if self.current_settings['Analyse']['ShowPlot'] == 2:
            self.scan_plot_window.setXRange(float(self.current_settings['Analyse']['ScanValue']), float(self.current_settings['Analyse']['ScanValue'])+float(self.current_settings['Analyse']['ScanValueDifference'])*(int(self.current_settings['Analyse']['Scans'])-1))

    def change_analyse_scanvaluedifference(self):
        self.current_settings['Analyse']['ScanValueDifference'] = float(self.ScanValueDifference.text())
        if self.current_settings['Analyse']['ShowPlot'] == 2:
            self.scan_plot_window.setXRange(float(self.current_settings['Analyse']['ScanValue']), float(self.current_settings['Analyse']['ScanValue'])+float(self.current_settings['Analyse']['ScanValueDifference'])*(int(self.current_settings['Analyse']['Scans'])-1))

    def change_analyse_scanlabel(self):
        self.current_settings['Analyse']['ScanLabel'] = str(self.ScanLabel.text())
        if self.current_settings['Analyse']['ShowPlot'] == 2:
            self.analyse_plot_widget.setLabel('bottom', self.current_settings['Analyse']['ScanLabel'])

    def change_analyse_calculate(self):
        self.current_settings['Analyse']['Calculate'] = str(self.AnalysisCalculate.currentText())

    def change_analyse_scans(self):
        self.current_settings['Analyse']['Scans'] = int(self.NumberOfScans.text())
        if self.current_settings['Analyse']['ShowPlot'] == 2:
            self.scan_plot_window.setXRange(float(self.current_settings['Analyse']['ScanValue']), float(self.current_settings['Analyse']['ScanValue'])+float(self.current_settings['Analyse']['ScanValueDifference'])*(int(self.current_settings['Analyse']['Scans'])-1))

    def change_analyse_pause(self):
        self.current_settings['Analyse']['Pause'] = str(self.ScanPause.text())

    def change_window_active(self, window):
        self.current_settings['Analyse']['Windows'][window]['Show'] = int(self.WindowActive[window].checkState())
        if self.current_settings['Analyse']['Windows'][window]['Show'] == 2:
            self.plot_window.addItem(self.window_start_draw[window])
            self.plot_window.addItem(self.window_finish_draw[window])
        else:
            self.plot_window.removeItem(self.window_start_draw[window])
            self.plot_window.removeItem(self.window_finish_draw[window])

    def change_window_channel(self, window):
        self.current_settings['Analyse']['Windows'][window]['Channel'] = str(self.WindowChannel[window].currentText())

    #def change_window_window(self, window):
    #    self.current_settings['Analyse']['Windows'][window]['Window'] = str(self.WindowWindow[window].currentText())

    def change_window_start_drag(self, window):
        self.current_settings['Analyse']['Windows'][window]['Start'] = int(round(self.window_start_draw[window].value()/ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s')))
        self.WindowStart[window].setText(str(self.current_settings['Analyse']['Windows'][window]['Start']))
        self.current_settings['Analyse']['Windows'][window]['Length'] = int(round(self.window_finish_draw[window].value()/ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'))-int(self.current_settings['Analyse']['Windows'][window]['Start']))
        self.WindowLength[window].setText(str(self.current_settings['Analyse']['Windows'][window]['Length']))
        self.window_start_draw[window].setBounds([0, int(self.current_settings['Analyse']['Windows'][window]['Start'] + self.current_settings['Analyse']['Windows'][window]['Length']) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s')])
        self.window_finish_draw[window].setBounds([int(self.current_settings['Analyse']['Windows'][window]['Start']) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'), ur(str(self.current_settings['Time']['Blocklength']).replace(' ', '')).m_as('s')])

    def change_window_start(self, window):
        self.current_settings['Analyse']['Windows'][window]['Start'] = str(self.WindowStart[window].text())
        self.window_start_draw[window].setBounds([0, (int(self.current_settings['Analyse']['Windows'][window]['Start']) + int(self.current_settings['Analyse']['Windows'][window]['Length'])) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s')])
        self.window_finish_draw[window].setBounds([int(self.current_settings['Analyse']['Windows'][window]['Start']) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'), ur(str(self.current_settings['Time']['Blocklength']).replace(' ', '')).m_as('s')])
        self.window_finish_draw[window].setValue((int(self.current_settings['Analyse']['Windows'][window]['Start']) + int(self.current_settings['Analyse']['Windows'][window]['Length']))*ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'))
        self.window_start_draw[window].setValue(int(self.current_settings['Analyse']['Windows'][window]['Start'])*ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'))

    def change_window_finish_drag(self, window):
        self.current_settings['Analyse']['Windows'][window]['Length'] = int(round(self.window_finish_draw[window].value()/ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'))-int(self.current_settings['Analyse']['Windows'][window]['Start']))
        self.WindowLength[window].setText(str(self.current_settings['Analyse']['Windows'][window]['Length']))
        self.window_start_draw[window].setBounds([0, (int(self.current_settings['Analyse']['Windows'][window]['Start']) + int(self.current_settings['Analyse']['Windows'][window]['Length'])) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s')])

    def change_window_length(self, window):
        self.current_settings['Analyse']['Windows'][window]['Length'] = str(self.WindowLength[window].text())
        self.window_finish_draw[window].setValue((int(self.current_settings['Analyse']['Windows'][window]['Start']) + int(self.current_settings['Analyse']['Windows'][window]['Length']))*ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s'))
        self.window_start_draw[window].setBounds([0, (int(self.current_settings['Analyse']['Windows'][window]['Start']) + int(self.current_settings['Analyse']['Windows'][window]['Length'])) * ur(str(self.current_settings['Time']['Timestep']).replace(' ', '')).m_as('s')])
