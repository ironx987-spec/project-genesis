# tool_dispatcher.py
# Диспетчер команд для расшифровки JSON решений ИИ и выполнения действий манипулятора
import json

class ToolDispatcher:
    def __init__(self, bridge, kinematics, safety):
        self.bridge = bridge
        self.kinematics = kinematics
        self.safety = safety

    def execute_action(self, ai_response_json: str):
        try:
            data = json.loads(ai_response_json)
            action = data.get('action')

            if action == 'move_to':
                coords = data.get('coords', [10, 10, 5])
                if self.safety.check_workspace_bounds(*coords):
                    angles = self.kinematics.inverse_kinematics(*coords)
                    if angles:
                        safe_a = self.safety.validate_angles(angles)
                        self.bridge.send_angles(safe_a, smooth=True)

            elif action == 'set_angles':
                angles = data.get('angles', [90, 90, 90, 90, 90, 10])
                safe_a = self.safety.validate_angles(angles)
                self.bridge.send_angles(safe_a, smooth=True)

            elif action == 'home':
                self.bridge.send_angles([90, 90, 90, 90, 90, 10], smooth=True)

            elif action == 'grip':
                # Захват предмета клешней (Канал 5)
                self.bridge.send_single_angle(5, 70, smooth=True)

            elif action == 'release':
                # Разжатие клешни (Канал 5)
                self.bridge.send_single_angle(5, 10, smooth=True)

            elif action == 'wake':
                if hasattr(self.bridge, 'wake_up'):
                    self.bridge.wake_up()

        except Exception as e:
            print(f"[DISPATCHER ERR] Failed to execute action: {e}")
