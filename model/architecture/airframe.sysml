package AirframeArchitecture {
    private import ScalarValues::*;
    private import MissionRequirements::*;

    // Structural interface definitions
    port def MechanicalMountPort;
    port def ControlSignalPort;

    part def AirfoilProfile {
        attribute designation : String;
        attribute thicknessRatio : Real; // t/c ratio
        attribute camberRatio : Real;    // camber ratio
        attribute maxCL : Real;          // maximum clean section lift coefficient
    }

    part def WingAssembly {
        // Architectural constraints and budget allocations
        attribute maxSpanAllocation : Real; // mm
        attribute targetMassAllocation : Real; // kg
        attribute servoQuantity : Integer;

        // Sub-elements and interfaces
        part profile : AirfoilProfile;
        port rootMount : MechanicalMountPort;
        port servoSignal : ControlSignalPort;

        // Traceability to operational envelope requirements
        satisfy icarusSpanReq;
        satisfy icarusWingMassReq;
    }

    // Concrete architectural instance for Icarus Phase 1 baseline
    part icarusWing : WingAssembly {
        attribute :>> maxSpanAllocation = 1800.0;
        attribute :>> targetMassAllocation = 0.65;
        attribute :>> servoQuantity = 2;

        part :>> profile {
            attribute :>> designation = "NACA 2412";
            attribute :>> thicknessRatio = 0.12;
            attribute :>> camberRatio = 0.02;
            attribute :>> maxCL = 1.4;
        }
    }
}
