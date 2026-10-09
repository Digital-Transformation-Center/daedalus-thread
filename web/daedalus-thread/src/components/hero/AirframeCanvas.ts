/**
 * Three.js controller managing WebGL rendering, studio lighting, materials,
 * continuous parametric morphing loop, and mouse parallax interaction.
 */

import * as THREE from 'three';
import {
  AIRFRAME_PRESETS,
  interpolateParams,
  type AirframeParams,
} from './AirframePresets';
import { createAirframeGeometry, updateAirframePositions } from './AirframeLoft';

/**
 * Controller class managing the 3D airframe viewport with military-grade tactical aesthetics.
 */
export class AirframeCanvasController {
  private container: HTMLElement;
  private renderer: THREE.WebGLRenderer;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private airframeMesh: THREE.Mesh;
  private wireframeMesh: THREE.Mesh;
  private airframeGroup: THREE.Group;
  private radarGridGroup: THREE.Group;
  private geometry: THREE.BufferGeometry;

  // Animation cycle state
  private presetIndex = 0;
  private nextPresetIndex = 1;
  private transitionTimer = 0;
  private readonly morphDuration = 2.0; // seconds to morph between designs
  private readonly dwellDuration = 3.2; // seconds to pause and display design
  private currentParams: AirframeParams;
  private isAutoCycle = true;
  private isWireframeActive = false;

  // Interactive mouse parallax
  private targetRotX = 0.22;
  private targetRotY = -0.45;
  private currentRotX = 0.22;
  private currentRotY = -0.45;

  private isRunning = true;
  private lastTime = 0;
  private resizeObserver: ResizeObserver;
  private targetElement: HTMLElement | null = null;
  private onMouseMoveBound: ((e: MouseEvent) => void) | null = null;
  private onMouseLeaveBound: (() => void) | null = null;

  // Callback listeners for UI telemetry HUD
  private onPresetChangeCallback: ((preset: AirframeParams, index: number) => void) | null = null;

  /**
   * Initializes the 3D scene inside the specified container.
   *
   * @param container Target HTML container element.
   */
  constructor(container: HTMLElement) {
    this.container = container;
    this.currentParams = { ...AIRFRAME_PRESETS[0] };

    // 1. Scene setup
    this.scene = new THREE.Scene();

    // Group holding the airframe for unified transform
    this.airframeGroup = new THREE.Group();
    this.scene.add(this.airframeGroup);

    // 2. Camera setup
    const aspect = container.clientWidth / (container.clientHeight || 1);
    this.camera = new THREE.PerspectiveCamera(36, aspect, 0.1, 100);
    this.camera.position.set(0, 0.35, 3.35);

    // 3. Renderer setup
    this.renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance',
    });
    this.renderer.setSize(container.clientWidth, container.clientHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.25;
    container.appendChild(this.renderer.domElement);

    // 4. Studio Tactical Lighting
    this.setupLighting();

    // 5. Stylized Airframe Mesh & Stealth Composite Materials
    this.geometry = createAirframeGeometry(this.currentParams);

    // Stealth composite dark tactical material (matte carbon-slate)
    const airframeMaterial = new THREE.MeshStandardMaterial({
      color: 0x1e293b,     // Tactical matte dark slate (#1e293b)
      roughness: 0.38,     // Micro-textured stealth composite sheen
      metalness: 0.45,     // Tactical aerospace metallic undertone
      flatShading: false,
    });

    this.airframeMesh = new THREE.Mesh(this.geometry, airframeMaterial);
    this.airframeMesh.rotation.order = 'YXZ';
    this.airframeGroup.add(this.airframeMesh);

    // Cyan glowing CAD wireframe overlay
    const wireframeMaterial = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      wireframe: true,
      transparent: true,
      opacity: 0.0, // Initially hidden until wireframe mode toggled
    });
    this.wireframeMesh = new THREE.Mesh(this.geometry, wireframeMaterial);
    this.wireframeMesh.rotation.order = 'YXZ';
    this.airframeGroup.add(this.wireframeMesh);

    // 6. Tactical Radar Grid Floor Reticle
    this.radarGridGroup = this.createRadarFloor();
    this.scene.add(this.radarGridGroup);

    // Initial framing calculation
    this.updateCameraFraming();

    // 7. Event Listeners & Observers
    this.setupInteractivity();

    this.resizeObserver = new ResizeObserver(() => this.handleResize());
    this.resizeObserver.observe(container);

    // 9. Start Render Loop
    this.lastTime = performance.now();
    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);
  }

  /**
   * Creates a tactical radar / telemetry circular grid underneath the aircraft.
   */
  private createRadarFloor(): THREE.Group {
    const group = new THREE.Group();
    group.position.set(0.0, -0.95, -0.2);

    // Concentric radar circles
    const radii = [0.6, 1.1, 1.7, 2.3];
    radii.forEach((r, idx) => {
      const circleGeo = new THREE.BufferGeometry();
      const segments = 64;
      const pts: THREE.Vector3[] = [];
      for (let i = 0; i <= segments; i++) {
        const theta = (i / segments) * Math.PI * 2;
        pts.push(new THREE.Vector3(Math.cos(theta) * r, 0, Math.sin(theta) * r));
      }
      circleGeo.setFromPoints(pts);
      const circleMat = new THREE.LineBasicMaterial({
        color: 0x38bdf8,
        transparent: true,
        opacity: idx === 1 ? 0.22 : 0.12,
      });
      group.add(new THREE.Line(circleGeo, circleMat));
    });

    // Crosshair axis ticks
    const axesGeo = new THREE.BufferGeometry();
    const axisPts = [
      new THREE.Vector3(-2.4, 0, 0),
      new THREE.Vector3(2.4, 0, 0),
      new THREE.Vector3(0, 0, -2.4),
      new THREE.Vector3(0, 0, 2.4),
    ];
    axesGeo.setFromPoints(axisPts);
    const axesMat = new THREE.LineBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.09,
    });
    group.add(new THREE.LineSegments(axesGeo, axesMat));

    return group;
  }

  /**
   * Sets up tactical aerospace lighting with high-contrast edge rims and specular highlights.
   */
  private setupLighting(): void {
    // Ambient soft fill for shadow detail
    const ambientLight = new THREE.AmbientLight(0x94a3b8, 0.9);
    this.scene.add(ambientLight);

    // Key light: cool defense-grade spotlight from high front-right
    const keyLight = new THREE.DirectionalLight(0xffffff, 1.35);
    keyLight.position.set(2.8, 3.8, 3.2);
    this.scene.add(keyLight);

    // Tactical cyan rim/edge light from rear-left to outline stealth profile
    const cyanRim = new THREE.DirectionalLight(0x38bdf8, 1.4);
    cyanRim.position.set(-3.5, 2.0, -2.5);
    this.scene.add(cyanRim);

    // Fill light: deep slate bounce from below-front
    const fillLight = new THREE.DirectionalLight(0x64748b, 0.65);
    fillLight.position.set(-2.0, -1.0, 2.0);
    this.scene.add(fillLight);
  }

  /**
   * Configures mouse movement tracking across the hero section for gentle 3D parallax.
   */
  private setupInteractivity(): void {
    this.targetElement = (this.container.closest('.dt-hero-section') as HTMLElement) || this.container;

    this.onMouseMoveBound = (event: MouseEvent) => {
      if (!this.targetElement) {
        return;
      }
      const rect = this.targetElement.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;

      this.targetRotY = -0.45 + x * 0.45;
      this.targetRotX = 0.22 - y * 0.25;
    };

    this.onMouseLeaveBound = () => {
      this.targetRotY = -0.45;
      this.targetRotX = 0.22;
    };

    this.targetElement.addEventListener('mousemove', this.onMouseMoveBound);
    this.targetElement.addEventListener('mouseleave', this.onMouseLeaveBound);
  }

  /**
   * Dynamically adjusts camera distance and framing based on viewport aspect ratio.
   * Ensures the airframe remains centered and completely in view without clipping wings.
   */
  private updateCameraFraming(): void {
    const width = this.container.clientWidth;
    const height = this.container.clientHeight;
    if (width === 0 || height === 0) {
      return;
    }

    const aspect = width / height;
    this.camera.aspect = aspect;

    // Base distance tuned for dedicated terminal window framing (aspect ~ 1.2 to 1.5)
    const baseDistance = 3.05;
    const minAspect = 1.35;
    const distanceScale = aspect < minAspect ? minAspect / aspect : 1.0;
    const cameraDistance = baseDistance * distanceScale;

    this.camera.position.set(0, 0.32 * (cameraDistance / baseDistance), cameraDistance);
    this.camera.lookAt(0, 0.02, 0);
    this.camera.updateProjectionMatrix();

    this.renderer.setSize(width, height);
  }

  /**
   * Handles container resize adjustments.
   */
  private handleResize(): void {
    this.updateCameraFraming();
  }

  /**
   * Main animation and render frame.
   *
   * @param now Current high-resolution timestamp.
   */
  private animate(now: number): void {
    if (!this.isRunning) {
      return;
    }

    const delta = Math.min((now - this.lastTime) * 0.001, 0.1);
    this.lastTime = now;

    // 1. Advance morphing cycle
    this.transitionTimer += delta;
    const totalCycle = this.morphDuration + this.dwellDuration;

    if (this.isAutoCycle) {
      if (this.transitionTimer >= totalCycle) {
        this.transitionTimer -= totalCycle;
        this.presetIndex = this.nextPresetIndex;
        this.nextPresetIndex = (this.nextPresetIndex + 1) % AIRFRAME_PRESETS.length;
        if (this.onPresetChangeCallback) {
          this.onPresetChangeCallback(AIRFRAME_PRESETS[this.presetIndex]!, this.presetIndex);
        }
      }
    } else {
      // Manual transition to chosen preset
      if (this.transitionTimer >= this.morphDuration) {
        this.transitionTimer = this.morphDuration;
        this.presetIndex = this.nextPresetIndex;
      }
    }

    // Determine current interpolation progress
    let morphProgress = 0;
    if (this.isAutoCycle) {
      if (this.transitionTimer < this.dwellDuration) {
        morphProgress = 0;
      } else {
        morphProgress = (this.transitionTimer - this.dwellDuration) / this.morphDuration;
      }
    } else {
      morphProgress = Math.min(1.0, this.transitionTimer / this.morphDuration);
    }

    const currentSource = AIRFRAME_PRESETS[this.presetIndex]!;
    const targetSource = AIRFRAME_PRESETS[this.nextPresetIndex]!;
    this.currentParams = interpolateParams(currentSource, targetSource, morphProgress);

    // Update geometry vertices and normal vectors
    updateAirframePositions(this.geometry, this.currentParams);

    // 2. Smooth mouse parallax and subtle aerial hover
    this.currentRotX += (this.targetRotX - this.currentRotX) * 0.05;
    this.currentRotY += (this.targetRotY - this.currentRotY) * 0.05;

    const timeSec = now * 0.001;
    const hoverY = Math.sin(timeSec * 1.2) * 0.035;
    const hoverRoll = Math.sin(timeSec * 0.9) * 0.03;

    // Gentle scale normalization across varying wingspans
    const spanRatio = 2.1 / this.currentParams.span;
    const dynamicScale = Math.pow(spanRatio, 0.42);
    this.airframeGroup.scale.setScalar(dynamicScale);

    this.airframeGroup.position.x = 0.0;
    this.airframeGroup.position.y = hoverY;
    this.airframeGroup.rotation.x = this.currentRotX;
    this.airframeGroup.rotation.y = this.currentRotY;
    this.airframeGroup.rotation.z = hoverRoll;

    // Slowly spin the radar grid for subtle tactical motion
    if (this.radarGridGroup) {
      this.radarGridGroup.rotation.y = timeSec * 0.15;
    }

    // 3. Render frame
    this.renderer.render(this.scene, this.camera);

    requestAnimationFrame(this.animate);
  }

  /**
   * Programmatically selects a mission preset and smoothly morphs toward it.
   *
   * @param index Preset index (0 to N-1).
   */
  public selectPreset(index: number): void {
    if (index < 0 || index >= AIRFRAME_PRESETS.length) return;
    if (index === this.presetIndex && this.transitionTimer >= this.morphDuration) return;

    this.isAutoCycle = false;
    this.nextPresetIndex = index;
    this.transitionTimer = 0;

    if (this.onPresetChangeCallback) {
      this.onPresetChangeCallback(AIRFRAME_PRESETS[index]!, index);
    }
  }

  /**
   * Resumes continuous autonomous preset cycling.
   */
  public resumeAutoCycle(): void {
    this.isAutoCycle = true;
    this.transitionTimer = 0;
  }

  /**
   * Toggles CAD wireframe inspection mode overlay.
   *
   * @returns Boolean indicating whether wireframe is now active.
   */
  public toggleWireframe(): boolean {
    this.isWireframeActive = !this.isWireframeActive;
    const wireMat = this.wireframeMesh.material as THREE.MeshBasicMaterial;
    wireMat.opacity = this.isWireframeActive ? 0.75 : 0.0;
    return this.isWireframeActive;
  }

  /**
   * Registers a listener callback invoked whenever the current airframe preset changes.
   *
   * @param cb Callback function receiving the current preset and index.
   */
  public setOnPresetChange(cb: (preset: AirframeParams, index: number) => void): void {
    this.onPresetChangeCallback = cb;
    if (AIRFRAME_PRESETS[this.presetIndex]) {
      cb(AIRFRAME_PRESETS[this.presetIndex]!, this.presetIndex);
    }
  }

  /**
   * Destroys resources and detaches event handlers.
   */
  public destroy(): void {
    this.isRunning = false;
    this.resizeObserver.disconnect();
    if (this.targetElement && this.onMouseMoveBound && this.onMouseLeaveBound) {
      this.targetElement.removeEventListener('mousemove', this.onMouseMoveBound);
      this.targetElement.removeEventListener('mouseleave', this.onMouseLeaveBound);
    }
    this.geometry.dispose();
    this.renderer.dispose();
    if (this.renderer.domElement.parentElement) {
      this.renderer.domElement.parentElement.removeChild(this.renderer.domElement);
    }
  }
}
