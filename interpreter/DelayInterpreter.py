from controller.DelayControl import SRSDG535Controller
from pint import UnitRegistry
ur = UnitRegistry()
from time import sleep

class SRSDG535Interpreter:
    def __init__(self):
        self.connectors = {'Ext': '0', 'T0': '1', 'A': '2', 'B': '3', 'AB': '4', 'C': '5', 'D': '6', 'CD': '7'}
        self.error_status = ['Unrecognized command', 'Wrong number of parameters','Value is outside allowed range', 'Wrong mode for the command', 'Delay linkage error', 'Delay range error', 'Recalled data was corrupt', 'Always zero']
        self.instrument_status = ['Command error detected', 'Busy with timing cycle', 'Trigger has occurred', '80MHz PLL is unlocked', 'Trigger rate too high', 'Always zero', 'Service request', 'Memory contents corrupted']
        self.impedances = {'50 Ohm': '0', 'HighZ': '1'}
        self.signalmodes = {'TTL': '0', 'NIM': '1', 'ECL': '2', 'Variable': '3'}
        self.triggermodes = {'Internal': '0', 'External': '1', 'Single shot': '2', 'Burst': '3'}
        self.slopes = {'Falling': '0', 'Rising': '1'}

    def start_control(self):
        self.ctr = SRSDG535Controller()

    def setup_connection(self, port):
        try:
            self.ctr.close_port()
        except:
            pass
        self.ctr.setup_port(port)

    def close_connection(self):
        self.ctr.close_port()

    def clear(self):
        self.ctr.clear()
        self.ctr.read_error_status()
        self.ctr.read_instrument_status()
        return self.check_error_status()

    def check_error_status(self):
        try:
            status = int(str(self.ctr.read_error_status().decode('ASCII')).replace('\r\n\n', ''))
            if status == 0:
                return
            else:
                return str(self.error_status[status])
        except ValueError:
            return 'Delay Generator not responding'

    def check_instrument_status(self):
        try:
            status = int(str(self.ctr.read_instrument_status().decode('ASCII')).replace('\r\n\n', ''))
            if status == 0:
                return
            else:
                return str(self.instrument_status[status])
        except ValueError:
            return 'Delay Generator not responding'

    def set_display(self, message):
        message = ' '.join(str(message).replace(' ', '_'))
        self.ctr.set_display(message)

# Delay

    def set_delay_time(self, channel, reference_channel, time):
        # Set delay of channel relative to reference channel to time in seconds, channel T0, A, B, C, D = 1, 2, 3, 5, 6
        channels = {'A': '0', 'B': '1', 'C': '2', 'D': '3'}
        self.ctr.set_display('')
        self.ctr.display_menu(1, 0, channels[channel])
        self.ctr.set_delay_time(self.connectors[channel], self.connectors[reference_channel], ' '.join(str(ur(str(time).replace(' ', '')).m_as('s'))))
        return self.check_error_status()

    def change_delay_sign(self, channel):
        channels = {'A': '0', 'B': '1', 'C': '2', 'D': '3'}
        self.ctr.set_display('')
        self.ctr.display_menu(1, 0, channels[channel])
        self.ctr.set_cursor_mode(0)
        self.ctr.set_cursor(3) # Set cursor to sign position
        self.ctr.change_value(1) # Change the sign
        return self.check_error_status()

# Outputs

    def set_termination_impedance(self, output, impedance):
        self.ctr.set_termination_impedance(self.connectors[output], self.impedances[impedance])
        return self.check_error_status()

    def set_output_mode(self, output, mode):
        # Set output T0, A, B, AB and -AB, C, D, CD and -CD = 1, ... 7 mode to TTL, NIM, ECL, VAR = 0, 1, 2, 3
        self.ctr.set_output_mode(self.connectors[output], self.signalmodes[mode])
        return self.check_error_status()

# Trigger

    def set_trigger_mode(self, mode):
        # 0 = Internal, 1 = External, 2 = Single shot, 3 = Burst
        self.ctr.set_trigger_mode(self.triggermodes[mode])
        return self.check_error_status()

    def set_int_trigger_rate(self, frequency):
        # Set internal trigger rate to frequency in Hz
        self.ctr.set_int_trigger_rate(' '.join(str(ur(str(frequency).replace(' ', '')).m_as('Hz'))))
        return self.check_error_status()

    def set_ext_trigger_impedance(self, impedance):
        # Set impedance for external trigger to 50 Ohm, high-Z = 0, 1
        self.ctr.set_ext_trigger_impedance(self.impedances[impedance])
        return self.check_error_status()

    def set_ext_trigger_level(self, level):
        # Set external trigger level in Volts
        self.ctr.set_ext_trigger_level(' '.join(str(ur(str(level).replace(' ', '')).m_as('V'))))
        return self.check_error_status()

    def set_ext_trigger_slope(self, slope):
        # Set external trigger slope to Falling, Rising = 0, 1
        self.ctr.set_ext_trigger_slope(self.slopes[slope])
        return self.check_error_status()



