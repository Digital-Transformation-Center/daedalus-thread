"""Servo mounting pocket generator and preset specifications."""
import math
import FreeCAD as App
import Part

# Specifications for common micro-servos (mm)
SERVO_PRESETS = {
    # Hee Wing T1 Ranger stock digital micro servo (FX-5g / FX-7g)
    "HeeWing_FX5G": {
        "pocket_length": 23.0,     # Length along X (chordwise)
        "pocket_width": 12.5,      # Width along Y (spanwise)
        "pocket_depth": 14.0,      # Pocket depth into wing underside
        "flange_length": 32.0,     # Flange ear length along X
        "flange_width": 12.5,      # Flange ear width
        "flange_depth": 4.0,       # Flange ear step depth
        "arm_slot_length": 24.0,   # Linkage arm slot extending aft toward aileron
        "arm_slot_width": 3.5,     # Slot width for servo horn
        "arm_slot_depth": 10.0,    # Slot depth
        "wire_slot_width": 14.0,   # Flat wire/connector passage width (chordwise)
        "wire_slot_height": 5.0,   # Flat wire/connector passage height (thickness)
    },
    "SG90": {
        "pocket_length": 23.5,
        "pocket_width": 12.5,
        "pocket_depth": 16.0,
        "flange_length": 32.5,
        "flange_width": 12.5,
        "flange_depth": 4.0,
        "arm_slot_length": 24.0,
        "arm_slot_width": 3.5,
        "arm_slot_depth": 10.0,
        "wire_slot_width": 14.0,
        "wire_slot_height": 5.0,
    }
}

class ServoPocket:
    """Generates cutter solids for servo pocket, flat wire conduit, and linkage slot."""

    def __init__(self, servo_type="HeeWing_FX5G"):
        if servo_type not in SERVO_PRESETS:
            servo_type = "HeeWing_FX5G"
        self.specs = SERVO_PRESETS[servo_type]

    def create_cutter(self, center_pos, wing_bottom_z, wing_geom):
        """Creates a boolean cutter solid for the servo bay, flat wire channel, and horn slot.
        
        Args:
            center_pos: App.Vector(x, y, z) servo center location
            wing_bottom_z: Bottom skin Z level at the servo location
            wing_geom: WingGeometry instance for station and dihedral tracking
            
        Returns:
            Part.Shape: Combined cutter shape to subtract from the main wing.
        """
        l = self.specs["pocket_length"]
        w = self.specs["pocket_width"]
        d = self.specs["pocket_depth"]

        # 1. Main servo body pocket from bottom skin upward into wing
        z_start = wing_bottom_z - 2.0
        body_box = Part.makeBox(
            l, w, d + 2.0,
            App.Vector(center_pos.x - (l / 2.0), center_pos.y - (w / 2.0), z_start)
        )

        # 2. Mounting flange ears
        fl_len = self.specs["flange_length"]
        fl_w = self.specs["flange_width"]
        fl_d = self.specs["flange_depth"]
        flange_box = Part.makeBox(
            fl_len, fl_w, fl_d + 2.0,
            App.Vector(center_pos.x - (fl_len / 2.0), center_pos.y - (fl_w / 2.0), z_start)
        )
        pocket = body_box.fuse(flange_box)

        # 3. Servo horn linkage slot extending aft toward the aileron
        hsl = self.specs["arm_slot_length"]
        hsw = self.specs["arm_slot_width"]
        hsd = self.specs["arm_slot_depth"]
        arm_slot = Part.makeBox(
            hsl, hsw, hsd + 2.0,
            App.Vector(center_pos.x, center_pos.y - (hsw / 2.0), z_start)
        )
        pocket = pocket.fuse(arm_slot)

        # 4. Flat rectangular wire and connector conduit running to the wing root
        # Fits standard 3-pin servo connectors (typically 8mm x 2.5mm or 14mm x 4mm)
        sw = self.specs["wire_slot_width"]
        sh = self.specs["wire_slot_height"]

        # Servo station cross-section
        w1 = Part.makePolygon([
            App.Vector(center_pos.x - sw / 2.0, center_pos.y, wing_bottom_z + 2.0),
            App.Vector(center_pos.x + sw / 2.0, center_pos.y, wing_bottom_z + 2.0),
            App.Vector(center_pos.x + sw / 2.0, center_pos.y, wing_bottom_z + 2.0 + sh),
            App.Vector(center_pos.x - sw / 2.0, center_pos.y, wing_bottom_z + 2.0 + sh),
            App.Vector(center_pos.x - sw / 2.0, center_pos.y, wing_bottom_z + 2.0)
        ])

        # Wing root cross-section (Y = -5mm past root rib)
        y_root = -5.0
        c_root = wing_geom.get_chord_at(0.0)
        le_root = wing_geom.get_le_position(0.0)
        x_root = le_root.x + (c_root * 0.50) # Maintain ~50% chord position
        z_root = wing_bottom_z - (center_pos.y * math.tan(wing_geom.dihedral_rad))

        w2 = Part.makePolygon([
            App.Vector(x_root - sw / 2.0, y_root, z_root + 2.0),
            App.Vector(x_root + sw / 2.0, y_root, z_root + 2.0),
            App.Vector(x_root + sw / 2.0, y_root, z_root + 2.0 + sh),
            App.Vector(x_root - sw / 2.0, y_root, z_root + 2.0 + sh),
            App.Vector(x_root - sw / 2.0, y_root, z_root + 2.0)
        ])

        flat_conduit = Part.makeLoft([Part.Wire(w1), Part.Wire(w2)], True, True)
        pocket = pocket.fuse(flat_conduit)

        return pocket
