# Firmware upgrade test requirement

#### 1. Firmware upgrade test cases support only manual mode, and it should be used under development test and manufacturing test stage. Test with param '-g manufacture -t manual'

#### 2. When firmware upgrade test is run, select test item manually. Current supported tests are: Upgrade firmware on Master/Primary flash and verify; upgrade firmware on slave/secondary flash and verify.

```shell
1.save master running firmware version and program test firmware
2.check master test firmware version and program baseline firmware
3.check master baseline firmware version
4.save slave running firmware version and program test firmware
5.check slave test firmware version and program baseline firmware
6.check slave baseline firmware version
```

#### 3. Example test case configuration

```json
{
    "software_system":{
        "sysdiag_version":"1.1",
        "timezone":"Asia/Shanghai",
        "sonic_version":"SONiC.dev_202012_td4_100g.0-dirty-20220118.203718"
    },
    "cpld_firmware_type":["LED_CPLD1","LED_CPLD2","FAN_CPLD","SYS_CPLD"],
    "fpga_firmware_type":["FPGA"],
    "bios_firmware_type":["BIOS"],
    "switch_firmware_type":["SWITCH_PCIE"],
    "cpld_firmware_baseline":{
        "SYS_CPLD": {
            "absolute_path":true,
            "file_path": "/etc/muxi/fw/8853-48cd8dq-w/components_fw/TD4_syscpld_v0b.25h.vme",
            "slave_upgrade":false,
            "same_with_master":false,
            "slave_file_path":"/etc/muxi/fw/8853-48cd8dq-w/components_fw/TD4_syscpld_v0b.25h.vme"
        },
        "LED_CPLD1":  {
            "absolute_path":false,
            "file_path": ""
        },
        "LED_CPLD2":  {
            "absolute_path":false,
            "file_path": "",
            "slave_upgrade":false,
            "same_with_master":false,
            "slave_file_path":""
        },
        "FAN_CPLD":  {
            "absolute_path":false,
            "file_path": "",
            "slave_upgrade":false,
            "same_with_master":false,
            "slave_file_path":""
        }
    },
    "fpga_firmware_baseline":{
        "FPGA":  {
            "absolute_path":false,
            "file_path": "",
            "slave_upgrade":false,
            "same_with_master":false,
            "slave_file_path":""
        }
    },
    "bios_firmware_baseline":{
        "FPGA":  {
            "absolute_path":false,
            "file_path": "",
            "version": "",
            "slave_upgrade":false,
            "same_with_master":false,
            "slave_file_path":"",
            "slave_version":""
        }
    },
    "switch_firmware_baseline":{
        "SWITCH_PCIE":  {
            "absolute_path":false,
            "file_path": "",
            "version": "",
            "slave_upgrade":false,
            "same_with_master":false,
            "slave_file_path":"",
            "slave_version":""
        }
    },
    "cpld_firmware_test":{
        "SYS_CPLD": {
            "absolute_path":true,
            "file_path": "/etc/muxi/fw/8853-48cd8dq-w/components_fw/TD4_syscpld_v0b.25h.vme",
            "slave_upgrade":false,
            "same_with_master":false,
            "slave_file_path":"/etc/muxi/fw/8853-48cd8dq-w/components_fw/TD4_syscpld_v0b.25h.vme"
        },
        "LED_CPLD1":  {
            "absolute_path":false,
            "file_path": "",
            "version": ""
        },
        "LED_CPLD2":  {
            "absolute_path":false,
            "file_path": "",
            "version": ""
        },
        "FAN_CPLD":  {
            "absolute_path":false,
            "file_path": "",
            "version": ""
        }
    },
    "fpga_firmware_test":{
        "FPGA":  {
            "absolute_path":false,
            "file_path": "",
            "version": "",
            "slave_upgrade":false,
            "same_with_master":false,
            "slave_file_path":"",
            "slave_version":""
        }
    },
    "bios_firmware_test":{
        "FPGA":  {
            "absolute_path":false,
            "file_path": "",
            "version": "",
            "slave_upgrade":false,
            "same_with_master":false,
            "slave_file_path":"",
            "slave_version":""
        }
    },
    "switch_firmware_test":{
        "SWITCH_PCIE":  {
            "absolute_path":false,
            "file_path": "",
            "version": "",
            "slave_upgrade":false,
            "same_with_master":false,
            "slave_file_path":"",
            "slave_version":""
        }
    }

}

```

##### 3.1 @firmware_type is list of firmware types to be upgraded, it'll be passed to FwMgrUtil (Platform plugins) class object and will invoke firmware_upgrade method to upgrde it. Firmware upgrade order is defined by list order.

##### 3.2 firmware_baseline is baseline firmware version, before TEST, running version of all firmware will be saved, after TEST, all original version will be restore and check.

##### 3.3 Each type of logical device, it has a set of params:


```json
 {
            "absolute_path":true,
            "file_path": "/etc/muxi/fw/8853-48cd8dq-w/components_fw/TD4_syscpld_v0b.24h.vme",
            "version": "b.24",
            "slave_upgrade"：true,
            "same_with_master":true,
            "slave_file_path":""，
            "slave_version":""
},
```

###### 3.3.1 @absolute_path is used to indicate whether the firmware_file use absolute path, if not specified, the path of firmware file will be appended a prefix $(PIT_SRC_DIR)/config/platform/$(PLATFORM_NAME)/

###### 3.3.2 @version is target version of primary flash firmware after upgrade; @slave_version is target version of secondary firmware after upgrade.

###### 3.3.3 @slave_upgrade indicates whether primary/secondary upgrqade is supported; @same_with_master indiates whether to use the same firmware file to test primary and secondary flash upgrade.

##### 4. Mandatory method in fwmgrutil.py:
         get_fw_version、firmware_upgrade、firmware_refresh, example implementation as follow

```python
    def get_fw_version(self, fw_type_list, fw_extr=None):
        """
            @fw_type_list firmware type list, should be list of the strings:'bios', 'uboot', 'bmc', 'cpld', .etc.
            @fw_extra OPTIONAL, extra information string, for fw_type 'BIOS'/'Uboot'/'BMC', value should be one of 'master'/'slave'
        	Retrieves all firmwares' version on the device
        	@return DICT, key=firmware name, value=DICT,include "version" and "description"
        """
        result = {}
        ret = run_command("show platform  firmware status")
        for item in fw_type_list:
            for str in ret.splitlines():
                if item in str:
                    str_list = str.split()
                    str_len = len(str_list)
                    for i in range(0, str_len):
                        if item == str_list[i]:
                            result[item] = {}
                            result[item]['version'] = str_list[i + 1]
                            desc = ''
                            for j in range(i + 2, str_len):
                                desc += str_list[j] + ' '
                            result[item]['description'] = desc
                            break
        return result

```

```python
    def firmware_upgrade(self, fw_type, fw_path, fw_extr=None):
        """
        	@fw_type: firmware type, should be one of the strings:'bios', 'uboot', 'bmc', 'cpld', .etc.
        	@fw_path: target firmware file
        	@fw_extra OPTIONAL, extra information string, for fw_type 'BIOS'/'Uboot'/'BMC', value should be one of 'master'/'slave'/'both'
        	@return: Boolean
        """
        cmd = "config platform firmware install chassis component %s fw %s -y" % (fw_type, fw_path)
        ret = False
        try:
            retstr = run_command(cmd, True)
            for line in retstr.splitlines():
                if ("%s upgrade success" % fw_type) in line:
                    print(line)
                    ret = True
                    break
        except Exception as e:
            print(str(e))
        return ret
```

```python
 def firmware_refresh(self, fw_extra=None):
        # os.system("sleep 10; shutdown now &")
        return True
```

##### 5. @running_version_dict is used to store firmware versions before TEST, saved in file master_firmware_baseline.json; it will also be used to restore original firmware version and be check.

```json
{
    "SYS_CPLD": {
        "version": "b.25",
        "description": "Mianboard System CPLD code version "
    },
    "LED_CPLD1": {
        "version": "1.5",
        "description": "LED_CPLD1 code version "
    },
    "LED_CPLD2": {
        "version": "1.7",
        "description": "LED_CPLD2 code version "
    },
    "FAN_CPLD": {
        "version": "a.a",
        "description": "FAN_CPLD code version "
    },
    "FPGA": {
        "version": "4a.6",
        "description": "Subcard borad FPGA code version "
    },
    "BIOS": {
        "version": "v09.0B.00.02",
        "description": "Basic Input/Output System code version "
    }
}
```

Note:
@get_fw_version MUST return dict in above format, otherwise version verification may failed.
