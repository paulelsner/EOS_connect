"""
This module defines the BaseControl class, which manages the state and demands
of a control system. It includes methods for setting and retrieving charge demands,
discharge permissions, and overall system state.
"""

import logging
from time import time
from datetime import datetime

logger = logging.getLogger("__main__")
logger.info("[BASE_CTRL] loading module ")

MODE_CHARGE_FROM_GRID = 0
MODE_AVOID_DISCHARGE = 1
MODE_DISCHARGE_ALLOWED = 2
MODE_AVOID_DISCHARGE_EVCC_FAST = 3
MODE_DISCHARGE_ALLOWED_EVCC_PV = 4
MODE_DISCHARGE_ALLOWED_EVCC_MIN_PV = 5

state_mapping = {
    -1: "MODE Startup",
    0: "MODE CHARGE FROM GRID",
    1: "MODE AVOID DISCHARGE",
    2: "MODE DISCHARGE ALLOWED",
    3: "MODE AVOID DISCHARGE EVCC FAST",
    4: "MODE DISCHARGE ALLOWED EVCC PV",
    5: "MODE DISCHARGE ALLOWED EVCC MIN+PV",
}


class BaseControl:
    """
    BaseControl is a class that manages the state and demands of a control system.
    It keeps track of the current AC and DC charge demands, discharge allowed status,
    and the overall state of the system. The overall state can be one of three modes:
    MODE_CHARGE_FROM_GRID, MODE_AVOID_DISCHARGE, or MODE_DISCHARGE_ALLOWED.
    """

    def __init__(self, config, timezone):
        self.current_ac_charge_demand = 0
        self.last_ac_charge_demand = 0
        self.current_dc_charge_demand = 0
        self.current_discharge_allowed = -1
        self.current_evcc_charging_state = False
        self.current_evcc_charging_mode = False
        # startup with None to force a writing to the inverter
        self.current_overall_state = -1
        self.current_battery_soc = 0
        self.time_zone = timezone
        self.config = config
        self._state_change_timestamps = []

    def get_state_mapping(self):
        """
        Returns the state mapping dictionary.
        """
        return state_mapping

    def was_overall_state_changed_recently(self, time_window_seconds):
        """
        Checks if the overall state was changed within the last `time_window_seconds`.
        """
        current_time = time()
        # Remove timestamps older than the time window
        self._state_change_timestamps = [
            ts
            for ts in self._state_change_timestamps
            if current_time - ts <= time_window_seconds
        ]
        return len(self._state_change_timestamps) > 0

    def get_current_ac_charge_demand(self):
        """
        Returns the current AC charge demand calculated based on maximum battery charge power.
        """
        return self.current_ac_charge_demand

    def get_current_dc_charge_demand(self):
        """
        Returns the current DC charge demand.
        """
        return self.current_dc_charge_demand

    def get_current_discharge_allowed(self):
        """
        Returns the current discharge demand.
        """
        return self.current_discharge_allowed

    def get_current_overall_state(self):
        """
        Returns the current overall state.
        """
        # Return the string representation of the state
        return state_mapping.get(self.current_overall_state, "unknown state")

    def get_current_overall_state_number(self):
        """
        Returns the current overall state as a number.
        """
        return self.current_overall_state

    def get_current_battery_soc(self):
        """
        Returns the current battery state of charge (SOC).
        """
        return self.current_battery_soc

    def get_current_evcc_charging_state(self):
        """
        Returns the current EVCC charging state.
        """
        return self.current_evcc_charging_state

    def get_current_evcc_charging_mode(self):
        """
        Returns the current EVCC charging mode.
        """
        return self.current_evcc_charging_mode

    def set_current_ac_charge_demand(self, value_relative):
        """
        Sets the current AC charge demand.
        """
        current_hour = datetime.now(self.time_zone).hour
        self.current_ac_charge_demand = (
            value_relative * self.config["battery"]["max_charge_power_w"]
        )
        logger.debug(
            "[BASE_CTRL] set AC charge demand for current hour %s:00 -> %s Wh -"
            + " based on max charge power %s W",
            current_hour,
            self.current_ac_charge_demand,
            self.config["battery"]["max_charge_power_w"],
        )
        self.set_current_overall_state()

    def set_current_dc_charge_demand(self, value_relative):
        """
        Sets the current DC charge demand.
        """
        current_hour = datetime.now(self.time_zone).hour
        self.current_dc_charge_demand = (
            value_relative * self.config["battery"]["max_charge_power_w"]
        )
        logger.debug(
            "[BASE_CTRL] set DC charge demand for current hour %s:00 -> %s Wh -"
            + " based on max charge power %s W",
            current_hour,
            self.current_dc_charge_demand,
            self.config["battery"]["max_charge_power_w"],
        )
        self.set_current_overall_state()

    def set_current_discharge_allowed(self, value):
        """
        Sets the current discharge demand.
        """
        current_hour = datetime.now(self.time_zone).hour
        self.current_discharge_allowed = value
        logger.debug(
            "[BASE_CTRL] set Discharge allowed for current hour %s:00 %s",
            current_hour,
            self.current_discharge_allowed,
        )
        self.set_current_overall_state()

    def set_current_evcc_charging_state(self, value):
        """
        Sets the current EVCC charging state.
        """
        self.current_evcc_charging_state = value
        # logger.debug("[BASE_CTRL] set current EVCC charging state to %s", value)
        self.set_current_overall_state()

    def set_current_evcc_charging_mode(self, value):
        """
        Sets the current EVCC charging mode.
        """
        self.current_evcc_charging_mode = value
        # logger.debug("[BASE_CTRL] set current EVCC charging mode to %s", value)
        self.set_current_overall_state()

    def set_current_overall_state(self):
        """
        Sets the current overall state and logs the timestamp if it changes.
        """
        if self.current_ac_charge_demand > 0:
            new_state = MODE_CHARGE_FROM_GRID
        elif self.current_discharge_allowed > 0:
            new_state = MODE_DISCHARGE_ALLOWED
        elif self.current_discharge_allowed == 0:
            new_state = MODE_AVOID_DISCHARGE
        else:
            new_state = -1
        # check if the grid charge demand has changed
        grid_charge_value_changed = (
            self.current_ac_charge_demand != self.last_ac_charge_demand
        )

        # override overall state if EVCC charging state is active and
        # in mode fast charge and discharge is allowed
        if (
            new_state == MODE_DISCHARGE_ALLOWED
            and self.current_evcc_charging_state
            and self.current_evcc_charging_mode == "now"
        ):
            new_state = MODE_AVOID_DISCHARGE_EVCC_FAST
            logger.info(
                "[BASE_CTRL] EVCC charging state is active,"
                + " setting overall state to MODE_AVOID_DISCHARGE_EVCC_FAST"
            )

        # override overall state if EVCC charging state is active and
        # in mode pv charge and discharge is allowed
        if (
            new_state == MODE_DISCHARGE_ALLOWED
            and self.current_evcc_charging_state
            and self.current_evcc_charging_mode == "pv"
        ):
            new_state = MODE_DISCHARGE_ALLOWED_EVCC_PV
            logger.info(
                "[BASE_CTRL] EVCC charging state is active,"
                + " setting overall state to MODE_DISCHARGE_ALLOWED_EVCC_PV"
            )

        # override overall state if EVCC charging state is active and
        # in mode pv charge and discharge is allowed
        if (
            new_state == MODE_DISCHARGE_ALLOWED
            and self.current_evcc_charging_state
            and self.current_evcc_charging_mode == "minpv"
        ):
            new_state = MODE_DISCHARGE_ALLOWED_EVCC_MIN_PV
            logger.info(
                "[BASE_CTRL] EVCC charging state is active,"
                + " setting overall state to MODE_DISCHARGE_ALLOWED_EVCC_MIN_PV"
            )

        if new_state != self.current_overall_state or grid_charge_value_changed:
            self._state_change_timestamps.append(time())
            # Limit the size of the state change timestamps to avoid memory overrun
            max_timestamps = 1000  # Adjust this value as needed
            if len(self._state_change_timestamps) > max_timestamps:
                self._state_change_timestamps.pop(0)
            if grid_charge_value_changed:
                logger.info(
                    "[BASE_CTRL] AC charge demand changed to %s",
                    self.current_ac_charge_demand,
                )
            else:
                logger.debug(
                    "[BASE_CTRL] overall state changed to %s",
                    state_mapping.get(new_state, "unknown state"),
                )
        # store the last AC charge demand for comparison
        self.last_ac_charge_demand = self.current_ac_charge_demand

        self.current_overall_state = new_state

    def set_current_battery_soc(self, value):
        """
        Sets the current battery state of charge (SOC).
        """
        self.current_battery_soc = value
        # logger.debug("[BASE_CTRL] set current battery SOC to %s", value)
