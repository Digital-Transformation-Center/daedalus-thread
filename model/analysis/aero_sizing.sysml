package AerodynamicAnalysis {
    private import ScalarValues::*;

    // Battery mass sizing based on cruise power and target duration
    calc def CalcBatteryMass {
        in cruisePowerWatts : Real; // Watts
        in flightDurationMin : Real; // minutes
        in batterySpecificEnergyWhKg : Real; // e.g. 200 Wh/kg
        in usableDodFactor : Real; // e.g. 0.80
        return batteryMassKg : Real = (cruisePowerWatts * (flightDurationMin / 60.0)) / (batterySpecificEnergyWhKg * usableDodFactor);
    }

    // Total aircraft gross mass
    calc def CalcGrossMass {
        in payloadMassKg : Real;
        in airframeMassKg : Real;
        in batteryMassKg : Real;
        return grossMassKg : Real = payloadMassKg + airframeMassKg + batteryMassKg;
    }

    // Minimum wing surface area needed to satisfy stall speed constraint
    calc def CalcMinWingArea {
        in grossWeightN : Real; // Newtons
        in airDensity : Real; // kg/m^3
        in stallSpeedMax : Real; // m/s
        in maxCL : Real; // maximum section lift coefficient
        return minAreaM2 : Real = (2.0 * grossWeightN) / (airDensity * (stallSpeedMax ** 2.0) * maxCL);
    }

    // Wingspan sizing bounded by maximum span limit
    calc def CalcBoundedSpan {
        in aspectRatio : Real;
        in wingAreaM2 : Real;
        in wingspanMaxM : Real;
        return spanM : Real = if (aspectRatio * wingAreaM2) ** 0.5 > wingspanMaxM 
                              then wingspanMaxM 
                              else (aspectRatio * wingAreaM2) ** 0.5;
    }

    // Root and tip chord sizing from taper ratio
    calc def CalcTaperedChords {
        in wingAreaM2 : Real;
        in spanM : Real;
        in taperRatio : Real;
        return rootChordM : Real = (2.0 * wingAreaM2) / ((1.0 + taperRatio) * spanM);
    }

    // Reusable math calculation for required cruise lift coefficient
    calc def CalcCruiseCL {
        in totalMass : Real; // kg
        in airDensity : Real; // kg/m^3
        in cruiseSpeed : Real; // m/s
        in wingArea : Real; // m^2
        return cl : Real = (2.0 * totalMass * 9.80665) / (airDensity * (cruiseSpeed ** 2.0) * wingArea);
    }

    // Wing aspect ratio and chord relation
    calc def CalcMeanChord {
        in wingspan : Real; // m
        in wingArea : Real; // m^2
        return chord : Real = wingArea / wingspan;
    }

    // Incidence pitch angle for cruise trim
    calc def CalcPitchIncidence {
        in cruiseCL : Real;
        in liftCurveSlope3DPerDeg : Real;
        in zeroLiftAlphaDeg : Real;
        return incidenceDeg : Real = (cruiseCL / liftCurveSlope3DPerDeg) + zeroLiftAlphaDeg;
    }
}
