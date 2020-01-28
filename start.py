from interpreter.PicoInterpreter import Pico5000Interpreter
from interpreter.DelayInterpreter import SRSDG535Interpreter
from interface.PicoInterface import Pico5000Interface
from PyQt5.QtWidgets import QMainWindow, QApplication

itp = Pico5000Interpreter()
app = QApplication([])
Pico_main = Pico5000Interface(itp)
Pico_main.show()
app.exec_()
