package SystemVerification {
    private import ScalarValues::*;
    private import MissionRequirements::*;

    // Verification cases closing the loop between domain models and requirements
    verification def VerifyStallSpeed {
        in measuredStallSpeed : Real;
        in req : StallSpeedReq;
        return verdict : Boolean = measuredStallSpeed <= req.maxStallSpeed;
    }

    verification def VerifyWingspan {
        in cadWingspan : Real;
        in req : WingspanLimitReq;
        return verdict : Boolean = cadWingspan <= req.maxWingspan;
    }

    verification def VerifyWingMass {
        in cadWingMass : Real;
        in req : WingMassBudgetReq;
        return verdict : Boolean = cadWingMass <= req.maxWingMass;
    }

    verification def VerifyFlightDuration {
        in achievableDurationMin : Real;
        in req : FlightDurationReq;
        return verdict : Boolean = achievableDurationMin >= req.minFlightDuration;
    }

    verification def VerifyPayloadCapacity {
        in allocatedPayloadMass : Real;
        in req : PayloadMassReq;
        return verdict : Boolean = allocatedPayloadMass >= req.minPayloadMass;
    }

    // Concrete Phase 1 verification evaluations
    action verifyIcarusStall : VerifyStallSpeed {
        verify icarusStallReq;
    }

    action verifyIcarusSpan : VerifyWingspan {
        verify icarusSpanReq;
    }

    action verifyIcarusMass : VerifyWingMass {
        verify icarusWingMassReq;
    }

    action verifyIcarusDuration : VerifyFlightDuration {
        verify icarusDurationReq;
    }

    action verifyIcarusPayload : VerifyPayloadCapacity {
        verify icarusPayloadReq;
    }
}
