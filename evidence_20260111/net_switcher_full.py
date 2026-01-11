import sys
import time
from cyclonedds.domain import DomainParticipant
from cyclonedds.topic import Topic
from cyclonedds.pub import DataWriter
from unitree_go.msg.dds_ import *
from std_msgs.msg.dds_ import *
from unitree_api.msg.dds_ import *
from fourg_agent import *
from utils import *
import asyncio
import json
import os
import subprocess
import psutil
import threading

from enum import Enum

from datetime import datetime, timezone, timedelta

class NetworkStatus(Enum):
    DISCONNECTED = 1
    ON_WIFI_CONNECTED = 2
    ON_4G_CONNECTED = 3

class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

global network_status
global network_status_before
network_status = NetworkStatus.DISCONNECTED
network_status_before = NetworkStatus.DISCONNECTED

global fourG_switch
fourG_switch = FourGSwitchStatus.ON

global tx_mb_4g_init
global tx_mb_4g_last_report
global tx_mb_4g_report_quantity
tx_mb_4g_init = 0
tx_mb_4g_last_report = 0
tx_mb_4g_report_quantity = 50

pull_wlan0_interface_up_cmd = "sudo ifconfig wlan0 up"
pull_wwan0_interface_up_cmd = "sudo ifconfig wwan0 up"

module_4gcm_start_cmd = "/unitree/sbin/mscli start 4gcm"
module_4gcm_stop_cmd  = "/unitree/sbin/mscli stop 4gcm"
pull_wwan0_interface_down_cmd = "sudo ifconfig wwan0 down"

wlan0_reconfigure_cmd = "wpa_cli -i wlan0 reconfigure"

public_network_wifi_interface = "wlan0"
public_network_4g_interface = "wwan0"

target_address_wifi = "8.8.8.8"
target_address_4g = "robot-mqtt.unitree.com"

robot_ver_file_path = "/unitree/robot/basic/ver"

shanghai_tz = timezone(timedelta(hours=8))
time_format = "%Y-%m-%d %H:%M:%S"

network_status_write_cd = threading.Condition()
global domainParticipant

# need check from ZMJ
def update_4g_target_address():
    command = ["sudo", "cat", "/unitree/robot/basic/country"]
    try:
        output = subprocess.check_output(command)
        content = output.decode("utf-8")
        if content != "CN":
            target_address_4g = "global-robot-mqtt.unitree.com"

    except subprocess.CalledProcessError as e:
        print("Error:", e)

def ping_target(interface, target_address, result_dict):
    # print("[net switcher] ping_target() interface=", interface,
    #       "target_address=", target_address)
    # print("[net switcher] datetime.now()=", datetime.now(),
    #       ", target_address=", target_address)
    try:
        result = subprocess.run(['ping', '-c', '1', '-I', interface, target_address],
                                capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and '1 packets transmitted, 1 received' in result.stdout:
            # print("[net switcher]", interface ,"reachable!")
            result_dict[target_address] = True
        else:
            # print("[net switcher]", interface ,"not reachable!")
            result_dict[target_address] = False
    except subprocess.TimeoutExpired:
        # print("[net switcher] datetime.now()=", datetime.now(),
        #       ", target_address=", target_address)
        # print("[net switcher]", interface ," ping tiemout, not reachable!")
        result_dict[target_address] = False


def is_public_network_reachable(interface, target_address):
    # print("[net switcher] is_public_network_reachable() enter, interface=", interface)
    target_addresses = ["8.8.8.8", "8.8.4.4",
                        "1.1.1.1", "1.0.0.1",
                        "208.67.222.222",
                        "114.114.114.114",
                        "1.2.4.8", "210.2.4.8",
                        "180.76.76.76",
                        "119.29.29.29",
                        "223.5.5.5", "223.6.6.6"]
    result_dict = {target: False for target in target_addresses}
    threads = []
    for target in target_addresses:
        thread = threading.Thread(target=ping_target, args=(interface, target, result_dict))
        threads.append(thread)
        thread.start()

    threads_in_work = True
    while threads_in_work:
        time.sleep(0.1)
        for target, result in result_dict.items():
            if result:
                print(f"{'[net switcher] ping'} {target}: {' Ping OK'}")
                return True

        for thread in threads:
            if not thread.is_alive():
                threads_in_work = False
                break
    return False

def is_network_reachable(interface, target_address):
    print(f"[net switcher] [{datetime.now()}] is_network_reachable() interface=", interface,
          ", target_address=", target_address,
          ", start ping test")
    try:
        result = subprocess.run(['ping', '-c', '1', '-I', interface, target_address],
                                capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and '1 packets transmitted, 1 received' in result.stdout:
            print(f"[net switcher] [{datetime.now()}] is_network_reachable() interface=", interface,
                  ", target_address=", target_address,
                  ", 4G(wwan0) public network reachable!")
            return True
        else:
            print("[net switcher]", interface ,"NOT reachable!")
            return False
    except subprocess.TimeoutExpired:
        print("[net switcher]", interface ,"NOT reachable!")
        return False

def check_interface_is_up(interface):
    try:
        output = subprocess.check_output(["ifconfig", interface])
        output = output.decode("utf-8")
        if interface in output and "UP" in output:
            return True
        else:
            return False
    except subprocess.CalledProcessError:
        return False

def check_interface_and_pull_up(interface_name):
    is_interface_up = check_interface_is_up(interface_name)
    if is_interface_up == False:
        if interface_name == public_network_wifi_interface:
            run_command(pull_wlan0_interface_up_cmd)
        elif interface_name == public_network_4g_interface:
            run_command(pull_wwan0_interface_up_cmd)

def run_command(command):
    print("run_command() command=", command)
    process = subprocess.Popen(command, shell=True)
    process.wait()
    code = process.returncode
    print("run_command() code=", code)
    return process.returncode

def log_network_status():
    utc_time = datetime.now(timezone.utc)
    shanghai_time = utc_time.astimezone(shanghai_tz)
    formatted_time = shanghai_time.strftime(time_format)
    print(f"[net switcher] [{formatted_time}], newwork_status={network_status}")

def check_valid_ip(ip):
    return True if ip and not ip.startswith(('192.168.')) else False

def get_ip_address(interface):
    try:
        result = subprocess.check_output(["ifconfig", interface])
        ip_lines = str(result).split("\\n")
        for line in ip_lines:
            if "inet " in line:
                ip = line.split("inet ")[1].split(" ")[0]
                return ip
        return None
    except subprocess.CalledProcessError:
        return None

def wait_wwan0_get_valid_ip_address():
    start_time = time.time()
    max_wait_time = 80
    wait_time_in_seconds = 0

    while time.time() - start_time < max_wait_time:
        ip = get_ip_address("wwan0")
        if check_valid_ip(ip):
            print("wwan0 has obtained a valid IP address:", ip)
            return ip
        time.sleep(1)
        wait_time_in_seconds = wait_time_in_seconds + 1
        print("wait_time_in_seconds=", wait_time_in_seconds)

    print("Timeout: wwan0 did not obtain a valid IP address within", max_wait_time ,"seconds.")
    return None

def is_air_version():
    try:
        with open(robot_ver_file_path, 'r') as file:
            content = file.read()
            last_digit = content[7]
            version_number = int(last_digit)
            if version_number == 1:
                print("AIR verison")
                return 1
            else:
                print("NON AIR verison")
                return 0
    except FileNotFoundError:
        print("The file can not be found")
        return -1
    except ValueError:
        print("The file content is not a valid octet decimal number")
        return -1

def get_network_tx_mb(interface):
    try:
        network_info = psutil.net_io_counters(pernic=True)
        if interface in network_info:
            tx_bytes = network_info[interface].bytes_sent
            tx_mb = tx_bytes / (1024 * 1024)
            return tx_mb
        else:
            return None
    except Exception as e:
        print("Error getting network TX bytes:", e)
        return None

def init_4g_tx_mb_record(interface):
    global tx_mb_4g_init
    check_interface_and_pull_up(interface)
    tx_mb = get_network_tx_mb(interface)
    if tx_mb is not None:
        print(f"Total TX bytes on {interface}: {tx_mb:.2f} MB")
    else:
        print(f"Could not retrieve TX bytes for {interface}.")
    tx_mb_4g_init = tx_mb

def update_4g_tx_mb_report(interface):
    global tx_mb_4g_last_report
    global tx_mb_4g_init
    print("[net_switcher] info, update_4g_tx_mb_report")
    tx_mb = get_network_tx_mb(interface)
    if tx_mb is not None:
        print(f"Total TX bytes on {interface}: {tx_mb:.2f} MB")
    else:
        print(f"Could not retrieve TX bytes for {interface}.")

    # check report
    tx_gap_mb = tx_mb - tx_mb_4g_init
    unreported_mb = tx_gap_mb - tx_mb_4g_last_report
    print("tx_mb:", tx_mb,
          ", tx_mb_4g_init:", tx_mb_4g_init,
          ", tx_gap_mb:", tx_gap_mb,
          ", tx_mb_4g_last_report:", tx_mb_4g_last_report,
          ", unreported_mb:", unreported_mb)
    if (unreported_mb > tx_mb_4g_report_quantity and
        unreported_mb < (tx_mb_4g_report_quantity * 5.0)):
        # do 4g traffic report
        print("[net_switcher] info, do 4g traffic report")
        traffic_report_to_json = {"report_quantity": tx_mb_4g_report_quantity}
        print("[net switcher] traffic_report_to_json=", traffic_report_to_json)
        # traffic_report_writer.write(String_(data=json.dumps(traffic_report_to_json)))

        tx_mb_4g_last_report = tx_mb_4g_last_report + tx_mb_4g_report_quantity
    elif unreported_mb > tx_mb_4g_report_quantity * 5:
        print("[net_switcher] warning, unreported mb too much!")


def write_dds_message_on_network_status():
    print("[dds write thread] init")
    global network_status
    global domainParticipant

    domainParticipant = DomainParticipant(0)
    # traffic_report_writer = DataWriter(domainParticipant, Topic(domainParticipant, "rt/4g_traffic_report", String_))
    net_status_writer = DataWriter(domainParticipant, Topic(domainParticipant, "rt/public_network_status", String_))

    time.sleep(0.5)

    while True:
        print("[dds write thread] while loop +1")
        with network_status_write_cd:
            network_status_write_cd.wait()

            # send to dds
            network_status_to_json = {"network_status": f"{network_status}"}
            print("[dds write thread] dds msg =", network_status_to_json)
            net_status_writer.write(String_(data=json.dumps(network_status_to_json)))


# main coroutine
async def main():
    global domainParticipant

    # start thread to write dds message on network status
    write_net_status_thread = \
        threading.Thread(target=write_dds_message_on_network_status, daemon=True)
    write_net_status_thread.start()

    await asyncio.sleep(1)

    # start fourg_agent thread
    fourg_agent_thread = \
        threading.Thread(target=thread_fourg_agent, args=(domainParticipant,), daemon=True)
    fourg_agent_thread.start()

    global network_status
    global network_status_before

    # prevents network components from being initialized when the Raspberry PI
    # is powered on.
    await asyncio.sleep(20)

    # if Go2 version is AIR, program then goes into permanent sleep.
    if is_air_version() == 1:
        print("inter air versoin")
        while True:
            print("\n\n[net switcher] newloop, air version")
            network_status = NetworkStatus.ON_WIFI_CONNECTED
            # send network status to dds
            with network_status_write_cd:
                network_status_write_cd.notify()

            await asyncio.sleep(10)
        return

    log_network_status()
    update_4g_target_address()

    init_4g_tx_mb_record(public_network_4g_interface)

    while True:
        print("\n\n[net switcher] newloop, time=", datetime.now())
        log_network_status()

        check_interface_and_pull_up("wlan0")
        # check_interface_and_pull_up("wwan0")

        fourG_switch = read_fourG_switch()

        if is_public_network_reachable(public_network_wifi_interface, target_address_wifi):
            print("[net switcher] wifi(wlan0) public network reachable")
            if (network_status != NetworkStatus.ON_WIFI_CONNECTED):
                # shut down 4g
                try_times = 5
                while (try_times > 0):
                    try_times = try_times - 1
                    code = run_command(module_4gcm_stop_cmd)
                    if code == 1:
                        break
                run_command(pull_wwan0_interface_down_cmd)

            network_status = NetworkStatus.ON_WIFI_CONNECTED
        else:
            print("[net switcher] wifi(wlan0) public network NOT reachable")
            if fourG_switch == FourGSwitchStatus.ON:
                if (network_status != NetworkStatus.ON_4G_CONNECTED):
                    # start 4gcm
                    try_times = 5
                    while (try_times > 0):
                        try_times = try_times - 1
                        code = run_command(module_4gcm_stop_cmd)
                        if code == 1:
                            break
                    check_interface_and_pull_up("wwan0")

                    try_times = 5
                    while (try_times > 0):
                        try_times = try_times - 1
                        code = run_command(module_4gcm_start_cmd)
                        if code == 0:
                            break
                    wait_wwan0_get_valid_ip_address()

                if is_network_reachable(public_network_4g_interface, target_address_4g):
                    network_status = NetworkStatus.ON_4G_CONNECTED
                else:
                    network_status = NetworkStatus.DISCONNECTED
            elif fourG_switch == FourGSwitchStatus.OFF:
                # shut down 4g
                try_times = 5
                while (try_times > 0):
                    try_times = try_times - 1
                    code = run_command(module_4gcm_stop_cmd)
                    if code == 1:
                        break
                run_command(pull_wwan0_interface_down_cmd)
                network_status = NetworkStatus.DISCONNECTED
            else:
                print("[net switcher] invalid fourG_switch enum")

        if (network_status != network_status_before):
            log_network_status()
        network_status_before = network_status

        # send network status to dds
        with network_status_write_cd:
            network_status_write_cd.notify()

        if network_status == NetworkStatus.ON_4G_CONNECTED:
            update_4g_tx_mb_report(public_network_4g_interface)

        await asyncio.sleep(10)

# entry point
asyncio.run(main())
