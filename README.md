# PicoScope5000 Software for reading out data and scanning

Welcome to the PicoScope5000 software developed for the NL-eEDM collaboration. This software has been developed for testing the performance of the Cryogenic source built at the Vrije Universiteit Amsterdam.

## How to get the software on Windows

1. Download Python 3 (https://www.python.org/downloads/windows/) and add it to PATH (option in installation menu or append manually).
2. Install pip if it is not included in the Python installation already.
3. Download git (https://git-scm.com/download/win).
4. Make a directory in which you want to get the software.
5. Open a terminal (windows + R) and navigate to the directory.
6. Download the software by cloning the directory
	>>> git clone https://github.com/AnnoTouwen/PicoScope5000.git
7. Copy the picosdk directory to the python packages folder, which could be something like
	C:/Python/Lib/site-packages
8. Install the following Python packages using pip in the terminal
	>>> pip install Pint
	>>> pip install PyYAML
	>>> pip install PyQt5
	>>> pip install numpy
	>>> pip install Pyqtgraph
	>>> pip install Matplotlib

## How to use the software

Run start.py by double clicking if Python 3 is set to be the standard for executing .py files.
Alternatively you could naviate to the directory in the terminal and run
	>>> python start.py

If a PicoScope5000 device is connected a window with the user interface should appear. The powersupply is checked and the device is set accordingly. The Default settings are loaded from config/users.yml. Dependent on these settings a first readout of the scope is also show in a seraprate window. In the user interface messages to the user are dislayed, settings can be changed and measurements can be started. Realtime analysis and plots are shown in separate windows.

### Powersupply

If the device has four input channels and an external powersupply is connected four channel mode is selected. If the device is power through USB at most two channels can be used. The settings can be changed via the Device menu in the upperleft corner of the interface, but the powersupply is only reset by restarting the programm.

### User

As the programm is started the Default settings are loaded, but it is suggested to login with your name and project, which you could fill in in the user menu. Your personal settings can be saved and loaded using the buttons on the right. The settings from a previous measurement can also be loaded from the metadata. In this menu the fontsize can also be changed. Note that this also changes the fontsize of the plots in the other windows.

### Save

The save directory for all the data output from the program can be set here. Also the base filename can be set. Not however that the full filename will be different dependent on the datatype and time of the measurement. The full filename always includes the Unix time, seconds since January 1, 1970, 00:00:00 at UTC. For binary data of the scope readout binary will be added to the filename and the extension is .bin. If a measurement is the average of multiple readouts the readouts themselves are stored separately and numbers starting from 1 are added. 