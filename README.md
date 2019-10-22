# PicoScope5000 Software for reading out data and scanning

Welcome to the PicoScope5000 software developed for the NL-eEDM collaboration. This software has been developed for testing the performance of the Cryogenic source built at the Vrije Universiteit Amsterdam.

## How to get the software on Windows

1. Download [Python 3](https://www.python.org/downloads/windows/) and add it to PATH (option in installation menu or append manually).
2. Install pip if it is not included in the Python installation already.
3. Download [git](https://git-scm.com/download/win).
4. Make a directory in which you want to get the software.
5. Open a terminal (windows + R -> cmd) and navigate to the directory.
6. Download the software by cloning the directory
```
	git clone https://github.com/AnnoTouwen/PicoScope5000.git
```
7. Copy the picosdk directory to the python packages folder, which could be something like
```
	C:/Python/Lib/site-packages
```
8. Install the following Python packages using pip in the terminal
```
	pip install Pint PyYAML PyQt5 numpy Pyqtgraph Matplotlib PySerial
```

## How to get the latest update on Windows

1. Open a terminal (windows + R) and navigate to the directory.
2. Update the software by pulling it to the directory
```
	git pull
```

## How to implement the Stanford Research Systems Delay Generator DG535

1. Connect the Delay Generator via the Prologix GPIB-USB controller and USB cable.
2. Run the CDM21228_Setup.exe from PicoScope5000/drivers/GPIB-USB connector to install the drivers for the converter.
3. Open the Device Manager (start + search: Device Manager) to check the connection port (COM), COM3 is default, but if this port is already in use another is selected. The port can be changed manually. This port has to be selected in the PicoScope interface.

## How to use the PicoScope software

Run start.py by double clicking if Python 3 is set to be the standard for executing .py files.
Alternatively you could naviate to the directory in the terminal and run
```
	python start.py
```

If a PicoScope5000 device is connected a window with the user interface should appear. The powersupply is checked and the device is set accordingly. The Default settings are loaded from config/users.yml. Dependent on these settings a first readout of the scope is also show in a seraprate window. In the user interface messages to the user are dislayed, settings can be changed and measurements can be started. Realtime analysis and plots are shown in separate windows.

### Powersupply

If the device has four input channels and an external powersupply is connected four channel mode is selected. If the device is power through USB at most two channels can be used. The settings can be changed via the Device menu in the upperleft corner of the interface, but the powersupply is only reset by restarting the programm.

### User

If the programm is started for the first time Default settings are loaded, but it is suggested to login with your name and project, which you could fill in in the user menu. If the program is closed properly the settings are saved and relaoded in the next startup. Your personal settings can also be saved manulally and loaded using the buttons on the right. The settings from a previous measurement can also be loaded from the metadata. In this menu the fontsize can also be changed. Note that this also changes the fontsize of the plots in the other windows.

### Save

The save directory for all the data output from the program can be set here, in which a folder will be created named by the current date set on your PC as YYYY-MM-DD. Also the base filename can be set. Note however that the full filename will be different dependent on the datatype and the numbers labelling the measurement or scan. For binary data of the scope readout a separate folder is created in which files will be saved with the extension .bin. These binary files are numbered, with measurementnumber and possibly blocknumber if all readouts are saved separately, not just the avereage over multiple of these. Scanfiles have the extension .yml. These datafiles are accompanied by metadatafiles with the same filname, but with metadata added and extension .yml. The plots for the scope and scan can also be saved, which will have a filename including scope or scan respectively, with extension .png.

The scandata are saved automatically (autosave every minute and at the end of a scan), but you might want to save the raw binary data as well. Save data lets you select to never, every scopereadout or every average over mutiple scope readouts (if applicable) save the binary data. The datafiles can be read and used by the PicoReadBinary.py script.

### Time

In this menu the resolution and timeresolution can be set. The PicoScope5000 can measure at 8 to 16 bit resolution and up to a time resolution of 1 ns, but not all combinations. Also not all combinations can be used with every number of channels. To find out the combinations read picoscope-5000-series-a-api-programmers-guide.pdf about Timebase or try combinations and note the feedback messages in the interface.
The timeresolution is calculated from the measurementtime and the number of measurementpoints in this interval. Note that the timestep goes by powers of 2, not all timesteps are possible. The measurementlength is reset after the timestep has been determined.

The trigger is also set in this menu. If you want to measure without a trigger deactivate it by unticking the box. The triggerposition and level can be shown in the plot of the scope readout. If not fixed the trigger values can be changed by dragging the lines in the plot. Any of the active channels can be used as trigger, but note that the PicoScope5000 also has an external trigger. The triggertype determines whether the trigger is activated on a rising or falling pass through the trigger level. The trigger level and sample position in the timewindow can be set by filling in a value, bu also by dragging the trigger lines if shown in the scope plot. A delay can be set to the trigger, to make the trigger happen a number of samples after the level crossing. An autotrigger sets the time after which a trigger occurs even without a crossing of the trigger level. The autotrigger is switched off by setting it to 0.

### Channels

Each of the channels can be activated or deactivated separately. Note that the number of activated channels is restricted by the powermodus, resolution and timeresolution. Inactive channels are never show, active channels can be set not to be shown in the scope plot by the Show tickbox. The voltagerange can be selected from the dropdown menu. Note that the resolution is devided over the range from minus to plus this voltage. Every channel can be used in either AC or DC mode. One can also rename channels to make the more destinguishable and easier to retrace afterwards.

### Scope

Instead of separate scopereadouts one can also average over multiple signals. A delay between these signal readouts can be set. If the time between these readouts is less than the set interval a warning is displayed once, but readouts continue at the fastest pace possible.

The scopeplot window can be show or closed here. It can also be expoted as png by clicking Save plot. The savelocation and filename are set in the save menu.

### Scan

On the scopereadout, or averages over multiple of those, windows can be selected over which the average voltage is calculated. These windows can be compared, which is called a scan. 

This analysis can be activated or deactivted. Multiple scans can be performed with a delay between them. If the time between these scan is less than the set interval a warning is displayed once, but scans continue at the fastest pace possible.

A window can be selected or added from the dropdownmenu to change its settings. The colour of the window in the scopereadout plotwindow can be set. It can be shown in the scope plotwindow, where the boundaries can be slided to select the desired window, if not fixed. The boundaries can also be set by filling in their start and length. For every window also an active channel has to be selected. Extra windows can be deleted, but not Window 1 and 2.

A calculator can be selected or added from the dropdownmenu to change its settings. The colour of the calculator in the scan plotwindow can be set. It can be selected wether it is shown in the scan plotwindow. Two windows and the operation between these averages can be selected from the dropdownmenus. The name of the calculator can be changed for better labelling in plots. Extra calculators can be deleted, but not Calculator 1.

The scans can be plotted in a scanplot, which will be shown in a separate window if show is activated. The horizontal axis initial value and stepsize can be set, next to a label for this axis. If the Scan axislabel is set to "Time (s)" the horizontal axis value is time in seconds from the time of the first scanpoint. This plot can also be exported as png by clicking Save plot. The savelocation and filename are set in the save menu.

## Delay

If a Stanford Research Systems Delay Generator DG535 is connected correctly it can also be controlled from the PicoScope software. To establish the connection set the communication port for the device and selecting Active. Note that only one communication channel can be active at the same time, close any other connections via this port before trying to connect. The correct communication port can be found in the device manager. The software communicates to GPIB adress 5, which should therefore be set manualy in the Delay Generator by pressing the GPIB button before connecting.

The output signals from the BNC connectors of the delay generator can be set to TTL, NIM or ECL logic. The output impedance can be set to 50 Ohm or HighZ.

The Delay Generator can be triggered internally or externally. For the internal trigger insert a trigger frequency. For the external trigger set the input impedance for the external trigger BNC connector to 50 Ohm or HighZ. Also select the edge and level of the signal at which the trigger has to occur.

The delay generator can generate four delays, labelled A to D. For every delay the delay time and reference point have to be selected, either another delay or the trigger time T0. Note that the delay generator sets the outputsignals to high after the delay time and only sets the outputsignals back to low after the full cycle has completed, skipping any intermediate triggers. Signals of specific lengths can be made using the A^B, A_B, C^D and C_D connectors.

## Using delay for scans

A scan over different delays can be performed by setting the Scanpoint label in the Scan tab to Delay A up to Delay D. The initial Scan value is set to the set delaytime, the Scanpoint value difference is converted to seconds, but can be changed manually. If now a scan is performed the delaytime for the selected delay is changed by the Scan value difference time, as can be seen by the changing delaytime value in the Delay tab.

## Running measurements

By pressing start a measurement is started with the settings described above. After the set number of measurements and scans is performed the measurement automatically stops. By pressing continuously a measurement is started that does not stop automatically. Pause breaks the measurement, either finite or continuous, untill it is continued by pressing the same button. Stop ends the measurement, it can only be restarted by starting a new measurement. 

## How to read the datafiles in Python

To interpret saved data PicoReadBinary.py can be used, either in another script or directly. To do so import the script by
```
	import PicoReadBinary as prb
```
The script reads datafiles based on their metadatfile given as input (Absolute path). 

### prb.load_settings()

Asks (1) for a string with the metadatafilename and returns (3) a dictionary with the settings in this file, a string with the name of the user, a string with the name of the project

### prb.time_ns()

Asks (1) for a string with the metadatafilename and returns (1) a list with the timevalues in nanoseconds of readout of the scope starting at 0.

### prb.block_mV()

Asks (2 + 1) for a string with the metadatafilename, a sting with the channel, an integer with the readoutnumber if not averaged and returns (1) a list with the voltages in millivolts of readout of the scope of the given channel. If the channel is not in the data it returns a string with an errormessages including which channels are available in the datafile.

### prb.scan_V()

Asks (1) for a string with the metadatafilename and returns (1) a dictionary with Scanvalue and the calculators, both lists with scanvalues and the voltage differences respectively, a string with the scanlabel.

## Contact

The programmers guide for the PicoScope5000 is included as picoscope-5000-series-a-api-programmers-guide.pdf for reference.
Questions and suggestions for improvement can be sent to the developer Anno Touwen, a.p.touwen@rug.nl
