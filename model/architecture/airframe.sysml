package AirframeArchitecture {
    private import ScalarValues::*;
    private import MissionRequirements::*;
    private import AerodynamicAnalysis::*;

    part def AirfoilProfile {
        attribute designation : String; // e.g., "Clark Y", "NACA 2412", "MH 60"
        attribute maxThicknessPercent : Real; // % of chord (t/c)
        attribute maxCamberPercent : Real; // % of chord
        attribute designCL : Real; // optimal cruise CL
    }

    part def WingAssembly {
        // Geometric parameters driving the CAD model
        attribute span : Real; // mm
        attribute rootChord : Real; // mm
        attribute tipChord : Real; // mm
        attribute sweepAngle : Real; // degrees
        attribute dihedralAngle : Real; // degrees

        // Linked aerodynamic profile
        part profile : AirfoilProfile;

        // Traceability to requirement
        satisfy reconMissionReq;
    }

    // System instance for your current aircraft configuration
    part uavWing : WingAssembly {
        attribute :>> span = 1800.0; // 1.8m
        attribute :>> rootChord = 240.0; // 240mm
        attribute :>> tipChord = 160.0; // 160mm
        attribute :>> sweepAngle = 3.5;
        attribute :>> dihedralAngle = 2.0;

        part :>> profile {
            attribute :>> designation = "NACA 4412";
            attribute :>> maxThicknessPercent = 12.0;
            attribute :>> maxCamberPercent = 4.0;
            attribute :>> designCL = 0.45;
        }
    }
}
