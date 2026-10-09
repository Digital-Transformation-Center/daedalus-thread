package MissionRequirements {
    private import ScalarValues::*;

    // Operational flight envelope requirements for Phase 1 (Icarus)
    requirement def StallSpeedReq {
        attribute maxStallSpeed : Real; // m/s
        doc /* Aircraft stall speed must not exceed 11.0 m/s for hand-launch safety. */
    }

    requirement def CruiseSpeedReq {
        attribute minCruiseSpeed : Real; // m/s
        doc /* Minimum level cruise airspeed required to maintain surveillance track. */
    }

    requirement def PayloadMassReq {
        attribute minPayloadMass : Real; // kg
        doc /* Minimum usable sensor and electronics payload mass. */
    }

    requirement def WingspanLimitReq {
        attribute maxWingspan : Real; // mm
        doc /* Geometric limit dictated by ground handling and transport constraints. */
    }

    requirement def WingMassBudgetReq {
        attribute maxWingMass : Real; // kg
        doc /* Total mass allocation for left and right wing structures combined. */
    }

    requirement def FlightDurationReq {
        attribute minFlightDuration : Real; // minutes
        doc /* Minimum level flight endurance required on primary battery capacity. */
    }

    // Concrete mission requirement baseline for Phase 1
    requirement icarusStallReq : StallSpeedReq {
        attribute :>> maxStallSpeed = 11.0;
    }

    requirement icarusCruiseReq : CruiseSpeedReq {
        attribute :>> minCruiseSpeed = 18.0;
    }

    requirement icarusPayloadReq : PayloadMassReq {
        attribute :>> minPayloadMass = 1.2;
    }

    requirement icarusSpanReq : WingspanLimitReq {
        attribute :>> maxWingspan = 1800.0;
    }

    requirement icarusWingMassReq : WingMassBudgetReq {
        attribute :>> maxWingMass = 0.65;
    }

    requirement icarusDurationReq : FlightDurationReq {
        attribute :>> minFlightDuration = 30.0;
    }
}
