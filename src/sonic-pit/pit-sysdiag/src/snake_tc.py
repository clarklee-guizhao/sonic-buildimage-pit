# -*- coding:utf-8
import time
import os
from test_case import TestCaseCommon
from pit_util_common import run_command
from errcode import E


class SNAKETC(TestCaseCommon):
    def __init__(self, index, logger, platform_cfg_file, case_cfg_file=None):
        MODULE_NAME = "snake_tc"
        TestCaseCommon.__init__(self, index, MODULE_NAME,
                                logger, platform_cfg_file, case_cfg_file)
        self.snake_info_dict = None
        self.sdk_path = None
        self.log_path = None
        self.tx_title = None
        self.rx_title = None
        try:
            if self.platform_cfg_json and "snake_info" in self.platform_cfg_json.keys():
                self.snake_info_dict = self.platform_cfg_json["snake_info"]
                self.sdk_path = self.snake_info_dict["sdk_path"]
                self.log_path = self.snake_info_dict["log_path"]
                self.tx_title = self.snake_info_dict["tx_pkt_title"]
                self.rx_title = self.snake_info_dict["rx_pkt_title"]
                self.package_type = self.snake_info_dict["package_type"]
        except Exception as e:
            self.logger.log_err(str(e), True)
        self.sdk_status = False
        self.port_list = []
        self.port_group = []

    def sdk_command(self, command=None, delay=0.2):
        status = 0
        if command != None:
            cmd = 'pmonutil sdksh "{}"'.format(command)
            status, out = run_command(cmd)
        time.sleep(delay)
        ret, data = run_command('cat {}'.format(self.log_path))
        os.system('echo > {}'.format(self.log_path))
        return status, data.strip().strip(b'\x00')

    def init_sdk(self, also_print_console=False):
        ret = E.EFAIL
        if self.sdk_status:
            ret = E.OK
            return ret
        os.chdir(self.sdk_path)
        check_user_cmd = 'pgrep bcm.user'
        status, out = run_command(check_user_cmd)
        if status:
            self.fail_reason.append("init sdk remote mode fail")
            ret = E.EIO
        else:
            process_id = out
            if process_id != '':
                status, out = run_command('kill -9 {}'.format(process_id))
                if status:
                    self.fail_reason.append("init sdk remote mode fail")
                    ret = E.EIO
                else:
                    if out != '':
                        self.logger.log_info(out, also_print_console)
                    else:
                        ret = E.OK
            else:
                ret = E.OK
        if ret == E.OK:
            clear_log_cmd = 'echo > {}'.format(self.log_path)
            os.system(clear_log_cmd)
            sdk_remote_cmd = './sdk_run.sh -d -f {} >/dev/null 2>&1'.format(
                self.log_path)
            os.system(sdk_remote_cmd)
            status, out = self.sdk_command()
            if not 'Enter daemon mode' in (out.strip().split('\n'))[-1]:
                self.logger.log_info(out, also_print_console)
                ret = E.ESNAKE34001
                self.fail_reason.append("snake sdk enter demon mode fail.")
            else:
                self.sdk_status = True
        else:
            return ret
        self.init_port_list()
        self.init_port_group()
        return ret

    def init_port_list(self):
        self.port_list = []
        status, out = self.sdk_command('ps')
        data = out.strip().split('\n')
        list_index = data.index('Request cmd received: [ps]')
        port_data = data[(list_index)+3:]
        for port_str in port_data:
            self.port_list.append({'port': port_str.replace(
                '(', '').split()[0], 'status': port_str.replace('(', '').split()[2]})

    def init_port_group(self):
        self.port_group = []
        port_g = {}
        port_t = ''.join([i for i in self.port_list[0]['port'] if not i.isdigit()])
        port_g.update({port_t:0})
        for item in self.port_list:
            port_t = ''.join([i for i in item['port'] if not i.isdigit()])
            if port_t in port_g:
                port_g[port_t] += 1
            else:
                port_g.update({port_t:1})
        for key in port_g:
            self.port_group.append('{}0-{}{}'.format(key,key,(port_g[key]-1)))

    def snake_test(self,lb_type='MAC', also_print_console=False):
        ret = self.init_sdk(also_print_console)
        if self.port_list == [] or self.port_group == []:
            ret = E.ESNAKE34002
            self.fail_reason.append("snake port info error.")
        if ret == E.OK:
            for package in self.package_type:
                for group in self.port_group:
                    self.sdk_command('port {} en=on lb={}'.format(group,lb_type) ,delay=1)
                self.init_port_list()
                for port in self.port_list:
                    if port['status'] == 'up':
                        self.sdk_command(
                            'tx {} pbm={} length={} untagged=yes'.format(package['count'], port['port'], package['size']))
                        self.sdk_command('port {} en=off'.format(port['port']))
                        status, out = self.sdk_command('show c')
                        for item in out.strip().split('\n')[3:]:
                            if self.tx_title in item:
                                tx_pkt = item.replace('+', '').split()[-1]
                            if self.rx_title in item:
                                rx_pkt = item.replace('+', '').split()[-1]
                        if tx_pkt == rx_pkt:
                            self.logger.log_info('port {} status {} tx_pkt {} rx_pkt {} pass'.format(
                                port['port'], port['status'], tx_pkt, rx_pkt), also_print_console)
                        else:
                            self.logger.log_err('port {} status {} tx_pkt {} rx_pkt {} fail'.format(
                                port['port'], port['status'], tx_pkt, rx_pkt), also_print_console)
                            ret = E.ESNAKE34003
                            self.fail_reason.append("snake port {} pkt count fail.".format(port['port']))
                    else:
                        self.logger.log_err('port {} status {} fail'.format(
                            port['port'], port['status']), also_print_console)
                        ret = E.ESNAKE34002
                        self.fail_reason.append("snake port {} status error.".format(port['port']))
        if ret != E.OK:
            self.logger.log_err("FAIL!", also_print_console)
        else:
            self.logger.log_info("PASS.", also_print_console)
        return ret

    def snake_mac_test(self, also_print_console=False):
        self.logger.log_info("[SNAKE MAC TEST]:", also_print_console)
        return self.snake_test('MAC',also_print_console)

    def snake_phy_test(self, also_print_console=False):
        self.logger.log_info("[SNAKE PHY TEST]:", also_print_console)
        return self.snake_test('PHY',also_print_console)

    def run_test(self, *argv):
        ret = self.snake_mac_test(True)
        if ret != E.OK:
            return ret
        ret = self.snake_phy_test(True)
        if ret != E.OK:
            return ret
        return ret
