import socket
import struct
import binascii
import subprocess
import re
import time
import sys

def create_ipv6_header(src_ip, dst_ip, payload_len, hop_limit):
    src_ip_packed = socket.inet_pton(socket.AF_INET6, src_ip)
    dst_ip_packed = socket.inet_pton(socket.AF_INET6, dst_ip)
    ipv6_header = struct.pack('!4sHsB16s16s', b'\x60\x00\x00\x00',payload_len, b'\x3b', hop_limit, src_ip_packed,dst_ip_packed)
    return ipv6_header

def create_raw_socket():
    try:
        raw_socket = socket.socket(socket.AF_INET6, socket.SOCK_RAW, socket.IPPROTO_IPV6)
        raw_socket.setsockopt(socket.IPPROTO_IPV6, socket.IP_HDRINCL, 1)
        return raw_socket
    except socket.error as e:
        print(f"Error creating raw socket: {e}")
        return None

def send_ipv6_packet(raw_socket, src_ip, dst_ip, payload, next_header=socket.IPPROTO_UDP, hop_limit=64):
    payload_len = len(payload)
    ipv6_header = create_ipv6_header(src_ip, dst_ip, payload_len, next_header, hop_limit)
    packet = ipv6_header + payload

    try:
        raw_socket.sendto(packet, (dst_ip, 0))
        print(f"IPv6 packet sent to {dst_ip}")
    except socket.error as e:
        print(f"Error sending packet: {e}")

def get_neighbor_ips():
    neighbor_ip_list = []
    ip_addr_output = subprocess.check_output(['ip', '-6', 'addr'], text=True)
    ip_addresses = re.findall(r'inet6\s+([0-9a-fA-F:]+)(?:/\d+)?', ip_addr_output)
    print(ip_addresses)
    for ip in ip_addresses:
        ip_parts = ip.split(':')
        if ip_parts[0] == '2001':
            continue
        if ip_parts[-1] == '10':
            ip_parts[-1] = '20'
            neighbor_ip = ':'.join(ip_parts)
            neighbor_ip_list.append(neighbor_ip)
        elif ip_parts[-1] == '20':
            ip_parts[-1] = '10'
            neighbor_ip = ':'.join(ip_parts)
            neighbor_ip_list.append(neighbor_ip)
    print(neighbor_ip_list)
    return neighbor_ip_list

def incluster_inform(sock, neighbor_ip_list, source_ip):
    hop_limit = '2'
    data = b"incluster_inform " + sys.argv[1].encode('ascii') + b" " + sys.argv[2].encode('ascii') + b" " + source_ip.encode('ascii') + b" " + hop_limit.encode('ascii') +  b" "#head_inform <node_id> <cluster_id> <head_ip> <hop_limit>
    data_len = len(data)
    # 发送数据包
    for dest_ip in neighbor_ip_list:
        # 创建 IP 头部
        ip_header = create_ipv6_header(source_ip, dest_ip, data_len, hop_limit=64)

        # 构造完整的数据包
        packet = ip_header + data
        sock.sendto(packet, (dest_ip, 0))
        #print("incluster_inform sent successfully")

def main():
    ip_addr_output = subprocess.check_output(['ip', '-6', 'addr'], text=True)
    ip_addresses = re.findall(r'inet6\s+([0-9a-fA-F:]+)(?:/\d+)?', ip_addr_output)
    ip_addresses = [ip for ip in ip_addresses if not ip.startswith(('2001:db8', 'fe80::'))]  # 过滤掉特定的IPv6地址
    src_ip = ip_addresses[1] # 源IPv6地址
    neighbor_ip_list = get_neighbor_ips()
    raw_socket = create_raw_socket()
    if raw_socket is None:
        return
    while True:
        incluster_inform(raw_socket, neighbor_ip_list, src_ip)
        #send_ipv6_packet(raw_socket, src_ip, dst_ip, payload)
        time.sleep(5)


if __name__ == "__main__":
    main()
