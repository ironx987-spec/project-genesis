// --- 3D-МОДЕЛЬ 6-DOF МАНИПУЛЯТОР ---
// Подключается к сцене doom_web.py. Ожидает глобальные: scene, camera, THREE.
(function() {
    const robot = new THREE.Group();
    scene.add(robot);

    const matBase  = new THREE.MeshStandardMaterial({ color: 0x2a4d8f, metalness: 0.6, roughness: 0.4 });
    const matLink  = new THREE.MeshStandardMaterial({ color: 0x4a6fa5, metalness: 0.5, roughness: 0.5 });
    const matJoint = new THREE.MeshStandardMaterial({ color: 0x1a1a1a, metalness: 0.8, roughness: 0.2 });
    const matGrip  = new THREE.MeshStandardMaterial({ color: 0x8f2a2a, metalness: 0.3, roughness: 0.7 });

    // 1. База
    const baseGroup = new THREE.Group();
    robot.add(baseGroup);
    const baseMesh = new THREE.Mesh(new THREE.CylinderGeometry(1.2, 1.5, 0.4, 32), matBase);
    baseMesh.position.y = 0.2;
    baseGroup.add(baseMesh);

    // 2. Плечо
    const shoulderGroup = new THREE.Group();
    shoulderGroup.position.y = 0.4;
    baseGroup.add(shoulderGroup);
    const shoulderMesh = new THREE.Mesh(new THREE.BoxGeometry(0.8, 1.0, 0.8), matLink);
    shoulderMesh.position.y = 0.5;
    shoulderGroup.add(shoulderMesh);

    // 3. Локоть
    const elbowGroup = new THREE.Group();
    elbowGroup.position.y = 1.0;
    shoulderGroup.add(elbowGroup);
    const elbowMesh = new THREE.Mesh(new THREE.BoxGeometry(0.6, 1.2, 0.6), matLink);
    elbowMesh.position.y = 0.6;
    elbowGroup.add(elbowMesh);

    // 4. Запястье Pitch
    const wristPitchGroup = new THREE.Group();
    wristPitchGroup.position.y = 1.2;
    elbowGroup.add(wristPitchGroup);
    const wristPitchMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, 0.4, 16), matJoint);
    wristPitchMesh.rotation.x = Math.PI / 2;
    wristPitchMesh.position.y = 0.2;
    wristPitchGroup.add(wristPitchMesh);

    // 5. Запястье Roll
    const wristRollGroup = new THREE.Group();
    wristRollGroup.position.y = 0.4;
    wristPitchGroup.add(wristRollGroup);
    const wristRollMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.25, 0.4, 16), matJoint);
    wristRollMesh.position.y = 0.2;
    wristRollGroup.add(wristRollMesh);

    // 6. Захват
    const gripperGroup = new THREE.Group();
    gripperGroup.position.y = 0.4;
    wristRollGroup.add(gripperGroup);
    const gripLeft = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.6, 0.2), matGrip);
    gripLeft.position.set(-0.2, 0.3, 0);
    gripperGroup.add(gripLeft);
    const gripRight = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.6, 0.2), matGrip);
    gripRight.position.set(0.2, 0.3, 0);
    gripperGroup.add(gripRight);

    // Экспортируем группы в глобальную область для будущего управления слайдерами
    window.robotGroups = {
        base: baseGroup,
        shoulder: shoulderGroup,
        elbow: elbowGroup,
        wrist_p: wristPitchGroup,
        wrist_r: wristRollGroup,
        gripper: gripperGroup
    };

    // Смещаем камеру для обзора манипулятора
    camera.position.set(4, 4, 6);
    camera.lookAt(0, 2, 0);

    console.log("[DOOM] 6-DOF манипулятор загружен. Группы доступны в window.robotGroups");
})();
