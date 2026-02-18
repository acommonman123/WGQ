import socket
import struct
#import binascii
import subprocess
import re
import sys
import os
import multiprocessing
import heapq
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

congestion_nodes = ['WALKERdgm-3101', 'WALKERdgm-3201', 'WALKERdgm-4001', 'WALKERdgm-3103', 'WALKERdgm-3104', 'WALKERdgm-3111', 'WALKERdgm-3203', 'WALKERdgm-3204', 'WALKERdgm-3211', 'WALKERdgm-4003', 'WALKERdgm-4004', 'WALKERdgm-4011']

def create_raw_socket():
    try:
        # 创建IPv6原始套接字
        raw_socket = socket.socket(socket.AF_INET6, socket.SOCK_RAW, socket.IPPROTO_IPV6)
        return raw_socket
    except socket.error as e:
        #print(f"Error creating raw socket: {e}")
        return None

def create_ipv6_header(src_ip, dst_ip, payload_len, hop_limit):
    src_ip_packed = socket.inet_pton(socket.AF_INET6, src_ip)
    dst_ip_packed = socket.inet_pton(socket.AF_INET6, dst_ip)
    ipv6_header = struct.pack('!4sHsB16s16s', b'\x60\x00\x00\x00',payload_len, b'\x3b', hop_limit, src_ip_packed,dst_ip_packed)
    return ipv6_header

def send_data(sock, dest_ip, src_ip, data_length):
    delay = 0
    if NODE_ID in congestion_nodes:
        time.sleep(0.9)
        delay += 0.9
    else:
        time.sleep(0.5)
        delay += 0.5
    data = b"data " + dest_ip.encode('ascii') + b" " + data_length.encode('ascii') + b" " + str(delay).encode('ascii')
    data_len = len(data)
    nexthop_ip = get_nexthop_ip(dest_ip.split('::')[0] + '::/64')
    if nexthop_ip == "neighbor":
        print("dest is neighbor")
        nexthop_ip = dest_ip
    elif nexthop_ip is None:
        print("no route to dest")
        return
    header = create_ipv6_header(src_ip, nexthop_ip, data_len, 64)
    packet = header + data
    while True:
        try:
            sock.sendto(packet, (nexthop_ip, 0))
            print(f"data send to {nexthop_ip}")
            break
        except socket.error as e:
            print(f"Error sending in_cluster packet: {e}")
            time.sleep(0.2)
    with open('/files/total_pkts.txt', 'a') as f:
        f.write(f"sent data to {dest_ip}\n")

def get_nexthop_ip(dest_ip):
    # 使用 subprocess 调用系统命令
    process = subprocess.Popen("ip -6 route",universal_newlines=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, errs = process.communicate()   
    # 获取路由表的输出，并按行分割
    routes = out.split('\n')
    pattern1 = dest_ip + r" via ([\da-f:]+) dev"
    match1 = re.search(pattern1, out)
    if match1:
        #print("下一跳IP:", match.group(1))
        nexthop_ip = match1.group(1)
        return nexthop_ip
    elif dest_ip in out:
        #print("下一跳IP:", match.group(1))
        return "neighbor"
    else:
        return None
    
if __name__ == "__main__":
    ip_addr_output = subprocess.check_output(['ip', '-6', 'addr'], text=True)
    ip_addresses = re.findall(r'inet6\s+([0-9a-fA-F:]+)(?:/\d+)?', ip_addr_output)
    ip_addresses = [ip for ip in ip_addresses if ip.startswith(('fd00:'))]  # 过滤掉2001和fe80开头的地址
    src_ip = ip_addresses[0] # 源IPv6地址
    dest_ip = sys.argv[1]
    NODE_ID = sys.argv[2]
    raw_socket = create_raw_socket()
    if raw_socket is None:
        print("Failed to create raw socket. Exiting.")
        sys.exit(1)
    while True:
        threading.Thread(target=send_data, args=(raw_socket, dest_ip, src_ip, '100')).start()
        #send_data(raw_socket, dest_ip, src_ip, '100')
        time.sleep(2.5)