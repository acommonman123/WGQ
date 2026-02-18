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
    
import threading, time

class SilentCountDown:
    def __init__(self, seconds: float):
        self._seconds = seconds
        self._cv = threading.Condition()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while True:
            with self._cv:
                # 1. 真正睡眠；返回值 True=被提前notify，False=自然超时
                reset = self._cv.wait(timeout=self._seconds)
            # 2. 只有“自然超时”才触发事件 A
            if not reset:
                self._on_finish()

    def reset(self):
        """事件 B 调用：打断当前睡眠，重新开始倒计时"""
        with self._cv:
            self._cv.notify()

    def _on_finish(self):
        print("🔔 倒计时结束，执行事件 A")
        event_a()

# ------------------ 演示 ------------------
def event_a():
    print(">>> 真正的 A 动作在这里发生 <<<")

def demo_event_b(cd: SilentCountDown):
    import random
    while True:
        time.sleep(6)
        print("🔄 事件 B 触发，倒计时重置")
        cd.reset()



def main():
    print('pid=', os.getpid(), '开始干活')
    ans = input('想重启吗？y/n: ')
    if ans.lower() == 'y':
        # 用当前解释器、当前脚本路径，把当前进程“替掉”
        subprocess.Popen([sys.executable] + sys.argv)
    print('正常结束，不会走到这里')

if __name__ == '__main__':
    print('程序开始运行')
    main()