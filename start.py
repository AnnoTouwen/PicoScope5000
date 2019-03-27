from interpreter.PicoInterpreter import Pico5000Interpreter
from interface.PicoInterface import Pico5000Interface
from PyQt5.QtWidgets import QMainWindow, QApplication

  
itp = Pico5000Interpreter()
'''  
itp.load_settings('users.yml')
itp.start_device()
itp.setup_device('12BIT')
for i in itp.user['channels']:
    itp.setup_channel(i)
itp.set_trigger()
itp.set_timewindow()
for i in itp.user['channels']:
    itp.set_buffer(i)
itp.get_block()
itp.read_data()
for i in itp.user['channels']:
    itp.interpret_data(i) 
import matplotlib.pyplot as plt    
for i in itp.user['channels']:
    plt.plot(itp.block['time'], itp.block[i][:])
plt.xlabel('Time (ns)')
plt.ylabel('Voltage (mV)')
plt.show()
itp.stop_device()
itp.close_device()
'''

app = QApplication([])
Pico_main = Pico5000Interface(itp)
Pico_main.show()
app.exec_()

