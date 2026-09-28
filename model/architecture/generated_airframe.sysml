package GeneratedAirframeArchitecture {
    private import ScalarValues::*;
    private import MissionRequirements::*;
    private import AirframeArchitecture::*;

    // Automatically generated UAV Wing instance synthesized by MBSE pipeline
    part generatedUavWing : WingAssembly {
        doc /* Synthesized instance from mission requirements */
        attribute :>> span = 1552.3; // mm
        attribute :>> rootChord = 250.9; // mm
        attribute :>> tipChord = 163.1; // mm
        attribute :>> sweepAngle = 3.5; // deg
        attribute :>> dihedralAngle = 2.0; // deg
        attribute :>> pitchAngle = 2.7; // deg

        attribute :>> wingAreaM2 = 0.3213; // m^2
        attribute :>> aspectRatio = 7.50;
        attribute :>> cruiseCL = 0.454;

        attribute :>> grossMassKg = 2.950;
        attribute :>> payloadMassKg = 1.200;
        attribute :>> batteryMassKg = 0.310;
        attribute :>> flightDurationMin = 45.0;

        part :>> profile {
            attribute :>> designation = "NACA 4412";
            attribute :>> maxThicknessPercent = 12.0;
            attribute :>> maxCamberPercent = 4.0;
            attribute :>> designCL = 0.454;
        }

        satisfy reconMissionReq;
    }
}
