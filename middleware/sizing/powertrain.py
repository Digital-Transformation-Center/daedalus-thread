"""Electric powertrain sizing and performance module for Daedalus Thread.

Calculates cruise electrical power consumption, sizes battery pack capacity
and mass, and validates flight endurance based on vehicle aeromechanical state.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class PowertrainMetrics:
    """Estimated electric powertrain performance metrics."""
    cruise_power_watts: float
    required_energy_wh: float
    usable_energy_wh: float
    battery_mass_kg: float
    achievable_duration_min: float
    powertrain_efficiency: float

    def to_dict(self) -> Dict[str, Any]:
        """Converts powertrain metrics to a standard dictionary."""
        return asdict(self)


def calculate_cruise_power(
    total_mass_kg: float,
    cruise_speed_mps: float,
    lift_to_drag_ratio: float,
    powertrain_efficiency: float = 0.65,
    avionics_power_watts: float = 12.0
) -> float:
    """Calculates total electrical power draw required for level cruise.

    Args:
        total_mass_kg: Total vehicle mass in kg.
        cruise_speed_mps: Level cruise airspeed in m/s.
        lift_to_drag_ratio: Aerodynamic lift-to-drag ratio (L/D).
        powertrain_efficiency: Combined efficiency of motor, ESC, and propeller.
        avionics_power_watts: Constant electrical load of flight computer and payload.

    Returns:
        Total electrical power in watts.
    """
    g = 9.80665
    aerodynamic_thrust_n = (total_mass_kg * g) / max(lift_to_drag_ratio, 1.0)
    shaft_power_watts = aerodynamic_thrust_n * cruise_speed_mps
    propulsion_electrical_watts = shaft_power_watts / max(powertrain_efficiency, 0.1)
    return propulsion_electrical_watts + avionics_power_watts


def size_battery(
    cruise_power_watts: float,
    target_duration_min: float,
    specific_energy_wh_kg: float = 180.0,
    depth_of_discharge: float = 0.80
) -> float:
    """Sizes required battery mass to sustain target flight duration.

    Args:
        cruise_power_watts: Continuous power draw in watts.
        target_duration_min: Target flight duration in minutes.
        specific_energy_wh_kg: Usable pack energy density in Wh/kg (default: Li-ion pack).
        depth_of_discharge: Maximum discharge fraction to protect cell longevity.

    Returns:
        Battery pack mass in kilograms.
    """
    energy_wh = cruise_power_watts * (target_duration_min / 60.0)
    total_nominal_energy_wh = energy_wh / max(depth_of_discharge, 0.1)
    return total_nominal_energy_wh / max(specific_energy_wh_kg, 1.0)


def calculate_endurance(
    battery_mass_kg: float,
    cruise_power_watts: float,
    specific_energy_wh_kg: float = 180.0,
    depth_of_discharge: float = 0.80
) -> float:
    """Calculates achievable flight endurance for a given battery mass.

    Args:
        battery_mass_kg: Battery pack mass in kg.
        cruise_power_watts: Continuous power draw in watts.
        specific_energy_wh_kg: Pack energy density in Wh/kg.
        depth_of_discharge: Maximum usable discharge depth.

    Returns:
        Achievable flight duration in minutes.
    """
    if cruise_power_watts <= 0.0:
        return 0.0
    usable_energy_wh = battery_mass_kg * specific_energy_wh_kg * depth_of_discharge
    hours = usable_energy_wh / cruise_power_watts
    return hours * 60.0


def evaluate_powertrain(
    total_mass_kg: float,
    cruise_speed_mps: float,
    lift_to_drag_ratio: float,
    target_duration_min: float,
    battery_mass_kg: float = 0.0,
    specific_energy_wh_kg: float = 180.0,
    depth_of_discharge: float = 0.80,
    powertrain_efficiency: float = 0.65
) -> PowertrainMetrics:
    """Evaluates electric powertrain state and endurance.

    Args:
        total_mass_kg: Total vehicle mass in kg.
        cruise_speed_mps: Level cruise airspeed in m/s.
        lift_to_drag_ratio: Aerodynamic L/D.
        target_duration_min: Mission endurance target in minutes.
        battery_mass_kg: Optional fixed battery mass. If <= 0, sized automatically.
        specific_energy_wh_kg: Energy density in Wh/kg.
        depth_of_discharge: Depth of discharge limit.
        powertrain_efficiency: Propulsive chain efficiency.

    Returns:
        PowertrainMetrics containing sized power, energy, and duration.
    """
    cruise_power = calculate_cruise_power(
        total_mass_kg=total_mass_kg,
        cruise_speed_mps=cruise_speed_mps,
        lift_to_drag_ratio=lift_to_drag_ratio,
        powertrain_efficiency=powertrain_efficiency
    )

    if battery_mass_kg <= 0.0:
        batt_mass = size_battery(
            cruise_power_watts=cruise_power,
            target_duration_min=target_duration_min,
            specific_energy_wh_kg=specific_energy_wh_kg,
            depth_of_discharge=depth_of_discharge
        )
    else:
        batt_mass = battery_mass_kg

    achievable_duration = calculate_endurance(
        battery_mass_kg=batt_mass,
        cruise_power_watts=cruise_power,
        specific_energy_wh_kg=specific_energy_wh_kg,
        depth_of_discharge=depth_of_discharge
    )

    nominal_energy = batt_mass * specific_energy_wh_kg
    usable_energy = nominal_energy * depth_of_discharge

    return PowertrainMetrics(
        cruise_power_watts=round(cruise_power, 2),
        required_energy_wh=round(cruise_power * (target_duration_min / 60.0), 2),
        usable_energy_wh=round(usable_energy, 2),
        battery_mass_kg=round(batt_mass, 3),
        achievable_duration_min=round(achievable_duration, 1),
        powertrain_efficiency=powertrain_efficiency
    )
