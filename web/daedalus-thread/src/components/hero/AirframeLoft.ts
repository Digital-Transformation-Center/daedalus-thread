/**
 * Procedural lofting engine for a smooth, stylized, cartoony aerodynamic UAV.
 * Features an authentic semi-ellipsoidal rounded nose dome, C1-matched fuselage zones
 * (zero ridges/creases), forward-placed wings, and high-density smooth vertex topology.
 */

import * as THREE from 'three';
import type { AirframeParams } from './AirframePresets';

/** Resolution settings for geometric lofting (high density for silky smooth surfaces). */
const FUSELAGE_STATIONS = 40;
const FUSELAGE_RADIAL_SEGS = 24;
const WING_SPAN_SEGS = 16;
const WING_CHORD_SEGS = 20;
const FIN_HEIGHT_SEGS = 12;
const FIN_CHORD_SEGS = 16;
const TAIL_SPAN_SEGS = 10;
const TAIL_CHORD_SEGS = 16;

// Fuselage station distribution across the 3 zones
const NOSE_STATIONS = 12;
const CABIN_STATIONS = 14;
const BOOM_STATIONS = FUSELAGE_STATIONS - NOSE_STATIONS - CABIN_STATIONS; // 14 stations

/**
 * Calculates a plump, stylized, cartoon-friendly airfoil thickness at chord position x.
 * Designed with a bulbous leading edge and a softly rounded trailing edge.
 *
 * @param x Normalized chord position between 0.0 (leading edge) and 1.0 (trailing edge).
 * @param thicknessRatio Maximum thickness ratio.
 * @returns Half-thickness coordinate.
 */
function stylizedAirfoilHalfThickness(x: number, thicknessRatio: number): number {
  const clampedX = Math.max(0, Math.min(1, x));
  // Smooth rounded teardrop profile that never pinches to a razor edge
  const leadingBulb = Math.sqrt(clampedX) * 0.35;
  const bodyDecay = -0.16 * clampedX - 0.20 * (clampedX * clampedX);
  const trailingRoundness = 0.05 * Math.sin((1.0 - clampedX) * Math.PI * 0.5);
  return thicknessRatio * (leadingBulb + bodyDecay + trailingRoundness);
}

/**
 * Calculates a gentle aerodynamic camber line elevation.
 *
 * @param x Normalized chord position between 0.0 and 1.0.
 * @param maxCamber Maximum camber height.
 * @returns Camber line elevation.
 */
function airfoilCamber(x: number, maxCamber: number): number {
  const clampedX = Math.max(0, Math.min(1, x));
  return 4.0 * maxCamber * clampedX * (1.0 - clampedX);
}

/**
 * Generates triangle quad indices for a regular grid mesh.
 *
 * @param indices Target index array.
 * @param baseVertex Starting vertex index offset.
 * @param uSegments Number of quad segments along U.
 * @param vSegments Number of quad segments along V.
 * @param isClosedU Whether the U perimeter wraps around.
 */
function buildGridIndices(
  indices: number[],
  baseVertex: number,
  uSegments: number,
  vSegments: number,
  isClosedU: boolean
): void {
  const stride = isClosedU ? uSegments : uSegments + 1;
  for (let v = 0; v < vSegments; v++) {
    for (let u = 0; u < uSegments; u++) {
      const uNext = isClosedU ? (u + 1) % uSegments : u + 1;
      const vNext = v + 1;

      const p0 = baseVertex + v * stride + u;
      const p1 = baseVertex + v * stride + uNext;
      const p2 = baseVertex + vNext * stride + u;
      const p3 = baseVertex + vNext * stride + uNext;

      indices.push(p0, p2, p1);
      indices.push(p1, p2, p3);
    }
  }
}

/**
 * Creates the initial Three.js BufferGeometry with static topology and index buffers.
 *
 * @param initialParams Initial airframe configuration.
 * @returns Prepared Three.js BufferGeometry.
 */
export function createAirframeGeometry(initialParams: AirframeParams): THREE.BufferGeometry {
  const geometry = new THREE.BufferGeometry();

  // Calculate total vertices across all components
  const fuseVerts = FUSELAGE_STATIONS * FUSELAGE_RADIAL_SEGS + 2; // +2 for nose and tail center points
  const wingVertsPerSide = (WING_SPAN_SEGS + 1) * (WING_CHORD_SEGS + 1);
  const totalWingVerts = wingVertsPerSide * 2;
  const finVerts = (FIN_HEIGHT_SEGS + 1) * (FIN_CHORD_SEGS + 1);
  const tailVertsPerSide = (TAIL_SPAN_SEGS + 1) * (TAIL_CHORD_SEGS + 1);
  const totalTailVerts = tailVertsPerSide * 2;

  const totalVertices = fuseVerts + totalWingVerts + finVerts + totalTailVerts;

  const positions = new Float32Array(totalVertices * 3);
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

  const indices: number[] = [];

  // 1. Fuselage body grid indices
  buildGridIndices(indices, 0, FUSELAGE_RADIAL_SEGS, FUSELAGE_STATIONS - 1, true);

  // Fuselage nose and tail cap fans
  const noseCenterIdx = FUSELAGE_STATIONS * FUSELAGE_RADIAL_SEGS;
  const tailCenterIdx = noseCenterIdx + 1;
  for (let u = 0; u < FUSELAGE_RADIAL_SEGS; u++) {
    const uNext = (u + 1) % FUSELAGE_RADIAL_SEGS;
    indices.push(noseCenterIdx, u, uNext);
    const lastRowBase = (FUSELAGE_STATIONS - 1) * FUSELAGE_RADIAL_SEGS;
    indices.push(tailCenterIdx, lastRowBase + uNext, lastRowBase + u);
  }

  // 2. Left & Right Wings
  let currentOffset = fuseVerts;
  buildGridIndices(indices, currentOffset, WING_CHORD_SEGS, WING_SPAN_SEGS, false);
  currentOffset += wingVertsPerSide;
  buildGridIndices(indices, currentOffset, WING_CHORD_SEGS, WING_SPAN_SEGS, false);
  currentOffset += wingVertsPerSide;

  // 3. Vertical Fin
  buildGridIndices(indices, currentOffset, FIN_CHORD_SEGS, FIN_HEIGHT_SEGS, false);
  currentOffset += finVerts;

  // 4. Left & Right Horizontal Stabilizer
  buildGridIndices(indices, currentOffset, TAIL_CHORD_SEGS, TAIL_SPAN_SEGS, false);
  currentOffset += tailVertsPerSide;
  buildGridIndices(indices, currentOffset, TAIL_CHORD_SEGS, TAIL_SPAN_SEGS, false);
  currentOffset += tailVertsPerSide;

  geometry.setIndex(indices);

  // Populate vertex positions
  updateAirframePositions(geometry, initialParams);

  return geometry;
}

/**
 * Updates vertex positions in-place based on the continuous airframe parameters.
 *
 * @param geometry Target Three.js BufferGeometry.
 * @param params Current airframe parameters.
 */
export function updateAirframePositions(
  geometry: THREE.BufferGeometry,
  params: AirframeParams
): void {
  const posAttr = geometry.getAttribute('position') as THREE.BufferAttribute;
  const pos = posAttr.array as Float32Array;
  let ptr = 0;

  // ==========================================
  // 1. FUSELAGE WITH CLASSICAL SEMI-ELLIPSOID NOSE & C1 CONTINUITY
  // ==========================================
  const halfLength = params.fuseLength * 0.5;
  const zNose = halfLength;
  const zTail = -halfLength;

  const noseLength = params.fuseLength * params.noseLengthRatio;
  const cabinLength = params.fuseLength * params.cabinLengthRatio;
  const boomLength = Math.max(0.1, params.fuseLength - noseLength - cabinLength);

  const zNoseEnd = zNose - noseLength;
  const zCabinEnd = zNoseEnd - cabinLength;

  const rBase = params.fuseRadius;
  const rTail = rBase * 0.18;
  const maxBulge = (params.cabinChubbiness - 1.0) * rBase;

  for (let s = 0; s < FUSELAGE_STATIONS; s++) {
    let z = 0;
    let radius = 0;
    let centerY = 0;

    if (s < NOSE_STATIONS) {
      // 1A. AUTHENTIC SEMI-ELLIPSOIDAL ROUNDED NOSE DOME
      // Polar angle theta evenly distributed from small angle to 90 deg (pi/2)
      // This produces uniform surface resolution along the spherical arc
      const theta = ((s + 1) / (NOSE_STATIONS + 0.15)) * (Math.PI * 0.5);
      z = zNose - noseLength * (1.0 - Math.cos(theta));
      radius = rBase * Math.sin(theta);
      centerY = -0.005 * Math.cos(theta);
    } else if (s < NOSE_STATIONS + CABIN_STATIONS) {
      // 1B. PAYLOAD CABIN (Sin^2 belly bulge: 0 derivative at boundaries = zero ridges!)
      const norm = (s - NOSE_STATIONS) / (CABIN_STATIONS - 1); // 0.0 -> 1.0
      z = zNoseEnd - norm * cabinLength;
      // Using sin^2 ensures d(bulge)/d(norm) is strictly 0 at both boundaries!
      const bulge = maxBulge * Math.pow(Math.sin(norm * Math.PI), 2);
      radius = rBase + bulge;
      centerY = 0.0;
    } else {
      // 1C. TAIL BOOM (Cosine taper: 0 derivative at cabin junction = zero ridges!)
      const norm = (s - (NOSE_STATIONS + CABIN_STATIONS)) / (BOOM_STATIONS - 1); // 0.0 -> 1.0
      z = zCabinEnd - norm * boomLength;
      // Cosine taper has derivative 0 at norm=0 and norm=1
      const cosineTaper = 0.5 * (1.0 + Math.cos(norm * Math.PI)); // 1.0 -> 0.0
      radius = rTail + (rBase - rTail) * cosineTaper;
      centerY = 0.035 * (1.0 - cosineTaper);
    }

    const radiusX = radius;
    const radiusY = radius * 0.94; // slightly flattened friendly organic belly

    for (let rad = 0; rad < FUSELAGE_RADIAL_SEGS; rad++) {
      const angle = (rad / FUSELAGE_RADIAL_SEGS) * Math.PI * 2.0;
      pos[ptr++] = radiusX * Math.cos(angle);
      pos[ptr++] = centerY + radiusY * Math.sin(angle);
      pos[ptr++] = z;
    }
  }

  // Smooth spherical nose apex center vertex
  pos[ptr++] = 0.0;
  pos[ptr++] = -0.005;
  pos[ptr++] = zNose;

  // Tail cap center vertex
  pos[ptr++] = 0.0;
  pos[ptr++] = 0.035;
  pos[ptr++] = zTail;

  // ==========================================
  // 2. FORWARD-MOUNTED PLUMP WINGS WITH ROUNDED CAPSULE TIPS
  // ==========================================
  const halfSpan = params.span * 0.5;
  const sweepRad = (params.sweepDeg * Math.PI) / 180.0;
  const dihedralRad = (params.dihedralDeg * Math.PI) / 180.0;
  // Position wing well forward along the fuselage
  const wingZRoot = params.fuseLength * params.wingForwardRatio;

  const buildWingHalf = (sideMultiplier: number) => {
    for (let sp = 0; sp <= WING_SPAN_SEGS; sp++) {
      const spanFrac = sp / WING_SPAN_SEGS; // 0.0 root -> 1.0 tip
      const spanX = sideMultiplier * spanFrac * halfSpan;

      let chord = params.rootChord + (params.tipChord - params.rootChord) * spanFrac;
      let spanThickness = params.wingThickness;

      // Soft pill-shaped rounded wingtip blend
      if (spanFrac > 0.82) {
        const tipT = (spanFrac - 0.82) / 0.18;
        const roundDecay = Math.cos(tipT * (Math.PI * 0.5));
        chord *= 0.75 + 0.25 * roundDecay;
        spanThickness *= 0.65 + 0.35 * roundDecay;
      }

      // Smooth sweep and dihedral
      const sweepZ = -spanFrac * halfSpan * Math.tan(sweepRad);
      const dihedralY = spanFrac * halfSpan * Math.sin(dihedralRad);
      const leZ = wingZRoot + sweepZ;

      for (let ch = 0; ch <= WING_CHORD_SEGS; ch++) {
        const chordFrac = ch / WING_CHORD_SEGS;
        let normChord = 0;
        let isUpper = false;

        if (chordFrac <= 0.5) {
          normChord = 1.0 - chordFrac * 2.0;
          isUpper = false;
        } else {
          normChord = (chordFrac - 0.5) * 2.0;
          isUpper = true;
        }

        const halfT = stylizedAirfoilHalfThickness(normChord, spanThickness) * chord;
        const camber = airfoilCamber(normChord, 0.018) * chord;
        const yOffset = isUpper ? camber + halfT : camber - halfT;
        const zOffset = -normChord * chord;

        pos[ptr++] = spanX;
        pos[ptr++] = dihedralY + yOffset;
        pos[ptr++] = leZ + zOffset;
      }
    }
  };

  buildWingHalf(1.0);  // Right wing
  buildWingHalf(-1.0); // Left wing

  // ==========================================
  // 3. SINGLE SWEPT VERTICAL TAIL FIN
  // ==========================================
  const finZBase = zTail + 0.22;
  const finSweepRad = (params.tailFinSweep * Math.PI) / 180.0;
  const finRootChord = 0.26;
  const finTipChord = 0.13;

  for (let h = 0; h <= FIN_HEIGHT_SEGS; h++) {
    const heightFrac = h / FIN_HEIGHT_SEGS;
    const finY = 0.03 + heightFrac * params.tailFinHeight;
    let chord = finRootChord + (finTipChord - finRootChord) * heightFrac;
    let thicknessRatio = 0.14;

    // Friendly rounded fin top cap
    if (heightFrac > 0.82) {
      const topT = (heightFrac - 0.82) / 0.18;
      const roundDecay = Math.cos(topT * (Math.PI * 0.5));
      chord *= 0.8 + 0.2 * roundDecay;
      thicknessRatio *= 0.6 + 0.4 * roundDecay;
    }

    const sweepOffsetZ = -heightFrac * params.tailFinHeight * Math.tan(finSweepRad);
    const leZ = finZBase + sweepOffsetZ;

    for (let ch = 0; ch <= FIN_CHORD_SEGS; ch++) {
      const chordFrac = ch / FIN_CHORD_SEGS;
      let normChord = 0;
      let isRightSide = false;

      if (chordFrac <= 0.5) {
        normChord = 1.0 - chordFrac * 2.0;
        isRightSide = false;
      } else {
        normChord = (chordFrac - 0.5) * 2.0;
        isRightSide = true;
      }

      const halfT = stylizedAirfoilHalfThickness(normChord, thicknessRatio) * chord;
      const xOffset = isRightSide ? halfT : -halfT;
      const zOffset = -normChord * chord;

      pos[ptr++] = xOffset;
      pos[ptr++] = finY;
      pos[ptr++] = leZ + zOffset;
    }
  }

  // ==========================================
  // 4. HORIZONTAL STABILIZER (LEFT & RIGHT)
  // ==========================================
  const halfTailSpan = params.tailSpan * 0.5;
  const tailZBase = zTail + 0.16;
  const tailRootChord = 0.20;
  const tailTipChord = 0.11;

  const buildTailHalf = (sideMultiplier: number) => {
    for (let sp = 0; sp <= TAIL_SPAN_SEGS; sp++) {
      const spanFrac = sp / TAIL_SPAN_SEGS;
      const tailX = sideMultiplier * spanFrac * halfTailSpan;
      let chord = tailRootChord + (tailTipChord - tailRootChord) * spanFrac;
      let thicknessRatio = 0.13;

      if (spanFrac > 0.82) {
        const tipT = (spanFrac - 0.82) / 0.18;
        const roundDecay = Math.cos(tipT * (Math.PI * 0.5));
        chord *= 0.8 + 0.2 * roundDecay;
        thicknessRatio *= 0.6 + 0.4 * roundDecay;
      }

      const sweepZ = -spanFrac * halfTailSpan * 0.14;
      const leZ = tailZBase + sweepZ;

      for (let ch = 0; ch <= TAIL_CHORD_SEGS; ch++) {
        const chordFrac = ch / TAIL_CHORD_SEGS;
        let normChord = 0;
        let isUpper = false;

        if (chordFrac <= 0.5) {
          normChord = 1.0 - chordFrac * 2.0;
          isUpper = false;
        } else {
          normChord = (chordFrac - 0.5) * 2.0;
          isUpper = true;
        }

        const halfT = stylizedAirfoilHalfThickness(normChord, thicknessRatio) * chord;
        const yOffset = isUpper ? halfT : -halfT;
        const zOffset = -normChord * chord;

        pos[ptr++] = tailX;
        pos[ptr++] = 0.03 + yOffset;
        pos[ptr++] = leZ + zOffset;
      }
    }
  };

  buildTailHalf(1.0);  // Right stabilizer
  buildTailHalf(-1.0); // Left stabilizer

  posAttr.needsUpdate = true;
  geometry.computeVertexNormals();
}
