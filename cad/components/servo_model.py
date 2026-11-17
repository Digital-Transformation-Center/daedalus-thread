"""Parametric 3D FreeCAD model for HeeWing T1-S Ranger micro-servos."""
import math
import FreeCAD as App
import Part

# Nominal physical dimensions (mm) for supported side-mounted micro-servos.
# HeeWing_FX5G represents the HeeWing FX-5G / FX-7G (7g metal-gear) sub-micro
# servo used in the HeeWing T1 / T1-S Ranger (ES9051 / ES9052MD footprint).
SERVO_SPECS = {
    "HeeWing_FX5G": {
        "body_length_x": 20.0,       # Main case length along chord (X)
        "body_height_y": 20.2,       # Main case height along span (Y), base to shoulder
        "body_thickness_z": 8.4,     # Case thickness into wing depth (Z)
        "corner_radius": 0.4,        # Outer case corner fillet radius
        "ear_span_x": 27.6,          # Total mounting ear span (3.8 mm per side)
        "ear_thickness_y": 1.6,      # Mounting ear flange thickness along Y
        "ear_y_from_base": 15.0,     # Ear center distance from servo base (-Y)
        "ear_hole_span_x": 23.6,     # Center-to-center mounting hole distance
        "ear_hole_dia": 2.0,         # Mounting screw hole diameter
        "gear_cap_length_x": 10.4,   # Stepped upper gear housing length (X)
        "gear_cap_height_y": 2.4,    # Stepped upper gear housing height (+Y)
        "spline_x_offset": 5.0,      # Output shaft offset aft (+X) from body center
        "boss_dia": 8.4,             # Primary output gear boss diameter
        "boss_protrusion_y": 2.6,    # Primary boss protrusion (+Y) beyond body_height_y
        "aux_boss_dia": 4.8,         # Secondary gear-train boss diameter
        "aux_boss_x_offset": 0.8,    # Secondary boss X offset from body center
        "aux_boss_protrusion_y": 2.0,# Secondary boss protrusion (+Y)
        "spline_dia": 4.2,           # Output spline shaft diameter
        "spline_protrusion_y": 3.2,  # Spline protrusion (+Y) beyond boss face
        "wire_boot_w_x": 3.0,        # Wire strain-relief boot width (X)
        "wire_boot_h_z": 2.2,        # Wire strain-relief boot thickness (Z)
        "wire_boot_len_y": 2.2,      # Wire boot protrusion (-Y) from base
        "wire_boot_x_offset": -8.0,  # Wire boot X offset from body center (inboard-fore)
        "wire_width": 2.4,           # 3-pin ribbon wire width (mm)
        "wire_thickness": 0.6,       # 3-pin ribbon wire thickness (mm)
        "max_wire_length": 200.0,    # Aileron lead length budget (mm, FX-7G-180)
    },
    "SG90": {
        "body_length_x": 22.5,
        "body_height_y": 22.5,
        "body_thickness_z": 12.0,
        "corner_radius": 0.5,
        "ear_span_x": 32.0,
        "ear_thickness_y": 2.5,
        "ear_y_from_base": 16.0,
        "ear_hole_span_x": 27.5,
        "ear_hole_dia": 2.2,
        "gear_cap_length_x": 12.0,
        "gear_cap_height_y": 2.5,
        "spline_x_offset": 5.5,
        "boss_dia": 11.6,
        "boss_protrusion_y": 3.0,
        "aux_boss_dia": 5.5,
        "aux_boss_x_offset": 0.5,
        "aux_boss_protrusion_y": 2.2,
        "spline_dia": 4.8,
        "spline_protrusion_y": 3.5,
        "wire_boot_w_x": 3.4,
        "wire_boot_h_z": 2.4,
        "wire_boot_len_y": 2.5,
        "wire_boot_x_offset": -9.0,
        "wire_width": 2.6,
        "wire_thickness": 0.8,
        "max_wire_length": 200.0,
    },
}


def _make_rounded_xy_prism(x_min, x_max, y_min, y_max, z_min, z_max, radius):
    """Creates a vertical prism with rounded XY corners between z_min and z_max."""
    w = x_max - x_min
    h = y_max - y_min
    dz = z_max - z_min
    r = min(float(radius), w * 0.45, h * 0.45)
    if r <= 1e-4:
        return Part.makeBox(w, h, dz, App.Vector(x_min, y_min, z_min))

    s2 = math.sqrt(0.5)
    c = r * (1.0 - s2)
    pts = [
        App.Vector(x_min + r, y_min, z_min),
        App.Vector(x_max - r, y_min, z_min),
        App.Vector(x_max - c, y_min + c, z_min),
        App.Vector(x_max, y_min + r, z_min),
        App.Vector(x_max, y_max - r, z_min),
        App.Vector(x_max - c, y_max - c, z_min),
        App.Vector(x_max - r, y_max, z_min),
        App.Vector(x_min + r, y_max, z_min),
        App.Vector(x_min + c, y_max - c, z_min),
        App.Vector(x_min, y_max - r, z_min),
        App.Vector(x_min, y_min + r, z_min),
        App.Vector(x_min + c, y_min + c, z_min),
    ]
    edges = [
        Part.LineSegment(pts[0], pts[1]).toShape(),
        Part.Arc(pts[1], pts[2], pts[3]).toShape(),
        Part.LineSegment(pts[3], pts[4]).toShape(),
        Part.Arc(pts[4], pts[5], pts[6]).toShape(),
        Part.LineSegment(pts[6], pts[7]).toShape(),
        Part.Arc(pts[7], pts[8], pts[9]).toShape(),
        Part.LineSegment(pts[9], pts[10]).toShape(),
        Part.Arc(pts[10], pts[11], pts[0]).toShape(),
    ]
    face = Part.Face(Part.Wire(edges))
    return face.extrude(App.Vector(0, 0, dz))


def _make_y_cylinder_press_sweep(cx, y_start, length_y, cz, radius, z_top):
    """Creates a Y-axis cylinder fused with a vertical (+Z) clearance sweep.

    Below cz, the solid matches the lower semicircle of the cylinder so the
    feature seats into a curved cradle. Above cz, it sweeps straight up (+Z)
    to z_top so pressing the servo vertically (-Z) encounters zero undercuts.
    """
    cyl = Part.makeCylinder(
        radius,
        length_y,
        App.Vector(cx, y_start, cz),
        App.Vector(0, 1, 0),
    )
    sweep_h = max(0.5, z_top - cz)
    sweep_box = Part.makeBox(
        2.0 * radius,
        length_y,
        sweep_h,
        App.Vector(cx - radius, y_start, cz),
    )
    return cyl.fuse(sweep_box)


class ServoModel:
    """Builds a clean 3D FreeCAD servo solid and its press-in wing cutter."""

    def __init__(self, servo_type="HeeWing_FX5G"):
        if servo_type not in SERVO_SPECS:
            servo_type = "HeeWing_FX5G"
        self.servo_type = servo_type
        self.specs = SERVO_SPECS[servo_type]

    def get_spline_center_xy(self, center_x, center_y):
        """Returns global (x, y) of the output spline tip."""
        s = self.specs
        sx = center_x + s["spline_x_offset"]
        sy = (
            center_y
            + s["body_height_y"] / 2.0
            + s["boss_protrusion_y"]
            + s["spline_protrusion_y"]
        )
        return sx, sy

    def get_wire_boot_xy(self, center_x, center_y):
        """Returns global (x, y) center of the inboard wire exit boot."""
        s = self.specs
        wx = center_x + s["wire_boot_x_offset"]
        wy = center_y - s["body_height_y"] / 2.0 - s["wire_boot_len_y"] * 0.5
        return wx, wy

    def build_nominal_solid(self, center_x, center_y, floor_z):
        """Builds the clean nominal 3D FreeCAD solid of the side-mounted servo.

        Args:
            center_x: Chordwise center X (mm).
            center_y: Spanwise center Y (mm).
            floor_z: Bottom seating Z coordinate (mm).

        Returns:
            Part.Shape: Watertight solid representing the physical servo.
        """
        s = self.specs
        bx = s["body_length_x"]
        by = s["body_height_y"]
        bz = s["body_thickness_z"]
        cz = floor_z + bz / 2.0

        # 1. Main case body with filleted corners
        body = _make_rounded_xy_prism(
            center_x - bx / 2.0,
            center_x + bx / 2.0,
            center_y - by / 2.0,
            center_y + by / 2.0,
            floor_z,
            floor_z + bz,
            s["corner_radius"],
        )

        # 2. Mounting ears (fore/aft flanges) with screw holes
        ear_y_c = center_y - by / 2.0 + s["ear_y_from_base"]
        ear_y_min = ear_y_c - s["ear_thickness_y"] / 2.0
        ear_y_max = ear_y_c + s["ear_thickness_y"] / 2.0
        ears = Part.makeBox(
            s["ear_span_x"],
            s["ear_thickness_y"],
            bz,
            App.Vector(center_x - s["ear_span_x"] / 2.0, ear_y_min, floor_z),
        )
        hole_r = s["ear_hole_dia"] / 2.0
        for sign in (-1.0, 1.0):
            hx = center_x + sign * (s["ear_hole_span_x"] / 2.0)
            hole = Part.makeCylinder(
                hole_r,
                s["ear_thickness_y"] + 1.0,
                App.Vector(hx, ear_y_min - 0.5, cz),
                App.Vector(0, 1, 0),
            )
            ears = ears.cut(hole)

        solid = body.fuse(ears)

        # 3. Stepped upper gear housing on the +Y output face
        y_top_body = center_y + by / 2.0
        spline_x = center_x + s["spline_x_offset"]
        cap_x_min = max(center_x - bx / 2.0, spline_x - s["gear_cap_length_x"] / 2.0)
        cap_x_max = min(center_x + bx / 2.0, spline_x + s["gear_cap_length_x"] / 2.0)
        gear_cap = _make_rounded_xy_prism(
            cap_x_min,
            cap_x_max,
            y_top_body - 0.5,
            y_top_body + s["gear_cap_height_y"],
            floor_z,
            floor_z + bz,
            0.3,
        )
        solid = solid.fuse(gear_cap)

        # 4. Primary output gear boss, secondary gear boss, and output spline
        boss = Part.makeCylinder(
            s["boss_dia"] / 2.0,
            s["boss_protrusion_y"] + 0.5,
            App.Vector(spline_x, y_top_body - 0.5, cz),
            App.Vector(0, 1, 0),
        )
        aux_boss = Part.makeCylinder(
            s["aux_boss_dia"] / 2.0,
            s["aux_boss_protrusion_y"] + 0.5,
            App.Vector(center_x + s["aux_boss_x_offset"], y_top_body - 0.5, cz),
            App.Vector(0, 1, 0),
        )
        spline = Part.makeCylinder(
            s["spline_dia"] / 2.0,
            s["spline_protrusion_y"] + 0.5,
            App.Vector(spline_x, y_top_body + s["boss_protrusion_y"] - 0.5, cz),
            App.Vector(0, 1, 0),
        )
        solid = solid.fuse(boss).fuse(aux_boss).fuse(spline)

        # 5. Wire exit strain-relief boot at inboard bottom corner
        y_bot_body = center_y - by / 2.0
        boot = Part.makeBox(
            s["wire_boot_w_x"],
            s["wire_boot_len_y"] + 0.5,
            s["wire_boot_h_z"],
            App.Vector(
                center_x + s["wire_boot_x_offset"] - s["wire_boot_w_x"] / 2.0,
                y_bot_body - s["wire_boot_len_y"],
                cz - s["wire_boot_h_z"] / 2.0,
            ),
        )
        solid = solid.fuse(boot)
        return solid

    def build_press_cutter_solid(self, center_x, center_y, floor_z, top_z, tolerance=0.12):
        """Builds a zero-undercut press-in (-Z) cutter derived from the servo model.

        Every feature is expanded by `tolerance` per side for a fine friction fit
        and swept vertically upward (+Z) to `top_z` so the servo can be pressed
        straight down into the wing surface without overhanging skin interference.

        Args:
            center_x: Chordwise center X (mm).
            center_y: Spanwise center Y (mm).
            floor_z: Bottom seating Z coordinate (mm).
            top_z: Upper Z bound above the local wing skin (mm).
            tolerance: Per-side friction-fit clearance (mm).

        Returns:
            Part.Shape: Solid boolean cutter for the wing surface.
        """
        s = self.specs
        tol = float(tolerance)
        bx = s["body_length_x"]
        by = s["body_height_y"]
        bz = s["body_thickness_z"]
        cz = floor_z + bz / 2.0
        seat_z = floor_z - tol

        # 1. Main body press-in sweep
        body_cut = _make_rounded_xy_prism(
            center_x - bx / 2.0 - tol,
            center_x + bx / 2.0 + tol,
            center_y - by / 2.0 - tol,
            center_y + by / 2.0 + tol,
            seat_z,
            top_z,
            s["corner_radius"] + tol,
        )

        # 2. Mounting ear slots swept to top_z (solid ears without screw-hole islands
        #    so the ears press cleanly into recessed shoulder pockets)
        ear_y_c = center_y - by / 2.0 + s["ear_y_from_base"]
        ears_cut = Part.makeBox(
            s["ear_span_x"] + 2.0 * tol,
            s["ear_thickness_y"] + 2.0 * tol,
            top_z - seat_z,
            App.Vector(
                center_x - s["ear_span_x"] / 2.0 - tol,
                ear_y_c - s["ear_thickness_y"] / 2.0 - tol,
                seat_z,
            ),
        )
        cutter = body_cut.fuse(ears_cut)

        # 3. Stepped upper gear housing sweep
        y_top_body = center_y + by / 2.0
        spline_x = center_x + s["spline_x_offset"]
        cap_x_min = max(center_x - bx / 2.0, spline_x - s["gear_cap_length_x"] / 2.0) - tol
        cap_x_max = min(center_x + bx / 2.0, spline_x + s["gear_cap_length_x"] / 2.0) + tol
        cap_cut = _make_rounded_xy_prism(
            cap_x_min,
            cap_x_max,
            y_top_body - 0.5,
            y_top_body + s["gear_cap_height_y"] + tol,
            seat_z,
            top_z,
            0.3 + tol,
        )
        cutter = cutter.fuse(cap_cut)

        # 4. Cylindrical output gear boss, secondary boss, and spline press-sweeps
        boss_cut = _make_y_cylinder_press_sweep(
            spline_x,
            y_top_body - 0.5,
            s["boss_protrusion_y"] + 0.5 + tol,
            cz,
            s["boss_dia"] / 2.0 + tol,
            top_z,
        )
        aux_cut = _make_y_cylinder_press_sweep(
            center_x + s["aux_boss_x_offset"],
            y_top_body - 0.5,
            s["aux_boss_protrusion_y"] + 0.5 + tol,
            cz,
            s["aux_boss_dia"] / 2.0 + tol,
            top_z,
        )
        spline_cut = _make_y_cylinder_press_sweep(
            spline_x,
            y_top_body + s["boss_protrusion_y"] - 0.5,
            s["spline_protrusion_y"] + 0.5 + tol,
            cz,
            s["spline_dia"] / 2.0 + tol,
            top_z,
        )
        cutter = cutter.fuse(boss_cut).fuse(aux_cut).fuse(spline_cut)

        # 5. Wire exit boot press-sweep (floor at boot bottom, swept up to top_z)
        y_bot_body = center_y - by / 2.0
        boot_z_min = cz - s["wire_boot_h_z"] / 2.0 - tol
        boot_cut = Part.makeBox(
            s["wire_boot_w_x"] + 2.0 * tol,
            s["wire_boot_len_y"] + 0.5 + tol,
            top_z - boot_z_min,
            App.Vector(
                center_x + s["wire_boot_x_offset"] - s["wire_boot_w_x"] / 2.0 - tol,
                y_bot_body - s["wire_boot_len_y"] - tol,
                boot_z_min,
            ),
        )
        return cutter.fuse(boot_cut)

    def export_reference_step(self, step_path):
        """Exports the nominal servo solid centered at the origin to a STEP file."""
        solid = self.build_nominal_solid(0.0, 0.0, 0.0)
        solid.exportStep(step_path)
        return step_path
