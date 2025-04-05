"""
...
"""
import logging

logger = logging.getLogger("__main__")
logger.info("[BASE_CTRL] loading module ")

MODE_CHARGE_FROM_GRID = 0
MODE_AVOID_DISCHARGE = 1
MODE_DISCHARGE_ALLOWED = 2

class BaseControl:
    """
...
    """

    def __init__(self,config):
        self.current_ac_charge_demand = 0
        self.current_dc_charge_demand = 0
        self.current_discharge_allowed = 1
        self.current_overall_state = MODE_DISCHARGE_ALLOWED
        self.config = config

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

    def set_current_overall_state(self):
        """
        Sets the current overall state.
        """
        if self.current_ac_charge_demand > 0:
            value = MODE_CHARGE_FROM_GRID
        # elif self.current_dc_charge_demand > 0:
        elif self.current_discharge_allowed > 0:
            value = MODE_DISCHARGE_ALLOWED
        else:
            value = MODE_AVOID_DISCHARGE
        logger.debug("[BASE_CTRL] set current overall state to %s", value)
        self.current_overall_state = value
