# servo_driver.py
# Драйвер управления сервоприводами PCA9685 для DOOM
import time
from machine import I2C, Pin

class ServoDriver:
    def __init__(self, i2c: I2C, address: int = 0x40, freq: int = 50):
        self.i2c = i2c
        self.address = address
        self.freq = freq
        self.limits = {
            0: {"min_us": 500, "max_us": 2500, "min_deg": 0, "max_deg": 180},
            1: {"min_us": 500, "max_us": 2500, "min_deg": 10, "max_deg": 170},
            2: {"min_us": 500, "max_us": 2500, "min_deg": 0, "max_deg": 160},
            3: {"min_us": 500, "max_us": 2500, "min_deg": 0, "max_deg": 180},
            4: {"min_us": 500, "max_us": 2500, "min_deg": 0, "max_deg": 180},
            5: {"min_us": 600, "max_us": 2400, "min_deg": 0, "max_deg": 90},
        }
        self.current_angles = [90, 90, 90, 90, 90, 0]
        self._init_pca9685()

    def _write_reg(self, reg: int, value: int):
        self.i2c.writeto_mem(self.address, reg, bytes([value]))

    def _read_reg(self, reg: int) -> int:
        return self.i2c.readfrom_mem(self.address, reg, 1)[0]

    def _init_pca9685(self):
        self._write_reg(0x00, 0x00)
        self.set_pwm_freq(self.freq)
        self.wake_up()

    def wake_up(self):
        """Принудительное пробуждение драйвера из режима SLEEP"""
        oldmode = self._read_reg(0x00)
        newmode = (oldmode & ~0x10) | 0xA0
        self._write_reg(0x00, newmode)
        time.sleep_ms(5)

    def set_pwm_freq(self, freq: int):
        prescaleval = 25000000.0 / 4096.0 / freq - 1.0
        prescale = int(prescaleval + 0.5)
        oldmode = self._read_reg(0x00)
        sleep_mode = (oldmode & 0x7F) | 0x10
        self._write_reg(0x00, sleep_mode)
        self._write_reg(0xFE, prescale)
        self._write_reg(0x00, oldmode)
        time.sleep_ms(5)
        self._write_reg(0x00, 0xA0)
        time.sleep_ms(5)

    def set_pwm(self, channel: int, on: int, off: int):
        reg = 0x06 + 4 * channel
        self.i2c.writeto_mem(self.address, reg, bytes([on & 0xFF, on >> 8, off & 0xFF, off >> 8]))

    def set_angle(self, channel: int, angle: int):
        if channel not in self.limits:
            return
        cfg = self.limits[channel]
        angle = max(cfg["min_deg"], min(cfg["max_deg"], angle))
        us = cfg["min_us"] + (angle - cfg["min_deg"]) * (cfg["max_us"] - cfg["min_us"]) / (cfg["max_deg"] - cfg["min_deg"])
        off = int((us / 20000.0) * 4095)
        self.set_pwm(channel, 0, off)
        self.current_angles[channel] = angle

    def move_smooth(self, channel: int, target_angle: int, step_delay_ms: int = 20):
        start_angle = self.current_angles[channel]
        if start_angle == target_angle:
            return
        step = 1 if target_angle > start_angle else -1
        for angle in range(start_angle, target_angle + step, step):
            self.set_angle(channel, angle)
            time.sleep_ms(step_delay_ms)

    def emergency_stop(self):
        for i in range(16):
            self.set_pwm(i, 0, 0)
