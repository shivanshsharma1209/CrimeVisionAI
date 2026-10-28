/**
 * CrimeVision AI - Conceptual 3D Forensic Scene Visualization
 * Uses Three.js to render detected forensic entities in a 3D coordinate space.
 */

class Forensic3DScene {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.entities = [];
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.gridHelper = null;
        this.initialized = false;
        this.selectedEntity = null;

        if (this.container) {
            this.init();
        }
    }

    init() {
        if (this.initialized) return;

        const width = this.container.clientWidth || 800;
        const height = this.container.clientHeight || 550;

        // 1. Scene & Background
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x070a13);
        this.scene.fog = new THREE.FogExp2(0x070a13, 0.015);

        // 2. Camera
        this.camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
        this.camera.position.set(0, 35, 60);

        // 3. Renderer
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.container.appendChild(this.renderer.domElement);

        // 4. Orbit Controls
        if (typeof THREE.OrbitControls !== "undefined") {
            this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
            this.controls.enableDamping = true;
            this.controls.dampingFactor = 0.05;
            this.controls.maxPolarAngle = Math.PI / 2 - 0.02; // Don't go below floor
            this.controls.minDistance = 10;
            this.controls.maxDistance = 140;
        }

        // 5. Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);

        const dirLight = new THREE.DirectionalLight(0x00f0ff, 0.8);
        dirLight.position.set(30, 60, 40);
        dirLight.castShadow = true;
        this.scene.add(dirLight);

        const pointLight = new THREE.PointLight(0x38bdf8, 1.2, 100);
        pointLight.position.set(0, 20, 0);
        this.scene.add(pointLight);

        // 6. Ground Grid & Floor Plane
        this.gridHelper = new THREE.GridHelper(100, 50, 0x00f0ff, 0x1e293b);
        this.gridHelper.position.y = 0;
        this.scene.add(this.gridHelper);

        const floorGeo = new THREE.PlaneGeometry(100, 100);
        const floorMat = new THREE.MeshStandardMaterial({
            color: 0x0a0f1d,
            roughness: 0.8,
            metalness: 0.2,
        });
        const floor = new THREE.Mesh(floorGeo, floorMat);
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = -0.05;
        floor.receiveShadow = true;
        this.scene.add(floor);

        // Center Location Marker (Forensic Origin Beacon)
        this.addLocationBeacon(0, 0, 0, "Incident Origin (Sector 4)");

        // 7. Event Listeners
        window.addEventListener("resize", () => this.onWindowResize());
        this.renderer.domElement.addEventListener("click", (e) => this.onPointerClick(e));

        this.initialized = true;
        this.animate();
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        if (this.controls) {
            this.controls.update();
        }

        // Pulse entity halos
        const time = Date.now() * 0.003;
        for (const ent of this.entities) {
            if (ent.ring) {
                ent.ring.rotation.z = time * 0.5;
                const scale = 1 + Math.sin(time + ent.id) * 0.08;
                ent.ring.scale.set(scale, scale, scale);
            }
        }

        this.renderer.render(this.scene, this.camera);
    }

    onWindowResize() {
        if (!this.container || !this.renderer || !this.camera) return;
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    resetCamera() {
        if (this.camera && this.controls) {
            this.camera.position.set(0, 35, 60);
            this.controls.target.set(0, 0, 0);
            this.controls.update();
        }
    }

    toggleGrid() {
        if (this.gridHelper) {
            this.gridHelper.visible = !this.gridHelper.visible;
        }
    }

    clearSceneEntities() {
        for (const ent of this.entities) {
            this.scene.remove(ent.mesh);
            if (ent.ring) this.scene.remove(ent.ring);
        }
        this.entities = [];
    }

    addLocationBeacon(x, y, z, label) {
        const beaconGeo = new THREE.CylinderGeometry(0.2, 1.2, 5, 16);
        const beaconMat = new THREE.MeshStandardMaterial({
            color: 0xf59e0b,
            emissive: 0xf59e0b,
            emissiveIntensity: 0.4,
        });
        const beacon = new THREE.Mesh(beaconGeo, beaconMat);
        beacon.position.set(x, y + 2.5, z);
        this.scene.add(beacon);

        // Ground ring
        const ringGeo = new THREE.RingGeometry(1.5, 2.0, 32);
        const ringMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b, side: THREE.DoubleSide });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = -Math.PI / 2;
        ring.position.set(x, 0.05, z);
        this.scene.add(ring);
    }

    populateFromCaseData(detections, timelineEvents) {
        this.clearSceneEntities();

        if (!detections || detections.length === 0) {
            // Add default conceptual demo layout if no detections yet
            this.addEntityNode({ type: "person", label: "Person 1", conf: 0.94, x: -12, z: 8 });
            this.addEntityNode({ type: "person", label: "Person 2", conf: 0.91, x: -6, z: 12 });
            this.addEntityNode({ type: "truck", label: "Cargo Transport", conf: 0.96, x: 18, z: -10 });
            this.addEntityNode({ type: "object", label: "Unattended Backpack", conf: 0.82, x: -14, z: 6 });
            return;
        }

        // Layout entities in a conceptual forensic radial layout
        const count = detections.length;
        detections.forEach((det, idx) => {
            const angle = (idx / Math.max(1, count)) * Math.PI * 2;
            const radius = 15 + (idx % 3) * 8;
            const x = Math.cos(angle) * radius;
            const z = Math.sin(angle) * radius;

            const name = (det.object_name || "object").toLowerCase();
            let entType = "object";
            if (name.includes("person") || name.includes("man") || name.includes("woman")) {
                entType = "person";
            } else if (name.includes("car") || name.includes("truck") || name.includes("vehicle") || name.includes("bus")) {
                entType = "vehicle";
            } else if (det.is_weapon_candidate || name.includes("knife") || name.includes("scissors")) {
                entType = "weapon";
            }

            this.addEntityNode({
                id: det.id,
                type: entType,
                label: `${det.object_name.toUpperCase()} (ID: ${det.id || idx + 1})`,
                conf: det.confidence,
                x: x,
                z: z,
                model: det.model_name || "RT-DETR",
                bbox: det.bbox || [],
                timestamp: det.timestamp,
            });
        });
    }

    addEntityNode(data) {
        let geo, mat, color, height;

        if (data.type === "person") {
            geo = new THREE.CapsuleGeometry(1.2, 3.5, 8, 16);
            color = 0x00f0ff; // Cyan
            height = 3.5;
        } else if (data.type === "vehicle") {
            geo = new THREE.BoxGeometry(7, 4, 12);
            color = 0x10b981; // Emerald
            height = 2;
        } else if (data.type === "weapon") {
            geo = new THREE.OctahedronGeometry(2.0);
            color = 0xef4444; // Neon Red
            height = 2;
        } else {
            geo = new THREE.SphereGeometry(1.6, 16, 16);
            color = 0x38bdf8; // Blue
            height = 1.6;
        }

        mat = new THREE.MeshStandardMaterial({
            color: color,
            roughness: 0.3,
            metalness: 0.4,
            emissive: color,
            emissiveIntensity: 0.25,
        });

        const mesh = new THREE.Mesh(geo, mat);
        mesh.position.set(data.x, height, data.z);
        mesh.castShadow = true;
        mesh.userData = data;

        // Ground target ring
        const ringGeo = new THREE.RingGeometry(2.5, 3.0, 32);
        const ringMat = new THREE.MeshBasicMaterial({
            color: color,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.6,
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = -Math.PI / 2;
        ring.position.set(data.x, 0.05, data.z);

        this.scene.add(mesh);
        this.scene.add(ring);

        this.entities.push({
            id: data.id || Math.random(),
            mesh: mesh,
            ring: ring,
            data: data,
        });
    }

    onPointerClick(event) {
        const rect = this.renderer.domElement.getBoundingClientRect();
        this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        this.raycaster.setFromCamera(this.mouse, this.camera);
        const meshes = this.entities.map((e) => e.mesh);
        const intersects = this.raycaster.intersectObjects(meshes);

        if (intersects.length > 0) {
            const hitMesh = intersects[0].object;
            this.showInspector(hitMesh.userData);
        }
    }

    showInspector(data) {
        const panel = document.getElementById("scene3d-inspector-content");
        if (!panel) return;

        const tsStr = data.timestamp !== null && data.timestamp !== undefined ? `${data.timestamp}s` : "Static Frame";
        const confPct = Math.round((data.conf || 0.85) * 100);

        panel.innerHTML = `
            <div class="mb-2">
                <span class="badge bg-info text-dark font-monospace">${data.type.toUpperCase()}</span>
                <span class="text-white fw-bold ms-1">${data.label}</span>
            </div>
            <div class="small text-secondary mb-1">
                <strong>Detection Confidence:</strong> <span class="text-success">${confPct}%</span>
            </div>
            <div class="small text-secondary mb-1">
                <strong>Timestamp:</strong> <span class="text-warning">${tsStr}</span>
            </div>
            <div class="small text-secondary mb-1">
                <strong>Conceptual Coordinates:</strong> [X: ${data.x.toFixed(1)}, Z: ${data.z.toFixed(1)}]
            </div>
            <div class="small text-secondary mb-2">
                <strong>Model:</strong> ${data.model || "RT-DETR"}
            </div>
            <div class="p-2 rounded font-monospace" style="background: rgba(7, 10, 19, 0.8); font-size: 0.72rem; color: #94a3b8;">
                Disclaimer: Spatial layout represents conceptual node clustering. Absolute metric telemetry requires multi-calibrated sensor cameras.
            </div>
        `;
    }
}
