from time import sleep
import os
import numpy as np
import encoder
import nozzle
import button
import printhead
import screen
import spy
from threading import *


nozzlePins = [7, 11, 13, 15, 19, 21, 23, 29, 31, 33, 35, 37, 40, 38, 36, 32]
pin_right, pin_left, pin_down, pin_clean = 26, 24, 22, 18

printBtn = button.Button(10)
cleanBtn = button.VirtButton("1", "2")
moveBtn = button.VirtButton("3", "4")
stopBtn = button.Button(8)
cleanNowBtn = button.VirtButton("5", "6")
moveDownBtn = button.VirtButton("7", "8")
restartBtn = button.VirtButton("9", "q")
enc = encoder.Encoder(16, 12)  # 16 - clk, 12 - dt

instructFilename = "INSTRUCTION.TXT"
screenUpdPeriod = 0.5  # задержка между обновлениями экрана (секунды)
spyUpdPeriod = 0.2  # задержка между обновлениями шпиона (секунды)


class ValuesUpdater:
    def __init__(self, nozzles, state):
        self.nozzles = nozzles
        self.state = state
        self.upd_lock = RLock()
        self.virtual_nozzles = [nozzle.VirtualNozzle(state) for _ in range(len(nozzlePins))]

    def clean_nozzle(self):
        for i in self.state.nozzlesClean:
            self.nozzles[i].isCleaning = True
        done = False
        while not done:
            done = True
            for i in self.nozzles:
                if i.isCleaning:
                    done = False
            sleep(0.1)

    def update_vals(self):
        with self.upd_lock:
            self.state.isUpdating = True
            for i in self.nozzles:
                i.isUpdating = True
            if max([self.virtual_nozzles[j].curL for j in range(len(self.virtual_nozzles))]) == self.state.curL:
                print('COPY PRELOADED')
                self.copy_preloaded_vals()
            else:
                print('LOAD FROM SCRATCH')
                self.parse_vals(self.state.curL)
                self.copy_preloaded_vals()
            # self.print_vals()
            for i in self.nozzles:
                i.isUpdating = False
            self.state.isUpdating = False
        Thread(target=self.parse_vals, args=(self.state.curL+1, )).start()

    def print_vals(self):
        for i in range(len(self.nozzles)):
            print("ID: " + str(i))
            print("SIG: " + str(self.nozzles[i].sig))
            print("WAIT: " + str(self.nozzles[i].wait))
            print("CURL: " + str(self.nozzles[i].curL))
            print("=========")

    def copy_preloaded_vals(self):  # устанавливает предзагруженные значения
        print('copy')
        for i in range(len(self.virtual_nozzles)):
            self.nozzles[i].sig = self.virtual_nozzles[i].sig
            self.nozzles[i].wait = self.virtual_nozzles[i].wait
            self.nozzles[i].curL = self.virtual_nozzles[i].curL

    def parse_vals(self, cur_l):  # скачивает следующие значения с флешки
        print('parse', cur_l)
        with self.upd_lock:
            with open(self.state.file) as file:
                found = False
                for line in file:
                    if line.replace('\r', '').replace('\n', '') == "L" + str(cur_l):
                        found = True
                        continue
                    elif "L" in line and found:
                        return
                    if found:
                        substr = line.split('.')
                        addr = int(substr[0].replace('F', ''))
                        setting = substr[1].split(';')
                        sig = np.zeros(shape=self.state.width + 1, dtype=np.uint32)
                        wait = np.zeros(shape=self.state.width + 1, dtype=np.uint32)
                        for i in setting:
                            sub = i.split(':')
                            if len(sub) == 3:
                                pos = int(sub[0])
                                sig[pos] = int(sub[1])
                                wait[pos] = int(sub[2])
                        self.virtual_nozzles[addr].sig = sig
                        self.virtual_nozzles[addr].wait = wait
                        self.virtual_nozzles[addr].curL = cur_l


class State:
    def __init__(self):
        self.isAlive = True
        self.file = None
        self.direct = False
        self.curL = -1
        self.startL = -1
        self.width = 0
        self.down = 0
        self.cleanPinTime = 0
        self.cleanNozzleTime = 0
        self.nozzlesClean = []
        self.isFeedEnabled = False
        self.isUpdating = False
        self.isMovingDown = False
        self.findFile()

    def findFile(self):
        filePath = ""
        for drive in os.listdir("/media/pi"):
            filePath = "/media/pi/" + drive + "/" + instructFilename
            if os.path.isfile(filePath):
                break
        if not os.path.isfile(filePath):
            raise FileNotFoundError
        else:
            self.file = filePath

    def saveLine(self):
        f = open("currentLine.txt", 'w')
        f.write(str(self.curL))
        f.close()

    def loadLine(self):
        if os.path.isfile("currentLine.txt"):
            f = open("currentLine.txt")
            curL = f.read()
            if curL.isnumeric():
                self.curL = int(curL)

    def load_settings(self):
        file = open(self.file, "r")
        for i in file:
            i = i.replace('\n', '').replace('\r', '')
            substr = i.split('=')
            if substr[0] == 'Width':
                self.width = int(substr[1])
            elif substr[0] == 'Start':
                self.curL = int(substr[1])
                self.startL = int(substr[1])
            elif substr[0] == 'Down':
                self.down = int(substr[1])
            elif substr[0] == 'Clear':
                val = substr[1].split('.')
                timers = val[0].split(':')
                self.cleanPinTime = int(timers[0])
                self.cleanNozzleTime = int(timers[1])
                nozzles = val[1].split(':')
                for j in nozzles:
                    self.nozzlesClean.append(int(j))
            if self.isReady():
                file.close()
                self.printSettings()
                return True
        file.close()
        return False

    def printSettings(self):
        print("SETTINGS:")
        print("Width: " + str(self.width))
        print("Start: " + str(self.startL))
        print("Down: " + str(self.down))
        print("Clear pin: " + str(self.cleanPinTime))
        print("Clear nozzle: " + str(self.cleanNozzleTime))
        print("Clear nozzle list: " + str(self.nozzlesClean))
        print("=========")

    def isReady(self):
        if self.curL != -1 and self.width != 0 and self.down != 0 and self.cleanPinTime != 0 and \
                self.cleanNozzleTime != 0 and len(self.nozzlesClean) > 0 and self.startL != -1:
            return True
        return False


curState = State()
if not curState.load_settings():
    raise Exception("Can't read settings from file")
curState.loadLine()

noz = [nozzle.Nozzle(f"Nozzle {i} Thread", enc, i, printBtn, curState) for i in nozzlePins]
updater = ValuesUpdater(noz, curState)
move = printhead.Move("Move Thread", updater, curState, enc, stopBtn, moveBtn,
                      cleanBtn, pin_right, pin_left, pin_down, pin_clean)

screen = screen.ScreenUpdater("1602Screen", curState, moveBtn, printBtn, enc, screenUpdPeriod)
uart = spy.SpyUpdater("Spy", curState, spyUpdPeriod, enc)

cleanNowBtn.set_callback(move.clean_now)
moveDownBtn.set_callback(move.move_down_now)
restartBtn.set_callback(move.restart)

updater.update_vals()

for i in noz:
    i.daemon = True
    i.start()
move.daemon = True
move.start()

screen.daemon = True
screen.start()

uart.daemon = True
uart.start()

try:
    while True:
        print("encoder: " + str(enc.read()))
        # print(curState.isFeedEnabled, curState.curL, noz[0].curL, printBtn.isPressed())
        sleep(1)
finally:
    curState.isAlive = False
    sleep(1)
    enc.dispose()
    printBtn.dispose()
    cleanBtn.dispose()
    moveBtn.dispose()
    stopBtn.dispose()
    cleanNowBtn.dispose()
    moveDownBtn.dispose()
