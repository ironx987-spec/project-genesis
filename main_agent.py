# main_agent.py
# Главный координатор и агент управления роботом DOOM
import time
from esp_bridge import ESPBridge
from kinematics import ArmKinematics
from safety_guard import SafetyGuard
from tool_dispatcher import ToolDispatcher
from pose_sequences import play_pose
from log_center import LogCenter

def start():
    logger = LogCenter()
    logger.log('MAIN', 'Starting DOOM AI System...')

    bridge = ESPBridge(esp_ip='192.168.4.1', port=5005)
    kinematics = ArmKinematics()
    safety = SafetyGuard()
    dispatcher = ToolDispatcher(bridge, kinematics, safety)

    logger.log('MAIN', 'Setting SAFE HOME pose...')
    play_pose(bridge, 'home')

    logger.log('MAIN', 'All systems online. Entering main operational loop.')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.log('MAIN', 'Shutting down safely...')
        play_pose(bridge, 'rest')

if __name__ == '__main__':
    start()
