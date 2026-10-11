# pose_sequences.py
# Набор готовых поз и анимаций для манипулятора DOOM
import time

POSES = {
    'home': [90, 90, 90, 90, 90, 10],
    'rest': [90, 20, 150, 90, 90, 0],
    'wave': [90, 90, 60, 120, 90, 10],
    'look_around': [45, 100, 80, 90, 90, 10],
    'grab_ready': [90, 110, 40, 90, 90, 40]
}

def play_pose(bridge, pose_name: str, delay: float = 0.5):
    """Воспроизводит фиксированную позу из словаря POSES"""
    if pose_name in POSES:
        print(f"[DOOM POSE] Playing pose: '{pose_name}'")
        bridge.send_angles(POSES[pose_name], smooth=True)
        time.sleep(delay)
    else:
        print(f"[DOOM POSE ERR] Unknown pose: '{pose_name}'")

def wave_hand(bridge):
    """Анимация приветствия (махание рукой)"""
    print("[DOOM ANIMATION] Starting wave sequence...")
    play_pose(bridge, 'wave')
    for _ in range(3):
        bridge.send_angles([90, 90, 60, 140, 90, 10], smooth=True)
        time.sleep(0.3)
        bridge.send_angles([90, 90, 60, 100, 90, 10], smooth=True)
        time.sleep(0.3)
    play_pose(bridge, 'home')
