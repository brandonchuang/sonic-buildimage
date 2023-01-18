#############################################################################
# Edgecore
#
# Thermal contains an implementation of SONiC Platform Base API and
# provides the thermal device status which are available in the platform
#
#############################################################################

import os
import os.path
import glob

try:
    from sonic_platform_base.thermal_base import ThermalBase
    from .helper import APIHelper
except ImportError as e:
    raise ImportError(str(e) + "- required module not found")

THERMAL_I2C_PATH = "/sys/bus/i2c/devices/{}-00{}/hwmon/hwmon*/"
PSU_I2C_PATH = "/sys/bus/i2c/devices/{}-00{}/"
PSU_PMBUS_I2C_MAPPING = {
    0: {
        "num": 8,
        "addr": "58"
    },
    1: {
        "num": 9,
        "addr": "59"
    }
}

PSU_EEPROM_I2C_MAPPING = {
    0: {
        "num": 8,
        "addr": "50"
    },
    1: {
        "num": 9,
        "addr": "51"
    }
}

THERMAL_I2C_MAPPING = {
    0: {
        "num": 3,
        "addr": "4a"
    },
    1: {
        "num": 3,
        "addr": "4b"
    },
    2: {
        "num": 3,
        "addr": "4d"
    },
    3: {
        "num": 3,
        "addr": "4e"
    },
    4: {
        "num": 3,
        "addr": "4f"
    }
}

class Thermal(ThermalBase):
    """Platform-specific Thermal class"""

    # SYSFS_PATH = "/sys/bus/i2c/devices/"
    # SYSFS_PATH_PSU = "/sys/devices/platform/as7535_28xb_psu/"

    def __init__(self, thermal_index=0, is_psu=False, psu_index=0):
        self.index = thermal_index
        self.is_psu = is_psu
        self.psu_index = psu_index

        if self.is_psu:
            self.i2c_num = PSU_PMBUS_I2C_MAPPING[self.psu_index]["num"]
            self.i2c_addr = PSU_PMBUS_I2C_MAPPING[self.psu_index]["addr"]
            self.pmbus_path = PSU_I2C_PATH.format(self.i2c_num, self.i2c_addr)

            self.i2c_num = PSU_EEPROM_I2C_MAPPING[self.psu_index]["num"]
            self.i2c_addr = PSU_EEPROM_I2C_MAPPING[self.psu_index]["addr"]
            self.eeprom_path = PSU_I2C_PATH.format(self.i2c_num, self.i2c_addr)
        else:
            # Set sysfs path
            self.i2c_num = THERMAL_I2C_MAPPING[self.index]["num"]
            self.i2c_addr = THERMAL_I2C_MAPPING[self.index]["addr"]
            self.hwmon_path = THERMAL_I2C_PATH.format(self.i2c_num, self.i2c_addr)

        # self.ss_index = self.index + 1

    def __read_txt_file(self, file_path):
        for filename in glob.glob(file_path):
            try:
                with open(filename, 'r') as fd:
                    data = fd.readline().rstrip()
                    if len(data) > 0:
                        return data
            except IOError as e:
                pass

        return None

    def __get_temp(self, path, temp_file):
        file_path = os.path.join(path, temp_file)
        raw_temp = self.__read_txt_file(file_path)
        if raw_temp is not None:
            return float(raw_temp) / 1000
        else:
            return None

    def __set_threshold(self, path, file_name, temperature):
        if self.is_psu:
            return True

        file_path = os.path.join(path, file_name)
        for filename in glob.glob(file_path):
            try:
                with open(filename, 'w') as fd:
                    fd.write(str(temperature))
                return True
            except IOError as e:
                print("IOError")

    def get_temperature(self):
        """
        Retrieves current temperature reading from thermal
        Returns:
            A float number of current temperature in Celsius up to nearest thousandth
            of one degree Celsius, e.g. 30.125
        """
        if self.is_psu:
            if not self.get_presence():
                return None

            power_path = "{}{}".format(self.eeprom_path, 'psu_power_good')
            val = self.__read_txt_file(power_path)
            if val is not None:
                if int(val, 10) != 1:
                    return None

            return self.__get_temp(self.pmbus_path, "psu_temp1_input")
        else:
            return self.__get_temp(self.hwmon_path, "temp1_input")

    def get_high_threshold(self):
        """
        Retrieves the high threshold temperature of thermal
        Returns:
            A float number, the high threshold temperature of thermal in Celsius
            up to nearest thousandth of one degree Celsius, e.g. 30.125
        """
        if self.is_psu:
            return None
        else:
            return self.__get_temp(self.hwmon_path, "temp1_max")

    def set_high_threshold(self, temperature):
        """
        Sets the high threshold temperature of thermal
        Args :
            temperature: A float number up to nearest thousandth of one degree Celsius,
            e.g. 30.125
        Returns:
            A boolean, True if threshold is set successfully, False if not
        """
        if self.is_psu:
            return True
        else:
            return self.__set_threshold(self.hwmon_path, "temp1_max", temperature*1000)

    def get_name(self):
        """
        Retrieves the name of the thermal device
            Returns:
            string: The name of the thermal device
        """
        if self.is_psu:
            return "PSU-{} temp sensor 1".format(self.psu_index+1)
        else:
            return "Temp sensor {}".format(self.index+1)

    def get_presence(self):
        """
        Retrieves the presence of the Thermal
        Returns:
            bool: True if Thermal is present, False if not
        """
        if self.is_psu:
            path = "{}{}".format(self.eeprom_path, "psu_present")
            val = self.__read_txt_file(path)
            return int(val, 10) == 1
        else:
            path = "{}{}".format(self.hwmon_path, "temp1_input")
            val = self.__read_txt_file(path)
            if val is not None:
                return True
            else:
                return False

    def get_status(self):
        """
        Retrieves the operational status of the device
        Returns:
            A boolean value, True if device is operating properly, False if not
        """
        if self.is_psu:
            if not self.get_presence():
                return None

            path = "{}{}".format(self.pmbus_path, "psu_temp_fault")
            val = self.__read_txt_file(path)
            if val is None:
                return False
            else:
                return int(val, 10) == 0
        else:
            if self.get_temperature() is None:
                return False
            else:
                return True

    def get_model(self):
        """
        Retrieves the model number (or part number) of the device
        Returns:
            string: Model/part number of device
        """

        return "N/A"

    def get_serial(self):
        """
        Retrieves the serial number of the device
        Returns:
            string: Serial number of device
        """
        return "N/A"

    def get_position_in_parent(self):
        """
        Retrieves 1-based relative physical position in parent device.
        If the agent cannot determine the parent-relative position
        for some reason, or if the associated value of
        entPhysicalContainedIn is'0', then the value '-1' is returned
        Returns:
            integer: The 1-based relative physical position in parent device
            or -1 if cannot determine the position
        """
        return self.index+1

    def is_replaceable(self):
        """
        Retrieves whether thermal module is replaceable
        Returns:
            A boolean value, True if replaceable, False if not
        """
        return False
