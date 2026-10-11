# safety_guard.py
# Системы безопасности и программные концевики манипулятора DOOM

class SafetyGuard:
    def __init__(self, min_voltage: float = 5.0):
        # Жесткие границы углов для каждого из 6 сервоприводов
        self.angle_limits = {
            0: (0, 180),   # База
            1: (10, 160),  # Плечо
            2: (10, 150),  # Локоть
            3: (0, 180),   # Наклон кисти
            4: (0, 180),   # Вращение кисти
            5: (0, 90),    # Клешня
        }
        self.min_voltage = min_voltage

    def validate_angles(self, angles: list) -> list:
        """Обрезает углы до пределов физической безопасности механики"""
        safe_angles = []
        for ch, angle in enumerate(angles):
            min_a, max_a = self.angle_limits.get(ch, (0, 180))
            safe_val = max(min_a, min(max_a, int(angle)))
            safe_angles.append(safe_val)
        return safe_angles

    def check_workspace_bounds(self, x: float, y: float, z: float) -> bool:
        """Проверка на столкновение со столом или запредельный вылет"""
        # Защита от удара об стол
        if z < -2.0:
            print(f"[DOOM SAFETY] Collision risk detected! Z={z} is below table level.")
            return False
        
        # Защита от слишком далеких координат (предел вылета руки ~30 см)
        max_reach = 30.0
        dist = (x**2 + y**2 + z**2) ** 0.5
        if dist > max_reach:
            print(f"[DOOM SAFETY] Target distance {dist:.1f}cm exceeds max reach ({max_reach}cm).")
            return False

        return True

    def check_power(self, current_voltage: float) -> bool:
        """Проверка уровня напряжения питания"""
        if current_voltage < self.min_voltage:
            print(f"[DOOM SAFETY CRITICAL] Low voltage detected: {current_voltage}V! Emergency stop recommended.")
            return False
        return True
