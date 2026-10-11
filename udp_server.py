# udp_server.py
# UDP-сервер на ESP32 для приема команд движения DOOM
import socket
import json

def start_udp_server(servo_driver, host='0.0.0.0', port=5005):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f'[DOOM UDP] Listening on {host}:{port}')
    
    while True:
        data, addr = sock.recvfrom(1024)
        try:
            msg = json.loads(data.decode('utf-8'))
            
            # Принудительное пробуждение драйвера
            if msg.get('cmd') == 'wake':
                if hasattr(servo_driver, 'wake_up'):
                    servo_driver.wake_up()
                    print('[DOOM UDP] PCA9685 Woken up!')
            
            # Установка всех углов сразу
            elif 'angles' in msg:
                smooth = msg.get('smooth', False)
                for ch, angle in enumerate(msg['angles']):
                    if smooth:
                        servo_driver.move_smooth(ch, angle)
                    else:
                        servo_driver.set_angle(ch, angle)
            
            # Установка конкретного канала
            elif 'channel' in msg and 'angle' in msg:
                ch = msg['channel']
                angle = msg['angle']
                if msg.get('smooth', False):
                    servo_driver.move_smooth(ch, angle)
                else:
                    servo_driver.set_angle(ch, angle)
                    
        except Exception as e:
            print('[DOOM UDP ERR]', e)
