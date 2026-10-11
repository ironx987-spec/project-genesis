# kinematics.py
# Прямая и обратная кинематика (FK/IK) для 6 DOF манипулятора DOOM
import math

class ArmKinematics:
    def __init__(self, l1: float = 10.0, l2: float = 12.0, l3: float = 8.0):
        # Длины звеньев (см): l1 (плечо), l2 (предплечье), l3 (кисть до центра схвата)
        self.l1 = l1
        self.l2 = l2
        self.l3 = l3

    def inverse_kinematics(self, x: float, y: float, z: float, pitch: float = 0.0, roll: float = 0.0) -> list:
        """
        Обратная кинематика: по координатам (X, Y, Z) и наклону кисти вычисляет углы сервоприводов.
        """
        # 1. Расчет угла базы (вращение вокруг оси Z)
        base_angle = math.degrees(math.atan2(y, x))
        if base_angle < 0:
            base_angle += 180

        # 2. Проекция на плоскость XY
        r_total = math.sqrt(x**2 + y**2)

        # 3. Нахождение точки запястья (Wrist Center) с учетом наклона pitch
        pitch_rad = math.radians(pitch)
        r = r_total - self.l3 * math.cos(pitch_rad)
        z_wrist = z - self.l3 * math.sin(pitch_rad)

        # 4. Проверка досягаемости
        d = math.sqrt(r**2 + z_wrist**2)
        if d > (self.l1 + self.l2) or d == 0:
            print(f"[DOOM KINEMATICS] Point ({x}, {y}, {z}) is out of reach!")
            return None

        # 5. Расчет угла плеча (Shoulder)
        cos_alpha = (self.l1**2 + d**2 - self.l2**2) / (2 * self.l1 * d)
        cos_alpha = max(-1.0, min(1.0, cos_alpha))
        alpha = math.acos(cos_alpha)
        beta = math.atan2(z_wrist, r)
        shoulder_angle = math.degrees(beta + alpha)

        # 6. Расчет угла локтя (Elbow)
        cos_gamma = (self.l1**2 + self.l2**2 - d**2) / (2 * self.l1 * self.l2)
        cos_gamma = max(-1.0, min(1.0, cos_gamma))
        gamma = math.acos(cos_gamma)
        elbow_angle = 180 - math.degrees(gamma)

        # 7. Компенсация угла запястья (Pitch)
        wrist_pitch = pitch - (shoulder_angle - (180 - elbow_angle))
        wrist_pitch_angle = max(0, min(180, int(wrist_pitch + 90)))

        # 8. Угол вращения кисти (Roll)
        wrist_roll_angle = max(0, min(180, int(roll + 90)))

        return [
            int(max(0, min(180, base_angle))),
            int(max(0, min(180, shoulder_angle))),
            int(max(0, min(180, elbow_angle))),
            wrist_pitch_angle,
            wrist_roll_angle,
            0  # 6-й канал: Клешня по умолчанию закрыта/неизменна
        ]

    def forward_kinematics(self, angles: list) -> dict:
        """
        Прямая кинематика: по углам сервоприводов вычисляет текущую позицию (X, Y, Z).
        """
        if len(angles) < 3:
            return {"x": 0, "y": 0, "z": 0}

        b_rad = math.radians(angles[0])
        s_rad = math.radians(angles[1])
        e_rad = math.radians(180 - angles[2])

        # Вычисление координат в плоской проекции
        r1 = self.l1 * math.cos(s_rad)
        z1 = self.l1 * math.sin(s_rad)

        r2 = r1 + self.l2 * math.cos(s_rad - e_rad)
        z2 = z1 + self.l2 * math.sin(s_rad - e_rad)

        # Перевод в 3D координаты
        x = r2 * math.cos(b_rad)
        y = r2 * math.sin(b_rad)

        return {"x": round(x, 2), "y": round(y, 2), "z": round(z2, 2)}
