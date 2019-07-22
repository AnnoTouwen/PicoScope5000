import serial

class SRSDG535Controller:
    def __init__(self):
        pass

# Communication port

    def setup_port(self, port):
        # Open communicationport to Delay Generator
        self.DG = serial.Serial(port = str(port), timeout = 0.001)#, write_timeout = 1)
        self.DG.write('++addr 5\n'.encode('ASCII'))

    def close_port(self):
        # Close communicationport to Delay Generator
        self.DG.close()

# Initialization

    def clear(self):
        # Reset all settings on device
        self.DG.write('C L \r'.encode('ASCII'))

# Status

    def read_error_status(self):
        self.DG.write('E S \r'.encode('ASCII'))
        return self.DG.read_until('\r\n\n')

    def read_instrument_status(self):
        self.DG.write('I S \r'.encode('ASCII'))
        return self.DG.read_until('\r\n\n')

# Display

    def set_display(self, message):
        self.DG.write(('D S ' + str(message) + ' \r').encode('ASCII'))

    def display_menu(self, menu, submenu, line_number):
        self.DG.write(('D L '  + str(menu) + ' , ' + str(submenu) + ' , ' + str(line_number) + ' \r').encode('ASCII'))

    def set_cursor(self, position):
        self.DG.write(('S C '  + str(position) + ' \r').encode('ASCII'))

    def set_cursor_mode(self, mode):
        # mode: Cursor, Number = 0, 1
        self.DG.write(('C S '  + str(mode) + ' \r').encode('ASCII'))

    def change_value(self, direction):
        # direction: decrement, increment = 0, 1
        self.DG.write(('I C '  + str(direction) + ' \r').encode('ASCII'))

# Delay

    def set_delay_time(self, channel, reference_channel, time_in_seconds):
        # Set delay of channel relative to reference channel to time in seconds, channel T0, A, B, C, D = 1, 2, 3, 5, 6
        self.DG.write(('D T ' + str(channel) + ' , ' + str(reference_channel) + ' , ' + str(time_in_seconds) + ' \r').encode('ASCII'))

# Outputs

    def set_termination_impedance(self, output, impedance):
        # Set impedance for output T0, A, B, AB and -AB, C, D, CD and -CD = 1, ... 7 to 50 Ohm, high-Z = 0, 1
        self.DG.write(('T Z ' + str(output) + ' , ' + str(impedance) + ' \r').encode('ASCII'))

    def set_output_mode(self, output, mode):
        # Set output T0, A, B, AB and -AB, C, D, CD and -CD = 1, ... 7 mode to TTL, NIM, ECL, variable = 0, 1, 2, 3
        self.DG.write(('T Z ' + str(output) + ' , ' + str(mode) + ' \r').encode('ASCII'))

# Trigger

    def set_trigger_mode(self, mode):
        # 0 = Internal, 1 = External, 2 = Single shot, 3 = Burst
        self.DG.write(('T M ' + str(mode) + ' \r').encode('ASCII'))

    def set_int_trigger_rate(self, frequency_in_Hz):
        # Set internal trigger rate to frequency in Hz
        self.DG.write(('T R 0 , '+ str(frequency_in_Hz) + ' \r').encode('ASCII'))

    def set_ext_trigger_impedance(self, impedance):
        # Set impedance for external trigger to 50 Ohm, high-Z = 0, 1
        self.DG.write(('T Z 0 , ' + str(impedance) + ' \r').encode('ASCII'))

    def set_ext_trigger_level(self, level_in_Volts):
        # Set external trigger level in Volts
        self.DG.write(('T L ' + str(level_in_Volts) + ' \r').encode('ASCII'))

    def set_ext_trigger_slope(self, slope):
        # Set external trigger slope to falling, rising = 0, 1
        self.DG.write(('T S ' + str(slope) + ' \r').encode('ASCII'))

if __name__ == '__main__':
    Delay = SRSDG535Controller()
    Delay.setup_port('COM4')
    Delay.clear()
    Delay.read_error_status()
    Delay.read_instrument_status()
    Delay.set_display('R e m o t e _ C o n t r o l _ M o d e')
    print('Error status: ', str(Delay.read_error_status().decode('ASCII')))
    print('Instrumental status: ', str(Delay.read_instrument_status().decode('ASCII')))
    Delay.set_trigger_mode('0')
    Delay.set_int_trigger_rate('1 0 0 0')
    for channelindex in range(4):
        channel = [1, 2, 3, 5, 6]
        Delay.set_delay_time(channel[channelindex+1], channel[channelindex], '0 . 0 0 0 {}'.format(channelindex+1))
        print('Error status: ', str(Delay.read_error_status().decode('ASCII')))
    for output in range(7):
        Delay.set_termination_impedance(output+1, (output + 1) % 2)
        Delay.set_output_mode(output + 1, (output + 1) % 2)
        print('Error status: ', str(Delay.read_error_status().decode('ASCII')))
    Delay.set_trigger_mode('1')
    Delay.set_ext_trigger_level('1')
    Delay.set_ext_trigger_slope(1)
    Delay.set_ext_trigger_slope(0)
    Delay.set_ext_trigger_slope(1)
    Delay.set_ext_trigger_slope(0)
    Delay.close_port()


