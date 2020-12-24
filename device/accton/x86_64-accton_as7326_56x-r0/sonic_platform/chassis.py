#!/usr/bin/env python

#############################################################################
# Celestica
#
# Module contains an implementation of SONiC Platform Base API and
# provides the Chassis information which are available in the platform
#
#############################################################################

import os

try:
    from sonic_platform_base.chassis_base import ChassisBase
    from sonic_platform.sfp import Sfp
    from sonic_platform.fan_drawer import FanDrawer
    from sonic_platform.psu import Psu
    from sonic_platform.thermal import Thermal
    from sonic_platform.eeprom import Tlv
    from sonic_platform.component import Component
    from sonic_py_common import device_info

except ImportError as e:
    raise ImportError(str(e) + "- required module not found")

NUM_FAN_TRAY = 6
NUM_PSU = 2
NUM_THERMAL = 4
NUM_PORT = 56
NUM_COMPONENT = 4

HOST_REBOOT_CAUSE_PATH = "/host/reboot-cause/"
PMON_REBOOT_CAUSE_PATH = "/usr/share/sonic/platform/api_files/reboot-cause/"
REBOOT_CAUSE_FILE = "reboot-cause.txt"
PREV_REBOOT_CAUSE_FILE = "previous-reboot-cause.txt"
HOST_CHK_CMD = "docker > /dev/null 2>&1"


class Chassis(ChassisBase):
    """Platform-specific Chassis class"""

    def __init__(self):
        ChassisBase.__init__(self)
        self.config_data = {}
        (self.platform, self.hwsku) = device_info.get_platform_and_hwsku()

        self.__initialize_fan()
        self.__initialize_psu()
        self.__initialize_thermals()
        self.__initialize_components()
        self.__initialize_sfp()
        self.__initialize_eeprom()

    def __initialize_sfp(self):
        for index in range(NUM_PORT):
            sfp = Sfp(index)
            self._sfp_list.append(sfp)
        self.sfp_module_initialized = True

    def __initialize_fan(self):
        for fant_index in range(NUM_FAN_TRAY):
            fandrawer = FanDrawer(fant_index)
            self._fan_drawer_list.append(fandrawer)
            self._fan_list.extend(fandrawer._fan_list)

    def __initialize_psu(self):
        for index in range(NUM_PSU):
            psu = Psu(index)
            self._psu_list.append(psu)

    def __initialize_thermals(self):
        for index in range(NUM_THERMAL):
            thermal = Thermal(index)
            self._thermal_list.append(thermal)

    def __initialize_eeprom(self):
        self._eeprom = Tlv()

    def __initialize_components(self):
        for index in range(NUM_COMPONENT):
            component = Component(index)
            self._component_list.append(component)

    def __initialize_watchdog(self):
        self._watchdog = Watchdog()

    def __is_host(self):
        return os.system(HOST_CHK_CMD) == 0

    def __read_txt_file(self, file_path):
        try:
            with open(file_path, 'r') as fd:
                return fd.read().strip()
        except IOError:
            pass
        return None

    def get_name(self):
        """
        Retrieves the name of the device
            Returns:
            string: The name of the device
        """
        return self.hwsku

    def get_base_mac(self):
        """
        Retrieves the base MAC address for the chassis
        Returns:
            A string containing the MAC address in the format
            'XX:XX:XX:XX:XX:XX'
        """
        return self._eeprom.get_mac()

    def get_serial_number(self):
        """
        Retrieves the hardware serial number for the chassis
        Returns:
            A string containing the hardware serial number for this chassis.
        """
        return self._eeprom.get_serial()

    def get_system_eeprom_info(self):
        """
        Retrieves the full content of system EEPROM information for the chassis
        Returns:
            A dictionary where keys are the type code defined in
            OCP ONIE TlvInfo EEPROM format and values are their corresponding
            values.
        """
        return self._eeprom.get_eeprom()

    def get_reboot_cause(self):
        """
        Retrieves the cause of the previous reboot

        Returns:
            A tuple (string, string) where the first element is a string
            containing the cause of the previous reboot. This string must be
            one of the predefined strings in this class. If the first string
            is "REBOOT_CAUSE_HARDWARE_OTHER", the second string can be used
            to pass a description of the reboot cause.
        """
        description = 'None'

        reboot_cause_path = (HOST_REBOOT_CAUSE_PATH + REBOOT_CAUSE_FILE) if self.__is_host(
        ) else (PMON_REBOOT_CAUSE_PATH + REBOOT_CAUSE_FILE)
        prev_reboot_cause_path = (HOST_REBOOT_CAUSE_PATH + PREV_REBOOT_CAUSE_FILE) if self.__is_host(
        ) else (PMON_REBOOT_CAUSE_PATH + PREV_REBOOT_CAUSE_FILE)

        sw_reboot_cause      = self.__read_txt_file(reboot_cause_path) or "Unknown"
        prev_sw_reboot_cause = self.__read_txt_file(prev_reboot_cause_path) or "Unknown"

        if sw_reboot_cause != "Unknown":
            reboot_cause = self.REBOOT_CAUSE_NON_HARDWARE
            description = sw_reboot_cause
        elif prev_reboot_cause_path != "Unknown":
            reboot_cause = self.REBOOT_CAUSE_NON_HARDWARE
            description = prev_sw_reboot_cause

        return (reboot_cause, description)
