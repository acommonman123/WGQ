import socket
import struct
import binascii
import subprocess
import re
import sys
import os
import multiprocessing
import heapq
import time
import threading


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

def get_cluster_heads():
    orbit = 10
    sat = 2
    cluster_heads = []
    while orbit < 20:
        while sat < 16:
            if sat < 10:
                cluster_head = "WALKERdyd-" + str(orbit) + "0" + str(sat)
            else:
                cluster_head = "WALKERdyd-" + str(orbit) + str(sat)
            cluster_heads.append(cluster_head)
            sat = sat + 3
        sat = 2
        orbit = orbit + 3
    return cluster_heads
    

if __name__ == "__main__":
    print(get_cluster_heads())
    print(len(get_cluster_heads()))
    