from RPi import GPIO
from threading import *
from time import sleep


class Move(Thread):
    def __init__(self, name, updater, curState, enc, stopBtn, moveBtn,
                 cleanBtn, pin_right, pin_left, pin_down, pin_clean):
        Thread.__init__(self)
        self.pin_right = pin_right
        self.pin_left = pin_left
        self.pin_down = pin_down
        self.pin_clean = pin_clean
        self.gpio_init()
        self.name = name
        self.updater = updater
        self.state = curState
        self.encoder = enc
        self.stopBtn = stopBtn
        self.moveBtn = moveBtn
        self.cleanBtn = cleanBtn
        self.isCalibrated = False
        self.toCleanNow = False
        self.toDownNow = False
        self.firstCalibrate = False
        self.toRestart = False

    def gpio_init(self):
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.pin_right, GPIO.OUT)
        GPIO.output(self.pin_right, 0)
        GPIO.setup(self.pin_left, GPIO.OUT)
        GPIO.output(self.pin_left, 0)
        GPIO.setup(self.pin_down, GPIO.OUT)
        GPIO.output(self.pin_down, 0)
        GPIO.setup(self.pin_clean, GPIO.OUT)
        GPIO.output(self.pin_clean, 0)

    def run(self):
        while self.state.isAlive:
            try:
                if self.toRestart:
                    self.state.findFile()
                    self.state.load_settings()
                    self.state.curL = self.state.startL
                    self.isCalibrated = False
                    self.state.isFeedEnabled = self.isCalibrated
                    self.move_stop()
                    self.updater.update_vals()
                    self.toRestart = False
                if self.toCleanNow:
                    self.state.isFeedEnabled = False
                    self.clean_cycle()
                    self.toCleanNow = False
                if self.toDownNow:
                    self.state.isFeedEnabled = False
                    self.move_down()
                    self.toDownNow = False
                if self.moveBtn.isPressed():
                    self.state.isFeedEnabled = self.isCalibrated
                    if not self.isCalibrated:
                        self.move_left()
                        while (not self.stopBtn.isPressed()) and self.state.isAlive and self.moveBtn.isPressed():
                            sleep(0.01)
                        if self.moveBtn.isPressed():
                            self.move_stop()
                            self.isCalibrated = True
                            self.firstCalibrate = True
                            if self.cleanBtn.isPressed():
                                self.clean_cycle()
                            while self.state.isUpdating or self.state.isMovingDown:
                                sleep(0.01)
                            self.move_right()
                            while self.stopBtn.isPressed() and self.state.isAlive and self.moveBtn.isPressed():
                                sleep(0.01)
                            if self.moveBtn.isPressed():
                                self.encoder.write(0)
                            if self.state.curL % 2 != 0:
                                self.move_stop_nodelay()
                            else:
                                self.move_right()
                                while self.encoder.read() < self.state.width and self.state.isAlive \
                                        and self.moveBtn.isPressed():
                                    sleep(0.01)
                                self.move_stop()
                                if not self.moveBtn.isPressed():
                                    self.isCalibrated = False
                        else:
                            self.move_stop()
                    else:
                        if self.state.curL % 2 != 0:
                            self.move_right()
                            while self.encoder.read() < self.state.width and self.state.isAlive \
                                    and self.moveBtn.isPressed():
                                sleep(0.01)
                        else:
                            self.move_left()
                            while self.encoder.read() > 0 and (not self.stopBtn.isPressed()) and self.state.isAlive \
                                    and self.moveBtn.isPressed():
                                sleep(0.01)
                        if self.moveBtn.isPressed():
                            if self.state.curL % 2 == 0:
                                self.isCalibrated = False  # Отправляем на перекалибровку только после печати влево
                            self.state.curL += 1
                            self.move_stop()
                            self.state.saveLine()
                            self.move_down()
                            self.state.isFeedEnabled = False
                            self.updater.update_vals()
                            self.state.isFeedEnabled = self.isCalibrated
                        else:
                            self.isCalibrated = False
                            self.state.isFeedEnabled = self.isCalibrated
                            self.move_stop()
                else:
                    self.isCalibrated = False
                    self.state.isFeedEnabled = self.firstCalibrate
                    sleep(0.1)
            except KeyboardInterrupt:
                GPIO.cleanup()
                break
            except Exception as e:
                print(e)
                sleep(0.1)
                continue

    def move_right(self):
        GPIO.output(self.pin_right, 1)
        GPIO.output(self.pin_left, 0)
        self.state.direct = True
        print("right")

    def move_left(self):
        GPIO.output(self.pin_right, 0)
        GPIO.output(self.pin_left, 1)
        self.state.direct = False
        print("left")

    def move_stop(self):
        GPIO.output(self.pin_right, 0)
        GPIO.output(self.pin_left, 0)
        print("stop")
        sleep(0.5)

    def move_stop_nodelay(self):
        GPIO.output(self.pin_right, 0)
        GPIO.output(self.pin_left, 0)
        print("fastStop")

    def move_down(self):
        self.state.isMovingDown = True
        GPIO.output(self.pin_down, 1)
        print("down")
        sleep(self.state.down/1000)
        GPIO.output(self.pin_down, 0)
        sleep(0.5)
        self.state.isMovingDown = False

    def clean_cycle(self):
        GPIO.output(self.pin_clean, 1)
        print("clean")
        sleep(self.state.cleanPinTime/1000)
        GPIO.output(self.pin_clean, 0)
        sleep(0.1)
        self.updater.clean_nozzle()

    def clean_now(self, channel):
        self.toCleanNow = True

    def move_down_now(self, channel):
        self.toDownNow = True

    def restart(self, channel):
        self.toRestart = True

