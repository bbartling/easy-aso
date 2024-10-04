import random
from enum import Enum
from datetime import datetime


# Define FSM States for Supervisory Control
class HVACState(Enum):
    IDLE = "idle"
    MONITORING_OCCUPIED = "monitoring_occupied"
    MONITORING_UNOCCUPIED = "monitoring_unoccupied"
    ADJUSTING = "adjusting"
    RELEASE_OVERRIDE = "release_override"


# Define transitions between states
transitions = {
    HVACState.IDLE: [HVACState.MONITORING_OCCUPIED, HVACState.MONITORING_UNOCCUPIED],
    HVACState.MONITORING_OCCUPIED: [HVACState.ADJUSTING, HVACState.RELEASE_OVERRIDE],
    HVACState.MONITORING_UNOCCUPIED: [HVACState.ADJUSTING, HVACState.RELEASE_OVERRIDE],
    HVACState.ADJUSTING: [
        HVACState.MONITORING_OCCUPIED,
        HVACState.MONITORING_UNOCCUPIED,
    ],
    HVACState.RELEASE_OVERRIDE: [HVACState.IDLE],
}


# FSM Transition Check
def can_transition(current_state, next_state):
    return next_state in transitions.get(current_state, [])


# Simulate sensor readings for occupancy and temperature
def simulate_occupancy():
    """Simulate whether the building is occupied."""
    return random.choice([True, False])


def simulate_temperature():
    """Simulate temperature reading from a sensor."""
    return random.uniform(60.0, 85.0)


class SimpleFSM:
    def __init__(self):
        self.state = HVACState.IDLE

    def transition_to(self, new_state):
        """Attempt to transition to a new state if allowed."""
        if can_transition(self.state, new_state):
            print(f"Transitioning from {self.state.value} to {new_state.value}")
            self.state = new_state
        else:
            print(
                f"Invalid transition from {self.state.value} to {new_state.value}. This action is not allowed right now!"
            )

    def handle_state(self):
        """Run logic based on the current state."""
        print(f"Currently in state: {self.state.value}")

        if self.state == HVACState.MONITORING_OCCUPIED:
            print("Building is occupied. Performing energy efficiency tasks...")
            self.transition_to(HVACState.ADJUSTING)  # Adjust settings if needed.

        elif self.state == HVACState.MONITORING_UNOCCUPIED:
            print("Building is unoccupied. Monitoring basic system requirements...")
            temperature = simulate_temperature()
            print(f"Current temperature is {temperature}°F.")
            if temperature < 65.0 or temperature > 80.0:
                self.transition_to(HVACState.ADJUSTING)

        elif self.state == HVACState.ADJUSTING:
            print("Adjusting setpoints for the building...")
            self.transition_to(HVACState.RELEASE_OVERRIDE)

        elif self.state == HVACState.RELEASE_OVERRIDE:
            print("Releasing all overrides and returning to idle...")
            self.transition_to(HVACState.IDLE)


# Simulation Example
fsm = SimpleFSM()
fsm.transition_to(HVACState.MONITORING_OCCUPIED)
fsm.handle_state()
fsm.transition_to(HVACState.ADJUSTING)  # Correct transition
fsm.handle_state()
fsm.transition_to(HVACState.RELEASE_OVERRIDE)  # Valid transition
fsm.handle_state()
