#!/usr/bin/env python
# -*- coding: utf-8 -*-
__version__ = 'v0.1.0'
__author__  = "Pytool Lishoulei<admin@pytool.com>"
import os
import sys
import json
import traceback
from tabulate import tabulate
from test_case import TestCaseCommon
from errcode import E
from function import load_platform_util_module
from function import restful_command

class PSUTC(TestCaseCommon):
    __PSU_UTIL_MODULE_NAME = "psuutil"
    __PSU_UTIL_CLASS_NAME = "PsuUtil"
    __SENSORUTIL_MODULE_NAME = "sensorutil"
    __SENSORUTIL_CLASS_NAME = "SensorUtil"

    def __init__(self, index, logger, platform_cfg_file, case_cfg_file=None):
        MODULE_NAME = "psu_tc" # this param specified the case config dirictory
        TestCaseCommon.__init__(self, index, MODULE_NAME, logger, platform_cfg_file, case_cfg_file)
        self.psu_util = None
        self.sensor_util = None
        self.psu_info_dict = None
        self.psu_all = None

        try:
            if self.platform_cfg_json and 'psu_info' in self.platform_cfg_json:
                self.psu_info_dict = self.platform_cfg_json['psu_info']
        except Exception as e:
            self.logger.log_err(str(e), True)

        self.position = self.psu_info_dict['position']

        # Load platform utils
        try:
            sensor_util_module = load_platform_util_module(self.__SENSORUTIL_MODULE_NAME)
            sensor_util_class = getattr(sensor_util_module, self.__SENSORUTIL_CLASS_NAME)
            self.sensor_util = sensor_util_class()
        except AttributeError as e:
            self.logger.log_err(str(e))
            sys.exit(1)

        try:
            psu_module = load_platform_util_module(self.__PSU_UTIL_MODULE_NAME)
            psu_util_class = getattr(psu_module, self.__PSU_UTIL_CLASS_NAME)
            self.psu_util = psu_util_class()
        except AttributeError as e:
            msg = "Failed, create PsuUtil instance got exception: {}".format(str(e))
            self.logger.log_err(msg)
            self.logger.log_err(traceback.format_exc())
            sys.exit(2)

        # Fill info
        self.system_air_flow = self.sensor_util.get_sys_airflow()
        self.psu_all = self.psu_util.get_all_raw()
        if not self.psu_all:
            reason = "Failed, get psu all info failed."
            self.logger.log_err(reason)
            sys.exit(3)

        self.psu_count = self.psu_util.get_num_psus()

    def write_sysfs(self,file,v):
        if self.position == "bmc":
            rc,_ = restful_command("echo {} > {}".format(v,file))
            return rc
        else:
            with open(file,'w') as f:
                return f.write(v)

    def read_sysfs(self,file):
        if self.position == "bmc":
            rc,v = restful_command("cat {}".format(file))
            if rc:
                return v
        else:
            with open(file,'r') as f:
                return f.read().strip()
        return ""

    def get_psu_count(self):
        return self.psu_count

    def get_psu_attribute(self,psuid,name):
        try:
            return int(self.read_sysfs('/sys/s3ip/psu/psu{n}/{}'.format(psuid,name)))
        except Exception as e:
            self.fail_reason.append("fail to get psu{}.{}".format(psuid,name))
            self.logger.log_err("fail to get psu{}.{}".format(psuid,name), True)
            return 0

    def test_psu_info(self):
        '''
        S3IP 4.9.4 PSU info test
        a) Test logic
            1) Get PSU count as $(psu_count)
            2) Iterate over all PSUs, with commands
                * Get PSU FRU if applicable
                * Check KEY in FRU if applicable
                * Check PSU status
        b) Result
           b.1) All commands done sucessfully
           b.2) For step a.2): KEY must contains the followings keys
                ["PartNumber", "SerialNumber", "AirFlow", "Presence"]
           b.3) "PartNumber", "SerialNumber", should be non-null strings with differnt chars
           b.4) "Presence" should be "True"
           b.5) "AirFlow"" should be consistent with system airflow
           b.6) $psu_count should be consistent with $system_psu_count
        '''

        self.logger.log_info("test_psu_info start")
        ret = E.OK
        if self.psu_count != self.psu_info_dict['count']:
            reason = "Failed, system psu count %d(expected %d)" \
                     % (self.psu_count, self.psu_info_dict['count'])
            self.log_reason(reason)
            return E.EPSU5001

        for psuid in range(1, self.psu_count+1):
            psu_name = "PSU%d" % psuid

            self.logger.log_dbg("Testing {} info".format(psu_name))
            psu_info = self.psu_all[psu_name]
            if not psu_info:
                reason = "Failed, {} not in all_psu_ninfo".format(psu_name)
                self.log_reason(reason)
                ret = E.EPSU5001
                continue

            # Check presence
            if "Presence" not in psu_info:
                reason = "Failed: {} info, Presence is missing".format(psu_name)
                self.log_reason(reason)
                ret = E.EPSU5001
                continue

            if psu_info['Presence'] != 'yes':
                reason = "Failed: {} is absent".format(psu_name)
                self.log_reason(reason)
                ret = E.EPSU5001
                continue

            # Check FRU keys
            psu_info_keys = ["PartNumber", "SerialNumber", "AirFlow"]
            for info_key in psu_info_keys:
                if info_key not in psu_info:
                    reason = "Failed, {} PSU info key {} missing".format(psu_name, info_key)
                    self.fail_reason.append(reason)
                    self.log_log_dbg(reason)
                    ret = E.EPSU5001

            string_keys = ["PartNumber", "SerialNumber"]
            for str_key in string_keys:
                if len(psu_info[str_key]) < 2:
                    reason = "Failed, {} {} is {}, length too short".format(\
                             psu_name, str_key, psu_info[str_key])
                    self.fail_reason.append(reason)
                    self.log_log_dbg(reason)
                    ret = E.EPSU5001

            air_flow = psu_info["AirFlow"]
            sys_air_flow = self.system_air_flow
            if air_flow != sys_air_flow:
                reason = "Failed, {} airflow {} not consistent with " \
                         "system airflow {}".format(psu_name, air_flow, sys_air_flow)
                self.fail_reason.append(reason)
                self.logger.log_dbg(reason)
                ret = E.EPSU5001
                continue

            self.logger.log_dbg("{} info test done, PASS".format(psu_name))

        if ret == E.OK:
            self.logger.log_info("test_psu_info PASS.", True)
        else:
            self.logger.log_info("test_psu_info FAILED.", True)

        return ret

    def test_psu_status(self):
        '''
        S3IP 4.9.5 Test PSU status
        a) Test logic
           a.1) Get PSU count as $psu_count
           a.2) Iterate over all PSUs with commands
                *) Read PSU input status, include in_status, in_power, in_voltage, in_current
                *) Read PSU input sensor range
                *) Read PSU output status, include out_status, out_power, out_voltage, out_current
                *) Read PSU output sensor range
        b) Result
            1) $(psu_count) should consistent with $(system_psu_count)
            2) in_status should be True, in_power, in_voltage, in_current should be
               in range of in_power_range, in_voltage_range, in_current_range
            3) out_status should True, out_power, out_voltage, out_current should be in
               range of out_power_range, out_voltage_range, out_current_range
        '''
        self.logger.log_info("test_psu_status start")
        ret = E.OK

        if self.psu_count != self.psu_info_dict['count']:
            self.logger.log_err("psu_count FAIL  !", True)
            reason = "Failed, system PSU count %d(expected %d)" \
                     % (self.psu_count, self.psu_info_dict['count'])
            self.fail_reason.append(reason)
            return E.EPSU5001

        for psuid in range(1, self.psu_count+1):
            psu_name = "PSU%d" % psuid

            psu_info = self.psu_all[psu_name]
            self.logger.log_dbg("Testing {} status".format(psu_name))

            try:
                chk_ret = self.check_inputs(psu_name)
                if chk_ret != E.OK:
                    ret = chk_ret
            except Exception as e:
                reason = "Failed, check {} input got exception: {}".format( \
                         psu_name, str(e))
                self.log_reason(reason)
                self.logger.log_err(traceback.format_exc())
                ret = E.EPSU5001

            try:
                chk_ret = self.check_outputs(psu_name)
                if chk_ret != E.OK:
                    ret = chk_ret
            except Exception as e:
                reason = "Failed, check {} output got exception: {}".format( \
                         psu_name, str(e))
                self.log_reason(reason)
                self.logger.log_err(traceback.format_exc())
                ret = E.EPSU5001

            self.logger.log_dbg("{} info test done, PASS".format(psu_name))

        return ret

    def check_inputs(self, psu_name):
        #j = json.dumps(psu_info, sort_keys=True, indent=4, separators=(',', ': '))
        #print j
        ret = E.OK
        psu_info = self.psu_all[psu_name]
        psu_inputs = psu_info["Inputs"]
        input_keys = ["Status", "Voltage", "Current", "Power"]
        input_vars = [None, None, None, None]
        input_key_error_code = [E.EPSU5007, E.EPSU5002, E.EPSU5003, E.EPSU5008]

        self.logger.log_dbg("Checking {} inputs status".format(psu_name))
        in_key_len = len(input_keys)
        for keyid in range(in_key_len):
            in_key = input_keys[keyid]
            if in_key not in psu_inputs:
                reason = "Failed, {} status missing {}".format(psu_name, in_key)
                self.log_reason(reason)
                ret = E.EPSU5007

            input_vars[keyid] = psu_inputs[input_keys[keyid]]
            if in_key == "Status":
                if input_vars[keyid] != True:
                    reason = "Failed, {} input status is NOT True"
                    self.log_reason(reason)
                    break    # Don't check others if input stauts is not True
            else:
                try:
                    low_thd = input_vars[keyid]["LowAlarm"]
                    high_thd = input_vars[keyid]["HighAlarm"]
                    value = input_vars[keyid]["Value"]
                except Exception as e:
                    reason = "Failed, {} input {} value {} malformed".format( \
                             psu_name, in_key, input_vars[keyid])
                    self.log_reason(reason)
                    ret = E.EPSU5007

                if value < low_thd or value > high_thd:
                    reason = "{} input {} out of range, value {}(expected {}~{})".format(\
                             psu_name, in_key, value, low_thd, high_thd)
                    self.log_reason(reason)
                    ret = input_key_error_code[keyid]

        if ret == E.OK:
            self.logger.log_dbg("{} inputs status check done, PASS".format(psu_name))
        else:
            self.logger.log_dbg("{} inputs status check done, FAILED".format(psu_name))

        return ret

    def check_outputs(self, psu_name):
        ret = E.OK
        psu_info = self.psu_all[psu_name]
        psu_outputs = psu_info["Outputs"]
        output_keys = ["Status", "Voltage", "Current", "Power"]
        output_vars = [None, None, None, None]
        output_key_error_code = [E.EPSU5007, E.EPSU5004, E.EPSU5005, E.EPSU5009]

        self.logger.log_dbg("Checking {} outputs status".format(psu_name))
        out_key_len = len(output_keys)
        for keyid in range(out_key_len):
            out_key = output_keys[keyid]
            if out_key not in psu_outputs:
                reason = "Failed, {} status missing {}".format(psu_name, out_key)
                self.log_reason(reason)
                ret = E.EPSU5007

            output_vars[keyid] = psu_outputs[output_keys[keyid]]
            if out_key == "Status":
                if output_vars[keyid] != True:
                    reason = "Failed, {} output status is NOT True"
                    self.log_reason(reason)
                    break    # Don't check others if output stauts is not True
            else:
                try:
                    low_thd = output_vars[keyid]["LowAlarm"]
                    high_thd = output_vars[keyid]["HighAlarm"]
                    value = output_vars[keyid]["Value"]
                except Exception as e:
                    reason = "Failed, {} output {} value {} malformed".format( \
                             psu_name, in_key, output_vars[keyid])
                    self.log_reason(reason)
                    ret = E.EPSU5007

                if value < low_thd or value > high_thd:
                    reason = "{} output {} out of range, value {}(expected {}~{})".format(\
                             psu_name, in_key, value, low_thd, high_thd)
                    self.log_reason(reason)
                    ret = output_key_error_code[keyid]

        if ret == E.OK:
            self.logger.log_dbg("{} outputs status check done, PASS".format(psu_name))
        else:
            self.logger.log_dbg("{} outputs status check done, FAILED".format(psu_name))
        return E.OK

    def run_test(self, *argv):
        final_result = E.OK
        try:
            ret = self.test_psu_info()
            if ret != E.OK :
                final_result = ret
        except Exception as e:
            reason = "Failed, {} test_psu_info exception: {}".format(self.get_tc_name(), str(e))
            self.log_reason(reason)
            self.logger.log_err(traceback.format_exc())
            final_result = E.EFAIL

        try:
            ret = self.test_psu_status()
            if ret != E.OK :
                return ret
        except Exception as e:
            reason = "Failed, {} test_psu_status exception: {}".format(self.get_tc_name(), str(e))
            self.log_reason(reason)
            self.logger.log_err(traceback.format_exc())
            final_result = E.EFAIL

        return final_result
