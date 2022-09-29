#!/usr/bin/env python
# -*- coding: utf-8 -*-
__version__ = 'v0.1.0'
__author__  = "Pytool Li<admin@pytool.com>"
import os
from re import T
import sys
import json
import time
import requests
import traceback
from tabulate import tabulate
from test_case import TestCaseCommon
from errcode import *
from function import load_platform_util_module


from function import restful_command

DEFAULT_FAN_CONTROL_INTERVAL = 5  # interval for fan control command

class FANTC(TestCaseCommon):
    __FANUTIL_MODULE_NAME = "fanutil"
    __FANUTIL_CLASS_NAME = "FanUtil"
    __SENSORUTIL_MODULE_NAME = "sensorutil"
    __SENSORUTIL_CLASS_NAME = "SensorUtil"

    def __init__(self, index, logger, platform_cfg_file, case_cfg_file=None):
        MODULE_NAME = "fan_tc" # this param specified the case config dirictory
        TestCaseCommon.__init__(self, index, MODULE_NAME, logger, platform_cfg_file, case_cfg_file)

        self.fan_util = None
        self.fan_info_dict = None  # Expected result
        self.fan_all = None        # fan info read from H/W

        # Load platform test case list and per case test configuration
        try:
            if self.platform_cfg_json and 'fan_info' in self.platform_cfg_json:
                self.fan_info_dict = self.platform_cfg_json['fan_info']
        except Exception as e:
            self.logger.log_err(str(e), True)

        self.position = self.fan_info_dict['position']

        # Load platform utils
        try:
            sensor_util_module = load_platform_util_module(self.__SENSORUTIL_MODULE_NAME)
            sensor_util_class = getattr(sensor_util_module, self.__SENSORUTIL_CLASS_NAME)
            self.sensor_util = sensor_util_class()
        except AttributeError as e:
            self.logger.log_err(str(e))
            sys.exit(1)

        try:
            fan_util_module = load_platform_util_module(self.__FANUTIL_MODULE_NAME)
            fan_util_class = getattr(fan_util_module, self.__FANUTIL_CLASS_NAME)
            self.fan_util = fan_util_class()
        except AttributeError as e:
            self.logger.log_err(str(e))
            sys.exit(2)

        # Fill information
        self.system_air_flow = self.sensor_util.get_sys_airflow()
        self.fan_all = self.fan_util.get_all_raw()
        if not self.fan_all:
            self.logger.log_err("Failed to get all fan status")
            sys.exit(1)

        self.fan_count = self.get_fan_count()

    def get_fan_count(self):
        if self.fan_all:
            return self.fan_all["Number"]
        else:
            return self.fan_util.get_num_fans()

    def get_motor_count(self, fanid):
        fan_name = "FAN%d" % fanid
        if fan_name not in self.fan_all or "Rotors" not in fan_all[fan_name]:
            return -1
        else:
            return fan_all[fan_name]["Rotors"]

    # Speed test, per fan per rotor
    def speed_check(self, fan_all, ratio):
        ret = E.OK
        fan_count = fan_all["Number"]
        speed_tolerance = self.fan_info_dict["speed_tolerance"]

        msg = "speed_check: count {}, tolerance {}, ratio {}%".format(\
              fan_count, speed_tolerance, ratio)
        self.logger.log_dbg(msg)

        for fanid in range(1, fan_count+1):
            fan_name = "FAN%d" % fanid
            fan_info = fan_all[fan_name]
            num_motors = fan_info["Rotors"]
            for motorid in range(1, num_motors+1):
                motor_name = "Rotor%d" % motorid
                try:
                    speed = fan_info[motor_name]["Speed"]
                    speed_max = fan_info[motor_name]["SpeedMax"]
                    speed_min = fan_info[motor_name]["SpeedMin"]
                except Exception as e:
                    reason = "Failed to get {} {} info, missing " \
                             "Speed/SpeedMin/SpeedMax".format(fan_name, motor_name)
                    self.log_reason(reason)
                    self.logger.log_err(traceback.format_exc())
                    ret = E.EFAN6005
                    continue

                # Check speed range
                if speed > speed_max or speed < speed_min:
                    reason = "{} {} speed {} out of range.".format(fanid+1, motorid+1)
                    self.log_reason(reason)
                    ret = E.EFAN6005
                    continue

                # Check controlled fan speed
                speed_target = speed_min + ratio*(speed_max-speed_min)/100
                speed_delta = speed_target - speed
                if (speed_delta > (-speed_tolerance)) and (speed_delta < speed_tolerance):
                    msg = "{} {} fan control test done, PASS"
                    self.logger_dbg(msg)
                else:
                    reason = "Failed, {} {} ratio {}%, speed {}, target speed {}".format(\
                             fan_name, motor_name, ratio, speed, speed_target)
                    self.log_reason(reason)
                    ret = E.EFAN6005

        return ret

    def test_fan_info(self):
        '''
        S3IP 4.9.1 Fan Info Test
        a) Test logic
           a.1) Get fan count as $fan_count
           a.2) Iterate over all fans, with commands
                * Get fan FRU if applicable
                * Check KEY in FRU if applicable
                * Check fan status
        b) Result
           b.1) All commands done sucessfully
           b.2) For step a.2): KEY must contains the followings keys
                ["PartNumber", "SerialNumber", "AirFlow", "Presence"]
           b.3) "PartNumber", "SerialNumber", should be non-null strings with differnt chars
           b.4) "Presence" should be "True"
           b.5) "AirFlow"" should be consistent with system airflow
           b.6) $fan_count should be consistent with $system_fan_count
        '''

        self.logger.log_info("test_fan_info start")
        ret = E.OK
        self.fan_count = self.get_fan_count()
        if self.fan_count != self.fan_info_dict['count']:
            reason = "Failed, system fan count %d(expected %d)" \
                     % (self.fan_count, self.fan_info_dict['count'])
            self.log_reason(reason)
            return E.EFAN6001

        self.logger.log_dbg("System fan count %d, OK" % self.fan_count)

        for fanid in range(1, self.fan_count+1):
            fan_name = "FAN%d" % fanid

            self.logger.log_dbg("Testing {} info".format(fan_name))
            fan_info = self.fan_all[fan_name]
            if not fan_info:
                reason = "Failed, {} not in all_fan_info".format(fan_name)
                self.log_reason(reason)
                continue

            # Check presence
            if "Presence" not in fan_info:
                reason = "Failed: {} info, Presence is missing".format(fan_name)
                self.log_reason(reason)
                continue

            if fan_info['Presence'] != 'yes':
                reason = "Failed: {} is absent".format(fan_name)
                self.log_reason(reason)
                ret = E.EFAN6004
                continue

            # Check FRU keys
            fan_info_keys = ["PartNumber", "SerialNumber", "AirFlow"]
            for info_key in fan_info_keys:
                if info_key not in fan_info:
                    reason = "Failed, {} fan info key {} missing".format(fan_name, info_key)
                    self.fail_reason.append(reason)
                    self.log_log_dbg(reason)
                    ret = E.EFAN6001

            string_keys = ["PartNumber", "SerialNumber"]
            for str_key in string_keys:
                if len(fan_info[str_key]) < 2:
                    reason = "Failed, {} {} is {}, length too short".format(\
                             fan_name, str_key, fan_info[str_key])
                    self.fail_reason.append(reason)
                    self.log_log_dbg(reason)
                    ret = E.EFAN6001

            air_flow = fan_info["AirFlow"]
            sys_air_flow = self.system_air_flow
            if air_flow != sys_air_flow:
                reason = "Failed, {} airflow {} not consistent with " \
                         "system airflow {}".format(fan_name, air_flow, sys_air_flow)
                self.fail_reason.append(reason)
                self.logger.log_dbg(reason)
                ret = E.EFAN6001
                continue

            self.logger.log_dbg("{} info test done, PASS".format(fan_name))

        if ret == E.OK:
            self.logger.log_info("test_fan_info PASS.", True)
        else:
            self.logger.log_info("test_fan_info FAILED.", True)

        return ret

    def test_fan_motor_status(self, fan_name):
        ret = E.OK
        fan_info = self.fan_ll[fan_name]
        motor_count = fan_info["Rotors"]

        for motorid in range(1, motor_count+1):
            motor_name = "Rotor%d" % motorid
            motor_info = fan_info[motor_name]

            # Check running
            running = motor_info["Running"]
            if running != "yes":
                reason = "{} {} running status {}(expected 'yes')".format( \
                         fan_name, motor_name, running)
                self.fail_reason.append(reason)
                ret = E.EFAN6003

            # Check Hardware alarm
            hwalarm = motor_info["HwAlarm"]
            if hwalarm != "no":
                reason = "{} {} hardware alarm status {}(expected 'no')".format( \
                         fan_name, motor_name, hwalarm)
                self.fail_reason.append(reason)
                ret = E.EFAN6003

            try:
                speed = int(motor_info["Speed"])
                speed_min = int(motor_info["SpeedMin"])
                speed_max = int(motor_info["SpeedMax"])
                if speed not in range(speed_min, speed_max):
                    reason = "Failed, {} {} speed {} not in range {}~{}".format( \
                             fan_name, motor_name, speed, speed_min, speed_max)
                    self.fail_reason.append(reason)
                    ret = E.EFAN6002
            except Exception as e:
                reason = "Failed, {} {} Speed/SpeedMin/SpeedMax invalid".format(\
                         fan_name, motor_name)
                self.fail_reason.append(reason)
                ret = E.EFAN6001

        return ret

    def test_fan_status(self):
        '''
        S3IP 4.9.2 Fan Status Test
        a) Test logic
           a.1) Get fan count as $fan_count
           a.2) Iterate over all fans, with commands
                * Get motor count
                * Get motor speed, running_state, alarm_status
                * Get speed range of each motor
                * Check runing_state, alarm_status
        b) Result
           b.1) $fan_count match system expected $system_fan_count
           b.2) All commands done sucessfully
           b.3) $running_state should be 'True' for each motor
           b.4) $alarm_status should be 'False' for each motor
           b.4) $speed should be in range($speed_min, $speed_max) for each motor
        '''
        ret = E.OK
        self.logger.log_info("test_fan_status start", True)
        self.fan_count = self.get_fan_count()
        if self.fan_count != self.fan_info_dict['count']:
            reason = "Failed, system fan count %d(expected %d)" \
                     % (self.fan_count, self.fan_info_dict['count'])
            self.fail_reason.append(reason)
            return E.EFAN6001

        for fanid in range(1, self.fan_count+1):
            fan_name = "FAN%d" % fanid

            self.logger.log_dbg("Testing {} status".format(fan_name))
            fan_info = self.fan_all[fan_name]
            motor_count = fan_info["Rotors"]
            if motor_count != self.fan_info_dict["motor_count"]:
                reason = "Failed, {} motor count {}(expected {}".format(
                         fan_name, motor_count, self.fan_info_dict["motor_count"])
                self.fail_reason.append(reason)
                ret = E.EFAN6001
                continue

                fan_ret = self.test_fan_motor_status(fan_name)
                if fan_ret != E.OK:
                    ret = fan_ret
                    self.logger.log_err("{} speed test failed.".format(fan_name))

            self.logger.log_dbg("{} fan status test done, PASS".format(fan_name))

        if ret == E.OK:
            self.logger.log_dbg("test_fan_status PASS.")
        else:
            self.logger.log_dbg("test_fan_status FAILED.")

        return ret


    def test_fan_control(self):
        '''
        S3IP 4.9.3 Fan Control Test
        a) Test logic
           a.1) Stop fan control service
           a.2) Set fan speed to $fan_speed_test
           a.3) Wait $stable_interval seconds, let fan speed to be stable
           a.4) Read fan speed back as $fan_speed_readback, check against $fan_speed_test
           a.5) Iterate over stop a.2 ~ a.4, for 3 differnt value
           a.6) Restart fan control service
        b) Result
           b.1) All commands done sucessfully
           b.2) $fan_speed_test should be consistent with $fan_speed_readback for each iteration
        '''
        ret = E.OK
        if "fan_control_interval" in self.fan_info_dict:
            control_interval = self.fan_info_dict["fan_control_interval"]
        else:
            control_interval = DEFAULT_FAN_CONTROL_INTERVAL

        self.logger.log_info("test_fan_control start")
        self.stop_services()

        for ratio in self.fan_info_dict["ratio_target"]:
            if not self.fan_util.set_fan_speed_ratio(ratio):
                reason = "Failed, set all fan speed ratio to {} failed.".format(ratio)
                self.log_reason(reason)
                ret = E.EFAN6005
                continue

            time.sleep(control_interval)
            try:
                # Instant update
                fan_all = self.fan_util.get_all_raw()
            except Exception as e:
                reason = "Failed, get all fan info got exception: {}".format(str(e))
                self.log_reason(reason)
                self.logger.log_err(traceback.format_exc())
                ret = E.EFAN6005

            chk_ret = self.speed_check(fan_all, ratio)
            if chk_ret != E.OK:
                ret = chk_ret

        if ret == E.OK:
            self.logger.log_info("test_fan_control PASS.", True)
        else:
            self.logger.log_info("test_fan_control FAILED.", True)

        self.restore_services()
        return ret

    def run_test(self, *argv):
        final_result = E.OK

        try:
            ret = self.test_fan_info()
            if ret != E.OK :
                final_result = E.EFAIL
        except Exception as e:
            reason = "Failed, {} test_fan_info exception: {}".format(self.get_tc_name(), str(e))
            self.fail_reason.append(reason)
            self.logger.log_err(traceback.format_exc())
            self.logger.log_err(reason)

        try:
            ret = self.test_fan_status()
            if ret != E.OK :
                final_result = E.EFAIL
        except Exception as e:
            reason = "Failed, {} test_fan_status exception: {}".format(self.get_tc_name(), str(e))
            self.fail_reason.append(reason)
            self.logger.log_err(traceback.format_exc())
            self.logger.log_err(reason)

        try:
            ret = self.test_fan_control()
            if ret != E.OK :
                final_result = E.EFAIL
        except Exception as e:
            reason = "Failed, {} test_fan_control exception: {}".format(self.get_tc_name(), str(e))
            self.fail_reason.append(reason)
            self.logger.log_err(traceback.format_exc())
            self.logger.log_err(reason)

        return final_result

    def stop_services(self):
        self.fan_util.stop_fan_control()

    def restore_services(self):
        self.fan_util.start_fan_control()
