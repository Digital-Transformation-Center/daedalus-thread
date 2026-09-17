package Icarus {
    private import ScalarValues::*;

    // Sub-package imports
    public import Requirements::*;
    public import AirframeArchitecture::*;
    public import PropulsionArchitecture::*;
    public import Payloads::*;
    public import MassBudget::*;

    part def ModularUAV {
        part frame : Airframe;
        part propulsion : PropulsionSystem;
        part payloadBay : PayloadInterface;
    }
}
