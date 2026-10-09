package Icarus {
    private import ScalarValues::*;

    // Core digital thread package imports
    public import MissionRequirements::*;
    public import AirframeArchitecture::*;
    public import AeroAnalysis::*;
    public import SystemVerification::*;

    part def ModularUAV {
        attribute totalMass : Real; // kg
        attribute payloadCapacity : Real; // kg

        // Subsystem allocations
        part wingAssembly : WingAssembly;
    }

    // Baseline UAV instance for Phase 1 (Icarus)
    part icarusUAV : ModularUAV {
        attribute :>> totalMass = 2.4; // kg All-Up Weight
        attribute :>> payloadCapacity = 1.2; // kg

        part :>> wingAssembly = icarusWing;
    }
}
