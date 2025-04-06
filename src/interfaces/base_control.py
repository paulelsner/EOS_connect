"""
...
"""
import logging
from time import time

logger = logging.getLogger("__main__")
logger.info("[BASE_CTRL] loading module ")

MODE_CHARGE_FROM_GRID = 0
MODE_AVOID_DISCHARGE = 1
MODE_DISCHARGE_ALLOWED = 2

class BaseControl:
    """
        BaseControl is a class that manages the state and demands of a control system.
        It keeps track of the current AC and DC charge demands, discharge allowed status,
        and the overall state of the system. The overall state can be one of three modes:
        MODE_CHARGE_FROM_GRID, MODE_AVOID_DISCHARGE, or MODE_DISCHARGE_ALLOWED.
    """

    def __init__(self, config):
        self.current_ac_charge_demand = 0
        self.last_ac_charge_demand = 0
        self.current_dc_charge_demand = 0
        self.current_discharge_allowed = 1
        self.current_evcc_charging_state = False
        self.current_overall_state = MODE_DISCHARGE_ALLOWED
        self.config = config
        self._state_change_timestamps = []

    def was_overall_state_changed_recently(self, time_window_seconds):
        """
        Checks if the overall state was changed within the last `time_window_seconds`.
        """
        current_time = time()
        # Remove timestamps older than the time window
        self._state_change_timestamps = [
            ts for ts in self._state_change_timestamps if current_time - ts <= time_window_seconds
        ]
        return len(self._state_change_timestamps) > 0

    def get_current_ac_charge_demand(self):
        """
        Returns the current AC charge demand.
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
        return self.current_overall_state

    def set_current_ac_charge_demand(self, value):
        """
        Sets the current AC charge demand.
        """
        self.current_ac_charge_demand = value
        # logger.debug("[BASE_CTRL] set current AC charge demand to %s", value)
        self.set_current_overall_state()

    def set_current_dc_charge_demand(self, value):
        """
        Sets the current DC charge demand.
        """
        self.current_dc_charge_demand = value
        # logger.debug("[BASE_CTRL] set current DC charge demand to %s", value)
        self.set_current_overall_state()

    def set_current_discharge_allowed(self, value):
        """
        Sets the current discharge demand.
        """
        self.current_discharge_allowed = value
        # logger.debug("[BASE_CTRL] set current discharge demand to %s", value)
        self.set_current_overall_state()

    def set_current_evcc_charging_state(self, value):
        """
        Sets the current EVCC charging state.
        """
        self.current_evcc_charging_state = value
        # logger.debug("[BASE_CTRL] set current EVCC charging state to %s", value)
        self.set_current_overall_state()

    def set_current_overall_state(self):
        """
        Sets the current overall state and logs the timestamp if it changes.
        """
        if self.current_ac_charge_demand > 0:
            value = MODE_CHARGE_FROM_GRID
        elif self.current_discharge_allowed > 0:
            value = MODE_DISCHARGE_ALLOWED
        else:
            value = MODE_AVOID_DISCHARGE
        # check if the grid charge demand has changed
        grid_charge_value_changed = self.current_ac_charge_demand != self.last_ac_charge_demand

        # override overall state if EVCC charging state is active and discharge is allowed
        if value == MODE_DISCHARGE_ALLOWED and self.current_evcc_charging_state:
            value = MODE_AVOID_DISCHARGE
            logger.info("[BASE_CTRL] EVCC charging state is active,"+
                        " setting overall state to MODE_AVOID_DISCHARGE")

        if value != self.current_overall_state or grid_charge_value_changed:
            self._state_change_timestamps.append(time())
            # Limit the size of the state change timestamps to avoid memory overrun
            max_timestamps = 1000  # Adjust this value as needed
            if len(self._state_change_timestamps) > max_timestamps:
                self._state_change_timestamps.pop(0)
            if grid_charge_value_changed:
                logger.info("[BASE_CTRL] AC charge demand changed to %s",
                            self.current_ac_charge_demand)
            else:
                logger.debug("[BASE_CTRL] overall state changed to %s", value)
        # store the last AC charge demand for comparison
        self.last_ac_charge_demand = self.current_ac_charge_demand

        self.current_overall_state = value
