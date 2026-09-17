package AerodynamicAnalysis {
    private import ScalarValues::*;

    // Reusable math calculation for required lift coefficient
    calc def CalcCruiseCL {
        in totalMass : Real; // kg
        in airDensity : Real; // kg/m^3
        in cruiseSpeed : Real; // m/s
        in wingArea : Real; // m^2
        return cl : Real = (2.0 * totalMass * 9.81) / (airDensity * (cruiseSpeed ** 2.0) * wingArea);
    }

    // Wing aspect ratio & chord relation
    calc def CalcMeanChord {
        in wingspan : Real; // m
        in wingArea : Real; // m^2
        return chord : Real = wingArea / wingspan;
    }
}
