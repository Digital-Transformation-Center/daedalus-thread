"""Top-surface side-mounted clip-in servo pocket generator."""
import FreeCAD as App
import Part

# Specifications for side-mounted micro-servos (mm)
SERVO_PRESETS = {
    # Hee Wing T1S Ranger stock digital micro servo (FX-5g / FX-7g), mounted on its side
    "HeeWing_FX5G": {
        "body_span_y": 21.0,       # 20.6 mm body + 0.4 mm clearance along span (Y)
        "body_chord_x": 20.4,      # 20.0 mm body + 0.4 mm clearance along chord (X)
        "body_depth_z": 8.5,       # 8.2 mm thickness + 0.3 mm clearance into top skin (Z)
        "boss_outboard_y": 4.5,    # 4.0 mm round output boss + 0.5 mm clearance (+Y)
        "boss_dia": 11.0,          # Output gear boss diameter clearance
        "arm_slot_length": 22.0,   # Aft linkage slot toward aileron (+X)
        "arm_slot_width": 4.0,     # Linkage slot width (Y)
        "arm_slot_depth": 8.0,     # Linkage slot depth (Z)
        "snap_overhang": 0.7,      # Printed snap-fit tab overhang (mm)
        "snap_width": 4.5,         # Snap tab width along Y (mm)
        "snap_thickness": 1.2,     # Snap tab thickness in Z (mm)
        "wire_width": 2.4,         # Servo ribbon wire width (mm)
        "wire_thickness": 0.6,     # Servo ribbon wire thickness (mm)
        "max_wire_length": 200.0,  # Total cable length budget (mm)
    },
    "SG90": {
        "body_span_y": 23.0,
        "body_chord_x": 22.5,
        "body_depth_z": 12.5,
        "boss_outboard_y": 4.5,
        "boss_dia": 12.0,
        "arm_slot_length": 22.0,
        "arm_slot_width": 4.0,
        "arm_slot_depth": 9.0,
        "snap_overhang": 0.7,
        "snap_width": 4.5,
        "snap_thickness": 1.2,
        "wire_width": 2.6,
        "wire_thickness": 0.8,
        "max_wire_length": 200.0,
    },
}


class ServoPocket:
    """Generates cutters and snap-fit tabs for a top-surface side-mounted servo."""

    def __init__(self, servo_type="HeeWing_FX5G"):
        if servo_type not in SERVO_PRESETS:
            servo_type = "HeeWing_FX5G"
        self.specs = SERVO_PRESETS[servo_type]

    def create_geometry(self, center_x, center_y, wing_geom):
        """Creates pocket cutter, snap-fit tab solid, and bottom feed-through coordinates.

        Args:
            center_x: Chordwise center X (mm).
            center_y: Spanwise center Y (mm).
            wing_geom: WingGeometry instance.

        Returns:
            tuple: (cutter_solid, snap_tabs_solid, feed_xy, info_dict)
        """
        sy = self.specs["body_span_y"]
        cx = self.specs["body_chord_x"]
        dz = self.specs["body_depth_z"]

        # Sample top and bottom Z across the servo footprint
        z_tops = []
        z_bots = []
        for dx in (-cx / 2.0, 0.0, cx / 2.0):
            for dy in (-sy / 2.0, 0.0, sy / 2.0):
                zb, zt = wing_geom.get_surface_z(center_x + dx, center_y + dy)
                z_bots.append(zb)
                z_tops.append(zt)

        z_top_max = max(z_tops)
        z_top_min = min(z_tops)
        z_bot_min = min(z_bots)

        pocket_floor_z = z_top_min - dz
        pocket_top_z = z_top_max + 2.0

        # 1. Main rectangular body pocket cut downward from top surface (+Z)
        body_box = Part.makeBox(
            cx,
            sy,
            pocket_top_z - pocket_floor_z,
            App.Vector(center_x - cx / 2.0, center_y - sy / 2.0, pocket_floor_z),
        )

        # 2. Outboard (+Y) relief for the 4 mm round output boss (away from fuselage)
        boss_y = self.specs["boss_outboard_y"]
        boss_dia = self.specs["boss_dia"]
        boss_box = Part.makeBox(
            boss_dia,
            boss_y + 1.0,
            pocket_top_z - pocket_floor_z,
            App.Vector(
                center_x - boss_dia / 2.0,
                center_y + sy / 2.0 - 1.0,
                pocket_floor_z,
            ),
        )
        cutter = body_box.fuse(boss_box)

        # 3. Aft linkage horn clearance slot on the +Y output side toward the aileron
        hsl = self.specs["arm_slot_length"]
        hsw = self.specs["arm_slot_width"]
        hsd = self.specs["arm_slot_depth"]
        arm_z_bot = z_top_min - hsd
        arm_slot = Part.makeBox(
            hsl,
            hsw,
            pocket_top_z - arm_z_bot,
            App.Vector(
                center_x,
                center_y + sy / 2.0 + 0.5,
                arm_z_bot,
            ),
        )
        cutter = cutter.fuse(arm_slot)

        # 4. Vertical ribbon-wire feed-through hole at inboard corner down to bottom surface
        feed_x = center_x - cx / 2.0 + 2.5
        feed_y = center_y - sy / 2.0 + 2.5
        feed_w = max(3.4, self.specs["wire_width"] + 1.0)
        feed_t = max(2.0, self.specs["wire_thickness"] + 1.4)
        feed_hole = Part.makeBox(
            feed_w,
            feed_t,
            (pocket_floor_z + 1.0) - (z_bot_min - 2.0),
            App.Vector(feed_x - feed_w / 2.0, feed_y - feed_t / 2.0, z_bot_min - 2.0),
        )
        cutter = cutter.fuse(feed_hole)

        # 5. Printed snap-fit retention tabs on fore (-X) and aft (+X) rims
        overhang = self.specs["snap_overhang"]
        tab_w = self.specs["snap_width"]
        tab_t = self.specs["snap_thickness"]
        embed = 1.5

        _, z_fore = wing_geom.get_surface_z(center_x - cx / 2.0, center_y)
        _, z_aft = wing_geom.get_surface_z(center_x + cx / 2.0, center_y)

        fore_tab = Part.makeBox(
            embed + overhang,
            tab_w,
            tab_t,
            App.Vector(
                center_x - cx / 2.0 - embed,
                center_y - tab_w / 2.0,
                z_fore - tab_t - 0.2,
            ),
        )
        aft_tab = Part.makeBox(
            embed + overhang,
            tab_w,
            tab_t,
            App.Vector(
                center_x + cx / 2.0 - overhang,
                center_y - tab_w / 2.0,
                z_aft - tab_t - 0.2,
            ),
        )
        snap_tabs = fore_tab.fuse(aft_tab)

        info = {
            "x_center_mm": round(center_x, 2),
            "y_center_mm": round(center_y, 2),
            "feed_x_mm": round(feed_x, 2),
            "feed_y_mm": round(feed_y, 2),
            "depth_mm": round(dz, 2),
        }
        return cutter, snap_tabs, (feed_x, feed_y), info
