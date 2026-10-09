package AeroAnalysis {
    private import ScalarValues::*;

    // Core aerodynamic mathematical relations for conceptual UAV sizing
    calc def CalcCruiseCL {
        in totalMass : Real;   // kg
        in airDensity : Real;  // kg/m^3
        in cruiseSpeed : Real; // m/s
        in wingArea : Real;    // m^2
        return cl : Real = (2.0 * totalMass * 9.80665) / (airDensity * (cruiseSpeed ** 2.0) * wingArea);
    }

    calc def CalcStallSpeed {
        in totalMass : Real;   // kg
        in airDensity : Real;  // kg/m^3
        in wingArea : Real;    // m^2
        in maxCL : Real;
        return vStall : Real = ( (2.0 * totalMass * 9.80665) / (airDensity * wingArea * maxCL) ) ** 0.5;
    }

    calc def CalcRequiredWingArea {
        in totalMass : Real;   // kg
        in airDensity : Real;  // kg/m^3
        in stallSpeed : Real;  // m/s
        in maxCL : Real;
        return area : Real = (2.0 * totalMass * 9.80665) / (airDensity * (stallSpeed ** 2.0) * maxCL);
    }

    calc def CalcMeanChord {
        in wingspan : Real; // m
        in wingArea : Real; // m^2
        return chord : Real = wingArea / wingspan;
    }

    calc def CalcCruisePower {
        in totalMass : Real;        // kg
        in cruiseSpeed : Real;      // m/s
        in liftToDrag : Real;
        in powertrainEff : Real;
        return powerWatts : Real = (totalMass * 9.80665 * cruiseSpeed) / (liftToDrag * powertrainEff);
    }

    calc def CalcBatteryEnergy {
        in powerWatts : Real;        // W
        in flightDurationMin : Real; // minutes
        return energyWh : Real = powerWatts * (flightDurationMin / 60.0);
    }

    calc def CalcAchievableDuration {
        in batteryCapacityWh : Real; // Wh
        in dod : Real;               // depth of discharge
        in cruisePowerWatts : Real;  // W
        return durationMin : Real = ((batteryCapacityWh * dod) / cruisePowerWatts) * 60.0;
    }

    // Constraint asserting stall performance compliance
    constraint def StallMarginConstraint {
        in totalMass : Real;
        in airDensity : Real;
        in wingArea : Real;
        in maxCL : Real;
        in maxAllowedStallSpeed : Real;

        CalcStallSpeed(totalMass, airDensity, wingArea, maxCL) <= maxAllowedStallSpeed
    }
}
