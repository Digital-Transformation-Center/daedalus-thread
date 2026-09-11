package MissionRequirements {
    private import ScalarValues::*;

    requirement def MissionEnvelopeReq {
        attribute cruiseSpeedMin : Real; // m/s
        attribute stallSpeedMax : Real; // m/s
        attribute payloadMassMin : Real; // kg
        attribute operationalCeiling : Real; // m MSL
    }

    requirement def AerodynamicEfficiencyReq {
        attribute minLiftToDrag : Real; // L/D at cruise
    }

    requirement reconMissionReq : MissionEnvelopeReq {
        doc /* Reconnaissance / mapping flight profile */
        attribute :>> cruiseSpeedMin = 18.0; // ~35 knots
        attribute :>> stallSpeedMax = 11.0; // ~21 knots
        attribute :>> payloadMassMin = 1.2; // kg
        attribute :>> operationalCeiling = 1200.0;
    }
}
