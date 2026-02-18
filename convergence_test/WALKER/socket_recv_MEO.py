import socket
import struct
import binascii
import subprocess
import re
import sys
import os
import multiprocessing
import time



def create_raw_socket():
    try:
        # 创建IPv6原始套接字
        raw_socket = socket.socket(socket.AF_INET6, socket.SOCK_RAW, socket.IPPROTO_IPV6)
        return raw_socket
    except socket.error as e:
        print(f"Error creating raw socket: {e}")
        return None

def get_neighbor_ips():
    neighbor_ip_list = []
    ip_addr_output = subprocess.check_output(['ip', '-6', 'addr'], text=True)
    ip_addresses = re.findall(r'inet6\s+([0-9a-fA-F:]+)(?:/\d+)?', ip_addr_output)
    #print(ip_addresses)
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
    #print(neighbor_ip_list)
    return neighbor_ip_list

def create_ipv6_header(src_ip, dst_ip, payload_len, hop_limit):
    src_ip_packed = socket.inet_pton(socket.AF_INET6, src_ip)
    dst_ip_packed = socket.inet_pton(socket.AF_INET6, dst_ip)
    ipv6_header = struct.pack('!4sHsB16s16s', b'\x60\x00\x00\x00',payload_len, b'\x3b', hop_limit, src_ip_packed,dst_ip_packed)
    return ipv6_header

def send_in_cluster(sock, node_id, src_ip, head_id, dest_ip, route_to_head):
    data = b"in_cluster " + node_id.encode('ascii') + b" " + head_id.encode('ascii') + b" " + route_to_head.encode('ascii') # in_cluster <node_id> <head_id> 
    data_len = len(data)
    header = create_ipv6_header(src_ip, dest_ip, data_len, 64)
    packet = header + data
    try:
        sock.sendto(packet, (dest_ip, 0))
        print(f"in_cluster sent to {dest_ip}")
    except socket.error as e:
        print(f"Error sending packet: {e}")

def forward_incluster_inform(sock, neighbor_ip_list, source_ip, head_id, cluster_id, head_ip, ttl, route_to_head):
    data = b"incluster_inform " + head_id.encode('ascii') + b" " + cluster_id.encode('ascii') + b" " + head_ip.encode('ascii') + b" " + ttl.encode('ascii')  + b" " + route_to_head.encode('ascii')#incluster_inform <node_id> <cluster_id> <head_ip> <hop_limit>
    data_len = len(data)
    # 发送数据包
    for dest_ip in neighbor_ip_list:
        # 创建 IP 头部
        header = create_ipv6_header(source_ip, dest_ip, data_len, hop_limit=64)

        # 构造完整的数据包
        packet = header + data
        sock.sendto(packet, (dest_ip, 0))
        print("incluster_inform sent successfully")

def call_hello(node_id, cluster_id):
    os.system('python3 hello.py ' + node_id + ' ' + cluster_id)

def call_incluster_inform(node_id, cluster_id):
    os.system('python3 incluster_inform.py ' + node_id + ' ' + cluster_id)

def new_cluster_neighbor(sock, head_ip, cluster_neighbor_id, src_ip):
    data = b"new_cluster_neighbor " + cluster_neighbor_id.encode('ascii') # new_cluster_neighbor <cluster_neighbor_id>
    data_len = len(data)
    header = create_ipv6_header(src_ip, head_ip, data_len, hop_limit=64)
    packet = header + data
    sock.sendto(packet, (head_ip, 0))
    print(f"New cluster neighbor packet sent to {head_ip}")

def cluster_description(sock, dest_ip, cluster_id, head_id, cluster_member_list, src_ip):
    data = b"cluster_description " + b" " + cluster_id.encode('ascii') + b" " + head_id + b" ".join(cluster_member_list).encode('ascii')                
    data_len = len(data)
    header = create_ipv6_header(src_ip, dest_ip, data_len, hop_limit=64)
    packet = header + data
    sock.sendto(packet, (dest_ip, 0))
    print(f"Cluster description packet sent to {dest_ip}")

def cluster_update(sock, src_ip, cluster_id, neighbor_ip_list, cluster_member_list, ttl, seq):
    global MEO_ip
    cluster_members = " ".join(cluster_member_list)
    data = b"cluster_update" + b" " + cluster_id.encode('ascii') + b" " + ttl.encode('ascii') + b" " + seq.encode('ascii') + b" " + cluster_members.encode('ascii')  # in_cluster_ack <cluster_member_list>
    data_len = len(data)
    # 发送数据包
    for dest_ip in neighbor_ip_list:
        # 创建 IP 头部
        ip_header = create_ipv6_header(src_ip, dest_ip, data_len, hop_limit=64)

        # 构造完整的数据包
        packet = ip_header + data
        sock.sendto(packet, (dest_ip, 0))
        print("cluster_update sent successfully")
    
    # 创建 IP 头部
    ip_header = create_ipv6_header(src_ip, MEO_ip, data_len, hop_limit=64)

    # 构造完整的数据包
    packet = ip_header + data
    sock.sendto(packet, (MEO_ip, 0))
    print("cluster_update sent successfully")

def cluster_neighbor_update(sock, src_ip, cluster_id, cluster_neighbors):
    data = b"cluster_neighbor_update " + cluster_id.encode('ascii') + b" " + cluster_neighbors.encode('ascii')  # cluster_neighbor_update <cluster_id> <neighbor_list>
    data_len = len(data)
    # 创建 IP 头部
    ip_header = create_ipv6_header(src_ip, src_ip, data_len, hop_limit=64)

    # 构造完整的数据包
    packet = ip_header + data
    sock.sendto(packet, (MEO_ip, 0))
    #print("cluster_neighbor_update sent successfully")

def update_cluster_neighbor(payload_parts, sock, src_ip, lasthop):
    received_cluster_id = payload_parts[1]
    received_cluster_neighbor = payload_parts[2]
    seq = payload_parts[3]
        
    print('received_cluster_id: ', received_cluster_id)
    print('received_cluster_neighbor: ', received_cluster_neighbor)
    cluster_neighbor_update_MEO(sock, src_ip, received_cluster_id, received_cluster_neighbor)
    forward_cluster_neighbor_update(sock, src_ip, " ".join(payload_parts).encode('ascii'), neighbor_ip_list, lasthop)
    
    with open("output.txt", "a") as file:
        result = 'received_cluster_id: ' + str(received_cluster_id) + ', received_cluster_neighbor: ' + str(received_cluster_neighbor)
        file.write(result + '\n')
    

def cluster_neighbor_update_MEO(sock, src_ip, cluster_id, cluster_neighbor):
    global head_ip_list
    for dest_ip in head_ip_list:
        data = b"cluster_neighbor_update " + str(cluster_id).encode('ascii') + b" " + cluster_neighbor.encode('ascii') # cluster_update <cluster_id> <ttl> <seq> <cluster_member_list>
        data_len = len(data)
        # 创建 IP 头部
        ip_header = create_ipv6_header(src_ip, dest_ip, data_len, hop_limit=64)

        # 构造完整的数据包
        packet = ip_header + data
        while True:
            try:
                sock.sendto(packet, (dest_ip, 0))
                break
            except socket.error as e:
                print(f"Error sending cluster_neighbor_update_MEO packet: {e}")
                with open('error_log.txt', 'a') as log_file:
                    log_file.write(f"Error sending packet to {dest_ip}: {e}\n")
                time.sleep(0.2)
        #print("cluster_neighbor_update sent successfully")

def forward_cluster_neighbor_update(sock, src_ip, data, neighbor_ip_list, lasthop):
    for dest_ip in neighbor_ip_list:
        if dest_ip == lasthop:
            continue
        data_len = len(data)
        # 创建 IP 头部
        ip_header = create_ipv6_header(src_ip, dest_ip, data_len, hop_limit=64)

        # 构造完整的数据包
        packet = ip_header + data
        while True:
            try:
                sock.sendto(packet, (dest_ip, 0))
                print("forward_cluster_neighbor_update sent successfully")
                break
            except socket.error as e:
                print(f'{NODE_ID} Error forwarding cluster_neighbor_update:{e}')
                time.sleep(0.2)

def cluster_update_MEO(sock, src_ip, received_member_list, cluster_id_received, seq, neighbor_ip_list, lasthop):
    members = " ".join(received_member_list)
    data = b"cluster_update " + str(cluster_id_received).encode('ascii') + b" 0 " + seq.encode('ascii') + b" " + members.encode('ascii')  # cluster_update <cluster_id> <ttl> <seq> <cluster_member_list>
    for dest_ip in head_ip_list:
        data_len = len(data)
        # 创建 IP 头部
        ip_header = create_ipv6_header(src_ip, dest_ip, data_len, hop_limit=64)
        
        # 构造完整的数据包
        packet = ip_header + data
        while True:
            try:
                sock.sendto(packet, (dest_ip, 0))
                print(f"{NODE_ID} send cluster_update to LEO")
                break
            except socket.error as e:
                print(f"Error sending cluster_update_MEO packet: {e}")
                with open('error_log.txt', 'a') as log_file:
                    log_file.write(f"Error sending packet to {dest_ip}: {e}\n")
                time.sleep(0.2)
    forward_cluster_update(sock, src_ip, data, neighbor_ip_list, lasthop)

def forward_cluster_update(sock, src_ip, data, neighbor_ip_list, lasthop):
    for dest_ip in neighbor_ip_list:
        if dest_ip == lasthop:
            print(f"{NODE_ID} lasthop == desthop, jumping forwarding to {dest_ip}")
            continue
        data_len = len(data)
        # 创建 IP 头部
        ip_header = create_ipv6_header(src_ip, dest_ip, data_len, hop_limit=64)

        # 构造完整的数据包
        packet = ip_header + data
        while True:
            try:
                sock.sendto(packet, (dest_ip, 0))
                print("forward_cluster_update sent successfully")
                break
            except socket.error as e:
                print(f'{NODE_ID} error forwarding cluster_update: {e}')
                time.sleep(0.2)


def receive_ipv6_packet(raw_socket):
    global neighbor_list
    global status
    global member_list
    global cluster_neighbor_list
    global cluster_list
    global cluster_id_list
    global head_ip_list
    global HEAD_ID
    global HEAD_IP
    global NODE_ID
    global CLUSTER_ID
    global neighbor_ip_list
    neighbor_cluster_id = ''

    ip_addr_output = subprocess.check_output(['ip', '-6', 'addr'], text=True)
    ip_addresses = re.findall(r'inet6\s+([0-9a-fA-F:]+)(?:/\d+)?', ip_addr_output)
    ip_addresses = [ip for ip in ip_addresses if not ip.startswith(('2001:','fe80::'))]  # 过滤掉2001和fe80开头的地址
    src_ip = ip_addresses[0] # 源IPv6地址
    try:
        while True:
            packet, addr = raw_socket.recvfrom(65535)  # IPv6 MTU
            print("received_packet")
            print(f"Received packet from {addr}")
            # 解析IPv6头
            ipv6_header = packet[:40]
            payload = packet[40:]
            print(f"IPv6 Header: {ipv6_header}")
            print(f"Payload: {payload.decode('ascii')}")
            payload_parts = payload.decode('ascii').split(" ")  
            #接收到hello包
            if payload_parts[0] == "hello":
                neighbor_id = payload_parts[1]
                neighbor = (neighbor_id, addr[0])
                if neighbor not in neighbor_list:
                    neighbor_list.append(neighbor)
                print('neighbor_list: ', neighbor_list)
                neighbor_cluster_id = payload_parts[2]
                #如果是簇边缘节点接收到临簇的包, 告知簇首邻簇信息
                if neighbor_cluster_id != CLUSTER_ID and status == "MEMBER" and neighbor_cluster_id not in cluster_neighbor_list:
                    print('neighbor_cluster_id: ', neighbor_cluster_id)
                    new_cluster_neighbor(raw_socket, HEAD_IP, neighbor_cluster_id, src_ip)
                    cluster_neighbor_list.append(neighbor_cluster_id)
                    print('cluster_neighbor_list: ', cluster_neighbor_list)
        


            #MEO接收到簇邻居信息
            if payload_parts[0] == "cluster_neighbor_update":
                lasthop = addr[0]
                received_cluster_id = payload_parts[1]
                received_cluster_neighbor = payload_parts[2]
                seq = payload_parts[3]
                if received_cluster_id not in cluster_neighbor_update_seq.keys():
                    cluster_neighbor_update_seq[received_cluster_id] = 0
                if int(seq) > int(cluster_neighbor_update_seq[received_cluster_id]):
                    cluster_neighbor_update_seq[received_cluster_id] = int(seq)
                    process = multiprocessing.Process(target=update_cluster_neighbor, args=(payload_parts, raw_socket, src_ip, lasthop))
                    process.start()

                
            #接收到簇首通告
            if payload_parts[0] == 'head_inform':
                status = 'HEAD'
                HEAD_ID = NODE_ID
                HEAD_IP = src_ip
                CLUSTER_ID = payload_parts[1]
                incluster_inform_process = multiprocessing.Process(target=call_incluster_inform, args=(NODE_ID, CLUSTER_ID))
                incluster_inform_process.start()
                hello_process = multiprocessing.Process(target=call_hello, args=(NODE_ID, CLUSTER_ID))
                hello_process.start()

            #接收到簇更新消息
            if payload_parts[0] == "cluster_update":
                cluster_id_received = payload_parts[1]
                print(f'{NODE_ID} receive cluster_id_received: ', cluster_id_received)
                #print('cluster_id: ', CLUSTER_ID)
                ttl = payload_parts[2]
                seq = payload_parts[3]
                received_member_list = payload_parts[4:]
                

                    
                #MEO卫星接收到簇更新信息，将其转发到其他簇首
                if status == 'MEO':
                    if cluster_id_received not in cluster_update_seq.keys():
                        cluster_update_seq[cluster_id_received] = 0
                    if int(seq) > cluster_update_seq[cluster_id_received]:
                        cluster_update_seq[cluster_id_received] = int(seq)
                        process = multiprocessing.Process(target=cluster_update_MEO, args=(raw_socket, src_ip, received_member_list, cluster_id_received, seq, neighbor_ip_list, addr[0]))
                        process.start()
                        #print("cluster_update sent successfully")



    except KeyboardInterrupt:
        print("Stopped receiving packets.")
    except socket.error as e:
        print(f"Error receiving packet: {e}")

def main():
    raw_socket = create_raw_socket()
    if raw_socket is None:
        return
    print("Listening for IPv6 packets...")
    receive_ipv6_packet(raw_socket)

    raw_socket.close()

if __name__ == "__main__":
    manager = multiprocessing.Manager()
    lock = multiprocessing.Lock()
    NODE_ID = sys.argv[1]
    HEAD_IP = ''
    HEAD_ID = ''
    status = "MEO"
    CLUSTER_ID = ''
    neighbor_list = []
    member_list = []
    cluster_neighbor_list = []
    cluster_neighbor_description = {}
    head_ip_list = sys.argv[2:]  # 从命令行参数获取簇首IP列表
    cluster_id_list = []
    cluster_list = []
    ip_addr_output = subprocess.check_output(['ip', '-6', 'addr'], text=True)
    ip_addresses = re.findall(r'inet6\s+([0-9a-fA-F:]+)(?:/\d+)?', ip_addr_output)
    #ip_addresses = [ip for ip in ip_addresses if not ip.startswith(('2001:db8', 'fe80::'))]  # 过滤掉特定的IPv6地址
    MEO_ip = ip_addresses[1] # 源IPv6地址
    neighbor_ip_list = get_neighbor_ips()
    cluster_neighbor_update_seq = manager.dict()
    cluster_update_seq = manager.dict()

    main()

