/**
 * Parameter schemas and preset configurations for the stylized UAV airframe.
 * All units are normalized or in meters/degrees.
 */

export interface AirframeParams {
  /** Mission Callsign / Tactical Identifier. */
  callsign?: string;
  /** Human-readable Mission Profile Name. */
  missionName?: string;
  /** Tactical mission role description. */
  missionRole?: string;
  /** Total wingspan from tip to tip. */
  span: number;
  /** Wing root chord at centerline. */
  rootChord: number;
  /** Wing tip chord at tip transition. */
  tipChord: number;
  /** Wing leading edge sweep angle in degrees. */
  sweepDeg: number;
  /** Wing dihedral angle in degrees. */
  dihedralDeg: number;
  /** Wing volumetric airfoil thickness multiplier. */
  wingThickness: number;
  /** Forward displacement ratio of the wing along the fuselage (0.15 to 0.35). */
  wingForwardRatio: number;
  /** Total fuselage length from nose to tail boom. */
  fuseLength: number;
  /** Fuselage pod width and height cross-section radius. */
  fuseRadius: number;
  /** Fraction of fuselage dedicated to the blunt rounded nose dome. */
  noseLengthRatio: number;
  /** Fraction of fuselage dedicated to the payload cabin. */
  cabinLengthRatio: number;
  /** Extra width multiplier for the central payload pod. */
  cabinChubbiness: number;
  /** Horizontal stabilizer total span. */
  tailSpan: number;
  /** Vertical tail fin height above fuselage boom. */
  tailFinHeight: number;
  /** Vertical fin leading edge sweep in degrees. */
  tailFinSweep: number;
  /** Normalized bar values (0.0 to 1.0) for the dynamic bar chart graphic. */
  barValues: number[];
}

/** Predefined mission airframe configurations exported from Configurator. */
export const AIRFRAME_PRESETS: AirframeParams[] = [
  {
    callsign: 'DT-ISR-280',
    missionName: 'ISR Long-Endurance',
    missionRole: 'High-altitude loiter & surveillance reconnaissance',
    span: 2.8,
    rootChord: 0.29,
    tipChord: 0.11,
    sweepDeg: 12,
    dihedralDeg: 3,
    wingThickness: 0.17,
    wingForwardRatio: 0.22,
    fuseLength: 1.85,
    fuseRadius: 0.08,
    noseLengthRatio: 0.1,
    cabinLengthRatio: 0.33,
    cabinChubbiness: 1,
    tailSpan: 0.64,
    tailFinHeight: 0.31,
    tailFinSweep: 38,
    barValues: [0.62, 0.58, 0.68, 0.52, 0.86, 0.66],
  },
  {
    callsign: 'DT-DASH-170',
    missionName: 'High-Speed Interceptor',
    missionRole: 'Low-level tactical dash & rapid transit',
    span: 1.7,
    rootChord: 0.55,
    tipChord: 0.3,
    sweepDeg: 24.5,
    dihedralDeg: 0,
    wingThickness: 0.17,
    wingForwardRatio: 0.33,
    fuseLength: 1.6,
    fuseRadius: 0.125,
    noseLengthRatio: 0.1,
    cabinLengthRatio: 0.43,
    cabinChubbiness: 1,
    tailSpan: 0.58,
    tailFinHeight: 0.31,
    tailFinSweep: 22,
    barValues: [0.44, 1.0, 0.45, 0.44, 0.4, 1.0],
  },
  {
    callsign: 'DT-CARGO-170',
    missionName: 'Sensor Payload Pod',
    missionRole: 'Internal optical/RF sensor package housing',
    span: 1.7,
    rootChord: 0.55,
    tipChord: 0.08,
    sweepDeg: 24.5,
    dihedralDeg: 1.2,
    wingThickness: 0.17,
    wingForwardRatio: 0.33,
    fuseLength: 1.6,
    fuseRadius: 0.085,
    noseLengthRatio: 0.2,
    cabinLengthRatio: 0.33,
    cabinChubbiness: 1.3,
    tailSpan: 0.62,
    tailFinHeight: 0.26,
    tailFinSweep: 38,
    barValues: [0.68, 0.82, 0.8, 0.2, 0.72, 0.77],
  },
  {
    callsign: 'DT-LOITER-235',
    missionName: 'Extended Patrol',
    missionRole: 'Area boundary monitoring & RF relay',
    span: 2.35,
    rootChord: 0.28,
    tipChord: 0.14,
    sweepDeg: 21.5,
    dihedralDeg: 7.2,
    wingThickness: 0.17,
    wingForwardRatio: 0.26,
    fuseLength: 1.7,
    fuseRadius: 0.08,
    noseLengthRatio: 0.1,
    cabinLengthRatio: 0.24,
    cabinChubbiness: 1,
    tailSpan: 0.62,
    tailFinHeight: 0.26,
    tailFinSweep: 38,
    barValues: [0.68, 0.82, 0.8, 0.5, 0.77, 0.77],
  },
  {
    callsign: 'DT-HEAVY-235',
    missionName: 'Heavy Logistics',
    missionRole: 'Multi-battery payload delivery & austere staging',
    span: 2.35,
    rootChord: 0.55,
    tipChord: 0.3,
    sweepDeg: 21.5,
    dihedralDeg: 0,
    wingThickness: 0.1,
    wingForwardRatio: 0.22,
    fuseLength: 1.7,
    fuseRadius: 0.11,
    noseLengthRatio: 0.27,
    cabinLengthRatio: 0.42,
    cabinChubbiness: 1,
    tailSpan: 0.62,
    tailFinHeight: 0.26,
    tailFinSweep: 38,
    barValues: [0.94, 0.72, 0.85, 0.2, 0.77, 0.77],
  },
  {
    callsign: 'DT-SWARM-090',
    missionName: 'Compact Swarm UAS',
    missionRole: 'Expendable attritable reconnaissance node',
    span: 0.9,
    rootChord: 0.55,
    tipChord: 0.1,
    sweepDeg: 30,
    dihedralDeg: 4.4,
    wingThickness: 0.1,
    wingForwardRatio: 0.28,
    fuseLength: 0.9,
    fuseRadius: 0.11,
    noseLengthRatio: 0.1,
    cabinLengthRatio: 0.24,
    cabinChubbiness: 1,
    tailSpan: 0.32,
    tailFinHeight: 0.18,
    tailFinSweep: 38,
    barValues: [0.94, 0.72, 0.85, 0.2, 0.77, 0.45],
  },
];

/**
 * Linearly interpolates between two numbers.
 *
 * @param a Start value.
 * @param b End value.
 * @param t Progress factor between 0.0 and 1.0.
 * @returns Interpolated number.
 */
function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/**
 * Computes smooth Hermite cubic easing for animation transitions.
 *
 * @param t Progress between 0.0 and 1.0.
 * @returns Eased progress factor.
 */
export function smoothStep(t: number): number {
  const clamped = Math.max(0, Math.min(1, t));
  return clamped * clamped * (3 - 2 * clamped);
}

/**
 * Interpolates between two airframe parameter states.
 *
 * @param a Initial airframe parameters.
 * @param b Target airframe parameters.
 * @param t Progress factor between 0.0 and 1.0.
 * @returns Blended airframe parameters.
 */
export function interpolateParams(
  a: AirframeParams,
  b: AirframeParams,
  t: number
): AirframeParams {
  const eased = smoothStep(t);
  const blendedBars = a.barValues.map((val, idx) =>
    lerp(val, b.barValues[idx] ?? val, eased)
  );

  return {
    span: lerp(a.span, b.span, eased),
    rootChord: lerp(a.rootChord, b.rootChord, eased),
    tipChord: lerp(a.tipChord, b.tipChord, eased),
    sweepDeg: lerp(a.sweepDeg, b.sweepDeg, eased),
    dihedralDeg: lerp(a.dihedralDeg, b.dihedralDeg, eased),
    wingThickness: lerp(a.wingThickness, b.wingThickness, eased),
    wingForwardRatio: lerp(a.wingForwardRatio, b.wingForwardRatio, eased),
    fuseLength: lerp(a.fuseLength, b.fuseLength, eased),
    fuseRadius: lerp(a.fuseRadius, b.fuseRadius, eased),
    noseLengthRatio: lerp(a.noseLengthRatio, b.noseLengthRatio, eased),
    cabinLengthRatio: lerp(a.cabinLengthRatio, b.cabinLengthRatio, eased),
    cabinChubbiness: lerp(a.cabinChubbiness, b.cabinChubbiness, eased),
    tailSpan: lerp(a.tailSpan, b.tailSpan, eased),
    tailFinHeight: lerp(a.tailFinHeight, b.tailFinHeight, eased),
    tailFinSweep: lerp(a.tailFinSweep, b.tailFinSweep, eased),
    barValues: blendedBars,
    callsign: eased < 0.5 ? a.callsign : b.callsign,
    missionName: eased < 0.5 ? a.missionName : b.missionName,
    missionRole: eased < 0.5 ? a.missionRole : b.missionRole,
  };
}
