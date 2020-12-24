#!/usr/bin/env python

#############################################################################
# Celestica
#
# Module contains an implementation of SONiC Platform Base API and
# provides the fan status which are available in the platform
#
#############################################################################

try:
    from sonic_platform_base.fan_base import FanBase
except ImportError as e:
    raise ImportError(str(e) + "- required module not found")

FAN_MAX_RPM = 25500
PSU_FAN_MAX_RPM = 25500
CPLD_I2C_PATH = "/sys/bus/i2c/devices/11-0066/fan"
PSU_I2C_PATH = "/sys/bus/i2c/devices/{}-00{}/"
PSU_HWMON_I2C_MAPPING = {
    0: {
        "bus": 17,
        "addr": "59"
    },
    1: {
        "bus": 13,
        "addr": "5b"
    },
}

PSU_CPLD_I2C_MAPPING = {
    0: {
        "bus": 17,
        "addr": "51"
    },
    1: {
        "bus": 13,
        "addr": "53"
    },
}


class Fan(FanBase):
    """Platform-specific Fan class"""

    def __init__(self,
                 fan_tray_index,
                 fan_index=0,
                 is_psu_fan=False,
                 psu_index=0):
        self.fan_index = fan_index
        self.fan_tray_index = fan_tray_index
        self.is_psu_fan = is_psu_fan
        self.psu_index = psu_index

        if self.is_psu_fan:
            psu_i2c_bus = PSU_HWMON_I2C_MAPPING[psu_index]["bus"]
            psu_i2c_addr = PSU_HWMON_I2C_MAPPING[psu_index]["addr"]
            self.psu_hwmon_path = PSU_I2C_PATH.format(psu_i2c_bus,
                                                      psu_i2c_addr)
            psu_i2c_bus = PSU_CPLD_I2C_MAPPING[psu_index]["bus"]
            psu_i2c_addr = PSU_CPLD_I2C_MAPPING[psu_index]["addr"]
            self.cpld_path = PSU_I2C_PATH.format(psu_i2c_bus, psu_i2c_addr)

        FanBase.__init__(self)

    def __read_txt_file(self, file_path):
        try:
            with open(file_path, 'r') as fd:
                return fd.read().strip()
        except IOError:
            pass
        return ""

    def __write_txt_file(self, file_path, value):
        try:
            with open(file_path, 'w') as fd:
                fd.write(str(value))
        except Exception:
            return False
        return True

    def get_direction(self):
        """
        Retrieves the direction of fan
        Returns:
            A string, either FAN_DIRECTION_INTAKE or FAN_DIRECTION_EXHAUST
            depending on fan direction
        """
        if not self.is_psu_fan:
            val = self.__read_txt_file(
                CPLD_I2C_PATH + str(self.fan_tray_index) + "_direction")
            direction = self.FAN_DIRECTION_EXHAUST if (
                val == "0") else self.FAN_DIRECTION_INTAKE
        else:
            val = self.__read_txt_file(self.psu_hwmon_path + "psu_fan_dir")
            direction = self.FAN_DIRECTION_EXHAUST if (
                val == "F2B") else self.FAN_DIRECTION_INTAKE
        return direction

    def get_speed(self):
        """
        Retrieves the speed of fan as a percentage of full speed
        Returns:
            An integer, the percentage of full fan speed, in the range 0 (off)
                 to 100 (full speed)

        """
        speed = 0
        if self.is_psu_fan:
            speed = self.__read_txt_file(
                self.psu_hwmon_path + "psu_fan1_speed_rpm")
            speed = (int(speed, 10)) * 100 / PSU_FAN_MAX_RPM
            speed = 100 if (speed > 100) else speed
        elif self.get_presence():
            speed = self.__read_txt_file(CPLD_I2C_PATH + str(
                self.fan_index * 10 + self.fan_tray_index + 1) + "_input")
            speed = (int(speed, 10)) * 100 / FAN_MAX_RPM
            speed = 100 if (speed > 100) else speed
        return int(speed)

    def get_target_speed(self):
        """
        Retrieves the target (expected) speed of the fan
        Returns:
            An integer, the percentage of full fan speed, in the range 0 (off)
                 to 100 (full speed)

        Note:
            speed_pc = pwm_target/255*100

            0   : when PWM mode is use
            pwm : when pwm mode is not use
        """
        return False  #Not supported

    def get_speed_tolerance(self):
        """
        Retrieves the speed tolerance of the fan
        Returns:
            An integer, the percentage of variance from target speed which is
                 considered tolerable
        """
        return False  #Not supported

    def set_speed(self, speed):
        """
        Sets the fan speed
        Args:
            speed: An integer, the percentage of full fan speed to set fan to,
                   in the range 0 (off) to 100 (full speed)
        Returns:
            A boolean, True if speed is set successfully, False if not

        """

        if not self.is_psu_fan and self.get_presence():
            return self.__write_txt_file(
                CPLD_I2C_PATH + "_duty_cycle_percentage", int(speed))

        return False

    def set_status_led(self, color):
        """
        Sets the state of the fan module status LED
        Args:
            color: A string representing the color with which to set the
                   fan module status LED
        Returns:
            bool: True if status LED state is set successfully, False if not
        """
        return False  #Not supported

    def get_presence(self):
        """
        Retrieves the presence of the PSU
        Returns:
            bool: True if PSU is present, False if not
        """
        if self.is_psu_fan:
            val = self.__read_txt_file(self.cpld_path + "psu_present")
            return int(val, 10) == 1

        val = self.__read_txt_file(
            CPLD_I2C_PATH + str(self.fan_tray_index + 1) + "_present")
        return int(val, 10)
