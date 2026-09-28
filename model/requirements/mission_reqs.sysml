package MissionRequirements {
    private import ScalarValues::*;

    requirement def MissionEnvelopeReq {
        attribute cruiseSpeedTarget : Real; // Target cruise airspeed in m/s
        attribute cruiseSpeedMin : Real; // Backward compatibility alias
        attribute stallSpeedMax : Real; // Maximum stall airspeed in m/s
        attribute payloadMass : Real; // Required payload mass in kg
        attribute payloadMassMin : Real; // Backward compatibility alias
        attribute wingspanMax : Real; // Wingspan upper bound limit in mm
        attribute flightDurationTarget : Real; // Target flight duration in minutes
        attribute operationalCeiling : Real; // Operational ceiling in m MSL
    }

    requirement def AerodynamicEfficiencyReq {
        attribute minLiftToDrag : Real; // Minimum acceptable L/D at cruise
    }

    requirement reconMissionReq : MissionEnvelopeReq {
        doc /* Reconnaissance and mapping baseline flight profile */
        attribute :>> cruiseSpeedTarget = 18.0; // m/s (~35 knots)
        attribute :>> cruiseSpeedMin = 18.0;
        attribute :>> stallSpeedMax = 11.0; // m/s (~21 knots)
        attribute :>> payloadMass = 1.2; // kg
        attribute :>> payloadMassMin = 1.2;
        attribute :>> wingspanMax = 1800.0; // mm upper bound
        attribute :>> flightDurationTarget = 45.0; // minutes
        attribute :>> operationalCeiling = 1200.0;
    }
}
