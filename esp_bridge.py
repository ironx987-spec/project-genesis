# esp_bridge.py
# Мост связи между Termux (Python) и ESP32 по UDP для робота DOOM
import socket
import json

class ESPBridge:
    def __init__(self, esp_ip='192.168.4.1', port=5005):
        self.esp_ip = esp_ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2.0)

    def send_angles(self, angles: list, smooth: bool = False):
        """Отправка массива углов для всех сервоприводов"""
        msg = json.dumps({'angles': angles, 'smooth': smooth})
        try:
            self.sock.sendto(msg.encode('utf-8'), (self.esp_ip, self.port))
        except Exception as e:
            print(f"[DOOM BRIDGE ERR] Failed to send angles: {e}")

    def send_single_angle(self, channel: int, angle: int, smooth: bool = False):
        """Отправка угла на один конкретный канал"""
        msg = json.dumps({'channel': channel, 'angle': angle, 'smooth': smooth})
        try:
            self.sock.sendto(msg.encode('utf-8'), (self.esp_ip, self.port))
        except Exception as e:
            print(f"[DOOM BRIDGE ERR] Failed to send channel {channel}: {e}")

    def wake_up(self):
        """Отправка команды принудительного пробуждения PCA9685"""
        msg = json.dumps({'cmd': 'wake'})
        try:
            self.sock.sendto(msg.encode('utf-8'), (self.esp_ip, self.port))
            print("[DOOM BRIDGE] Sent wake-up command to ESP32.")
        except Exception as e:
            print(f"[DOOM BRIDGE ERR] Wake command failed: {e}")
