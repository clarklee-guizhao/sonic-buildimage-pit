# -*- coding:utf-8
from pit_util_common import run_command
from test_case import TestCaseCommon
from errcode import E


class SVIDTC(TestCaseCommon):
    def __init__(self, index, logger, platform_cfg_file, case_cfg_file=None):
        MODULE_NAME = "svid_tc"
        TestCaseCommon.__init__(
            self,
            index,
            MODULE_NAME,
            logger,
            platform_cfg_file,
            case_cfg_file)
        self.svid_info_dict = None
        try:
            if self.platform_cfg_json and "svid_info" in self.platform_cfg_json.keys():
                self.svid_info_dict = self.platform_cfg_json["svid_info"]
        except Exception as e:
            self.logger.log_err(str(e), True)

    def svid_test(self, also_print_console=False):
        ret = E.EFAIL
        self.logger.log_info("[SVID HIGH VOLTAGE TEST]:", also_print_console)
        self.logger.log_info("setting voltage...\n", also_print_console)
        get_cmd = "pmonutil volget"
        cmd_list = [
            "pmonutil volset high",
            "pmonutil volset low",
            "pmonutil volset normal"
        ]
        for cmd in cmd_list:
            self.logger.log_info(
                "set svid {} voltage".format(
                    cmd.split()[2]),
                also_print_console)
            status, out = run_command(cmd)
            if status != 0 or len(out) < 0:
                self.fail_reason.append("set svid fail.")
                ret = E.EIO
                self.logger.log_err("FAIL!", also_print_console)
                return ret
            else:
                self.logger.log_info("set svid success!", also_print_console)
                get_status, get_log = run_command(get_cmd)
                if get_status != 0 or len(get_log) <= 0:
                    self.fail_reason.append("get svid fail.")
                    ret = E.EIO
                    self.logger.log_err("FAIL!", also_print_console)
                    return ret
                else:
                    switch_vol_test_readback = round(
                        int(get_log) / float(1000), 1)
                    if switch_vol_test_readback != self.svid_info_dict["{}_voltage".format(
                            format(cmd.split()[2]))]:
                        if cmd.split()[2] == "high":
                            ret = E.ESVID33001
                        elif cmd.split()[2] == "low":
                            ret = E.ESVID33002
                        elif cmd.split()[2] == "normal":
                            ret = E.ESVID33003
                        self.fail_reason.append(
                            "{} voltage not match.".format(
                                cmd.split()[2]))
                        self.logger.log_err("FAIL!", also_print_console)
                        return ret
                    else:
                        ret = E.OK
                        self.logger.log_info("current svid voltage: {}V\n".format(
                            switch_vol_test_readback), also_print_console)
        self.logger.log_info("PASS.", also_print_console)
        return ret

    def run_test(self, *argv):
        ret = self.svid_test(True)
        if ret != E.OK:
            return ret
        return ret
