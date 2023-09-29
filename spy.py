from threading import *
from time import sleep
import serial


class SpyUpdater(Thread):
    def __init__(self, name, state, upd_period, enc):
        Thread.__init__(self)
        self.name = name
        self.freq = upd_period
        self.state = state
        self.encoder = enc

    def run(self):
        self.ser = serial.Serial(
            port='/dev/ttyUSB0',
            baudrate=115200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
            timeout=0.1
        )
        while True:
            try:
                self.ser.write(('L' + str(self.state.curL) + ';' + str(self.encoder.read()) + '\n').encode())
                sleep(self.freq)
            except KeyboardInterrupt:
                self.ser.close()
                break
            except Exception as e:
                print(e)
                break