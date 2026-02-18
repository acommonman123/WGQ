from email.contentmanager import raw_data_manager
from enum import member
import socket
import struct
import binascii
import subprocess
import re
import sys
import os
import multiprocessing
import time
import threading
import heapq

def create_raw_socket():
    try:
        # 创建IPv6原始套接字
        raw_socket = socket.socket(socket.AF_INET6, socket.SOCK_RAW, socket.IPPROTO_IPV6)
        return raw_socket
    except socket.error as e:
        print(f"Error creating raw socket: {e}")
        return None

'''def get_neighbor_ips():
    neighbor_ip_list = []
    ip_addr_output = subprocess.check_output(['ip', '-6', 'addr'], text=True)
    ip_addresses = re.findall(r'inet6\s+([0-9a-fA-F:]+)(?:/\d+)?', ip_addr_output)
    print(ip_addresses)
    for ip in ip_addresses:
        ip_parts = ip.split(':')
        if ip_parts[0] == '2001':
            continue
        if ip_parts[-1] == '2':
            ip_parts[-1] = '3'
            neighbor_ip = ':'.join(ip_parts)
            neighbor_ip_list.append(neighbor_ip)
        elif ip_parts[-1] == '3':
            ip_parts[-1] = '2'
            neighbor_ip = ':'.join(ip_parts)
            neighbor_ip_list.append(neighbor_ip)
    print(neighbor_ip_list)
    return neighbor_ip_list'''

def split_list(lst, chunk_size):
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

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
        while True:
            try:
                sock.sendto(packet, (dest_ip, 0))
                print("incluster_inform sent successfully")
                break
            except Exception as e:
                print(f"{NODE_ID} error forwarding incluster_inform to {dest_ip}")
                time.sleep(0.1)

def call_hello(node_id, cluster_id):
    os.system('python3 hello.py ' + node_id + ' ' + cluster_id)

def send_incluster_inform(sock, src_ip, node_id, cluster_id):
    hop_limit = '2'
    data = b"incluster_inform " + node_id.encode('ascii') + b" " + cluster_id.encode('ascii') + b" " + src_ip.encode('ascii') + b" " + hop_limit.encode('ascii')#head_inform <node_id> <cluster_id> <head_ip> <hop_limit>
    data_len = len(data)
    local_member_ip_dict = {k: member_ip_dict[k] for k in member_ip_dict.keys()}
    for member_id in local_member_ip_dict.keys():
        member_ip = local_member_ip_dict[member_id]
        #print("Sending incluster_inform to ", member_ip)
        # 创建 IP 头部
        header = create_ipv6_header(src_ip, member_ip, data_len, hop_limit=64)

        # 构造完整的数据包
        packet = header + data
        while True:
            try:
                sock.sendto(packet, (member_ip, 0))
                print(f"incluster_inform sent to {member_ip}")
                break
            except Exception as e:
                print(f"{NODE_ID} error sending incluster_inform to {member_id}")
                time.sleep(0.1)
    


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

def cluster_neighbor_update(sock, src_ip, cluster_id, cluster_neighbors):
    data = b"cluster_neighbor_update " + cluster_id.encode('ascii') + b" " + cluster_neighbors.encode('ascii')  # cluster_neighbor_update <cluster_id> <neighbor_list>
    data_len = len(data)
    # 创建 IP 头部
    ip_header = create_ipv6_header(src_ip, src_ip, data_len, hop_limit=64)

    # 构造完整的数据包
    packet = ip_header + data
    sock.sendto(packet, (MEO_ip, 0))
    #print("cluster_neighbor_update sent successfully")

def update_cluster_neighbor(payload_parts, sock, src_ip):
    received_cluster_id = payload_parts[1]
    received_cluster_neighbor = payload_parts[2]
    print('received_cluster_id: ', received_cluster_id)
    print('received_cluster_neighbor: ', received_cluster_neighbor)
    cluster_neighbor_update_MEO(sock, src_ip, received_cluster_id, received_cluster_neighbor)
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
                time.sleep(0.1)
        #print("cluster_neighbor_update sent successfully")

def cluster_update_MEO(sock, src_ip, received_member_list, cluster_id_received, seq):
    for dest_ip in head_ip_list:
        members = " ".join(received_member_list)
        data = b"cluster_update " + str(cluster_id_received).encode('ascii') + b" 0 " + seq.encode('ascii') + b" " + members.encode('ascii')  # cluster_update <cluster_id> <ttl> <seq> <cluster_member_list>
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
                print(f"Error sending cluster_update_MEO packet: {e}")
                with open('error_log.txt', 'a') as log_file:
                    log_file.write(f"Error sending packet to {dest_ip}: {e}\n")
                time.sleep(0.1)

def cluster_update(sock, src_ip, member_id, neighbor_ip_list, cluster_member_ips, seq):
    for dest_ip in neighbor_ip_list:
        print(NODE_ID, ' sending cluster_update to ', dest_ip)
        member_ips = " ".join(cluster_member_ips)
        data = b"cluster_update " + str(member_id).encode('ascii') + b" " + seq.encode('ascii') + b" " + member_ips.encode('ascii')  # cluster_update <cluster_id> <ttl> <seq> <cluster_member_list>
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
                print(f"Error sending cluster_update packet: {e}")
                with open('error_log.txt', 'a') as log_file:
                    log_file.write(f"Error sending packet to {dest_ip}: {e}\n")
                time.sleep(0.1)

def forward_cluster_update(node_id_received, seq, node_ips, sock, src_ip, lasthop):
    for dest_ip in neighbor_ip_list:
        if dest_ip == lasthop:
            continue
        ips = " ".join(node_ips)
        data = b"cluster_update " + str(node_id_received).encode('ascii') + b" " + seq.encode('ascii') + b" " + ips.encode('ascii')  # cluster_update <cluster_id> <ttl> <seq> <cluster_member_list>
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
                print(f"Error sending cluster_update_MEO packet: {e}")
                with open('error_log.txt', 'a') as log_file:
                    log_file.write(f"Error sending packet to {dest_ip}: {e}\n")
                time.sleep(0.1)

def send_incluster_comfirm(sock, src_ip, head_id, cluster_id, member_id, member_ip):
    data = b"incluster_confirm " + head_id.encode('ascii') + b" " + cluster_id.encode('ascii') + b" " + member_id.encode('ascii')# incluster_confirm <cluster_id> <member_id> <route_to_member>
    print('incluster_comfirm message: ', data.decode('ascii'))
    data_len = len(data)
    # 创建 IP 头部
    ip_header = create_ipv6_header(src_ip, member_ip, data_len, hop_limit=64)
    # 构造完整的数据包
    packet = ip_header + data
    while True:
        try:   
            sock.sendto(packet, (member_ip, 0))
            print(f"incluster_confirm sent to {member_ip}")
            break
        except Exception as e:
            print("Error in send_incluster_comfirm:", NODE_ID)
            print(e)
            print("nexthop ip:", member_ip, "src_ip:", src_ip)
            with open("error_log.txt", "a") as file:
                result = f"Error in send_incluster_comfirm: {NODE_ID}, nexthop: {member_ip}\n"
                file.write(result)
            time.sleep(0.1)

def broadcast_intracluster_graph(sock, src_ip,cluster_id, seq, local_intra_cluster_graph):
    #local_intra_cluster_graph = {k: list(intra_cluster_graph[k]) for k in intra_cluster_graph.keys()}
    topology_str = ""
    for node_id in local_intra_cluster_graph.keys():
        for neighbor_id in list(local_intra_cluster_graph[node_id]):
            topology_str = topology_str + node_id + " " + neighbor_id[0] + " "
    topology_str.strip()
    for dest_ip in neighbor_ip_list:
        data = b"intra_cluster_graph " + cluster_id.encode('ascii') + b" " + seq.encode('ascii') + b" " + topology_str.encode('ascii')
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
                print(f"Error sending node_update packet: {e}")
                with open('error_log.txt', 'a') as log_file:
                    log_file.write(f"Error sending packet to {dest_ip}: {e}\n")
                time.sleep(0.1)

def forward_intracluster_graph(data, sock, src_ip, lasthop):
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
                break
            except socket.error as e:
                print(f"Error sending intra_cluster_graph packet: {e}")
                with open('error_log.txt', 'a') as log_file:
                    log_file.write(f"Error sending packet to {dest_ip}: {e}\n")
                time.sleep(0.1)

def dijkstra(Graph, start, end):
    dist = {node: float('inf') for node in Graph}
    prev = {node: None for node in Graph}
    dist[start] = 0
    path = []
    if end not in list(dist.keys()):
        # 节点不在 dist 中，说明图中结构不一致
        return path, float('inf')
    
    pq = [(0, start)]
    visited = set()

    while pq:
        d, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)

        if u == end:
            break

        if u not in Graph:
            continue
        for v, w in Graph[u]:
            if v not in list(dist.keys()):
                # 节点不在 dist 中，说明图中结构不一致
                continue
            if v not in visited and dist[v] > d + w:
                dist[v] = d + w
                prev[v] = u
                heapq.heappush(pq, (dist[v], v))

    # 回溯路径

    u = end
    if dist[end] == float('inf'):  # 无法到达
        #print(f"{end} 不可达")
        return path, dist[end]

    while u is not None:
        path.append(u)
        u = prev[u]
    path.reverse()
    return path, dist[end]


def generate_routing_database(sock, src_ip, local_global_graph, local_node_ip_dict):
    #global global_graph
    all_nodes = list(local_global_graph.keys())
    for start in member_list:
        routing_message = ""
        start_ip = member_ip_dict[start]
        for end in all_nodes:
            if start == end:
                continue
            if end not in local_node_ip_dict:
                continue
            path, distance = dijkstra(local_global_graph, start, end)
            if distance == float('inf'):
                continue
            #routing_entry = f"{start} {end} {' '.join(path)} {distance}\n"
            nexthop = path[1] 
            end_ip_list = local_node_ip_dict[end]
            for ip in end_ip_list:
                routing_message = routing_message + ip + " " + nexthop + " "
            with open("routing_database.txt", "a") as file:
                result = f"From {start} to {end}, path: {' '.join(path)}, distance: {distance}, nexthop: {nexthop}\n"
                file.write(result)
        routing_update(sock, src_ip, start_ip, routing_message.strip())

def routing_update(sock, src_ip, member_ip, update_message):
    data = b"routing_update" + b" " + update_message.encode('ascii')  # routing_update <update_message>(e.g. <dest_ip> <nexthop_id>)
    data_len = len(data)
    # 创建 IP 头部
    ip_header = create_ipv6_header(src_ip, member_ip, data_len, hop_limit=64)

    # 构造完整的数据包
    packet = ip_header + data
    while True:
        try:
            sock.sendto(packet, (member_ip, 0))
            break
        except socket.error as e:
            print(f"{NODE_ID} Error sending routing_update packet to {member_ip}: {e}")
            with open('error_log.txt', 'a') as f:
                result = f"Error sending routing_update packet to {member_ip}: {e}\n"
                f.write(result)
            time.sleep(0.1)
    #print("routing_update sent successfully")

def periodic_update_intracluster_routing(sock, src_ip, interval):
    #global intra_cluster_graph
    #global last_update_intracluster_time
    intra_cluster_graph_seq = 1
    while True:
        try:
            time.sleep(interval)
            #broadcast_intracluster_graph(sock, src_ip, CLUSTER_ID, str(intra_cluster_graph_seq))
            intra_cluster_graph_seq += 1
            local_intra_cluster_graph = {k: list(intra_cluster_graph[k]) for k in intra_cluster_graph.keys()}
            local_global_graph = {k: list(global_graph[k]) for k in global_graph.keys()}
            local_node_ip_dict = {k: list(node_ip_dict[k]) for k in node_ip_dict.keys()}
            thread = threading.Thread(target=broadcast_intracluster_graph, args=(sock, src_ip, CLUSTER_ID, str(intra_cluster_graph_seq), local_intra_cluster_graph))
            thread.start()
            incluster_inform_thread = threading.Thread(target=send_incluster_inform, args=(sock, src_ip, NODE_ID, CLUSTER_ID))
            incluster_inform_thread.start()
            routing_update_thread = threading.Thread(target=generate_routing_database, args=(sock, src_ip, local_global_graph, local_node_ip_dict))
            routing_update_thread.start()
            with open("node_ip.txt", "a") as file:
                file.write(f"Node {NODE_ID} local_node_ip_dict at {time.time()}\n")
                #file.write(f"graph: {local_intra_cluster_graph}\n")
                file.write(f"local_node_ip_dict: {local_node_ip_dict}\n")
            with open('global_graph.txt', 'a') as file:
                file.write(f"Node {NODE_ID} global_graph at {time.time()}\n")
                file.write(f"local_global_graph: {local_global_graph}\n")
        except Exception as e:
            print("Error in periodic_update_intracluster_routing:", NODE_ID)
            print(e)
            print(f"local_intra_cluster_graph: {local_intra_cluster_graph}\n")
            print(f"local_intra_cluster_graph:{local_intra_cluster_graph}\n")
            with open("error_log.txt", "a") as file:
                file.write(f"Error in periodic_update_intracluster_routing: {NODE_ID}\n")
                file.write(str(e) + "\n")

def receive_ipv6_packet(raw_socket):
    global neighbor_list
    global status
    global member_list
    global cluster_neighbor_list
    global cluster_id_list
    global head_ip_list
    global HEAD_ID
    global HEAD_IP
    global NODE_ID
    global CLUSTER_ID
    
    neighbor_cluster_id = ''

    ip_addr_output = subprocess.check_output(['ip', '-6', 'addr'], text=True)
    #ip_addresses = re.findall(r'inet6\s+([0-9a-fA-F:]+)(?:/\d+)?', ip_addr_output)
    #ip_addresses = [ip for ip in ip_addresses if not ip.startswith(('2001:','fe80::'))]  # 过滤掉2001和fe80开头的地址
    try:
        while True:
            packet, addr = raw_socket.recvfrom(65535)  # IPv6 MTU
            print("received_packet")
            print(f"Received packet from {addr}")
            # 解析IPv6头
            ipv6_header = packet[:40]
            payload = packet[40:]
            #print(f"IPv6 Header: {ipv6_header}")
            #print(f"Payload: {payload.decode('ascii')}")
            payload_parts = payload.decode('ascii').split(" ")  

            if payload_parts[0] == "member_ip":
                member_id = payload_parts[1]
                member_ip = addr[0]
                member_ip_dict[member_id] = member_ip
            
            if payload_parts[0] == "in_cluster":
                member_id = payload_parts[1]
                member_ips = payload_parts[2:]
                member_list.append(member_id)
                #node_ip_dict[member_id] = member_ips
                #member_ip_dict[member_id] = addr[0]
                if member_id not in list(node_ip_dict.keys()):
                    node_ip_dict[member_id] = member_ips
                    send_incluster_comfirm(raw_socket, src_ip, NODE_ID, CLUSTER_ID, member_id, addr[0])
                
                if member_id not in list(node_ip_seq.keys()):
                    node_ip_seq[member_id] = 1
                seq = str(node_ip_seq[member_id])
                cluster_update(raw_socket, src_ip, member_id, neighbor_ip_list, member_ips, seq)
                node_ip_seq[member_id] += 1
                
            if payload_parts[0] == "cluster_update":
                print("cluster_update received")
                node_id_received = payload_parts[1]
                seq = payload_parts[2]
                received_member_ips = payload_parts[3:]
                if node_id_received not in list(node_ip_seq.keys()):
                    node_ip_seq[node_id_received] = 0
                if int(seq) > node_ip_seq[node_id_received]:
                    node_ip_seq[node_id_received] = int(seq)
                    forward_cluster_update(node_id_received, seq, received_member_ips, raw_socket, src_ip, addr[0])
                    if node_id_received not in list(node_ip_dict.keys()):
                        node_ip_dict[node_id_received] = manager.list()
                        node_ip_dict[node_id_received].extend(received_member_ips)
                    else:
                        node_ip_dict[node_id_received].extend(received_member_ips)

            if payload_parts[0] == "node_update":
                node_id = payload_parts[1]
                update_type = payload_parts[2]
                neighbor_id = payload_parts[3]
                lasthop = addr[0]
                if update_type == "NEW":
                    if node_id not in list(intra_cluster_graph.keys()):
                        intra_cluster_graph[node_id] = manager.list()
                        global_graph[node_id] = manager.list()
                        intra_cluster_graph[node_id].append((neighbor_id, 10))
                        global_graph[node_id].append((neighbor_id, 10))
                    else:
                        intra_cluster_graph[node_id].append((neighbor_id, 10))
                        global_graph[node_id].append((neighbor_id, 10))

            if payload_parts[0] == "intra_cluster_graph":
                message = " ".join(payload_parts)
                lasthop = addr[0]
                received_cluster_id = payload_parts[1]
                seq = payload_parts[2]
                neighbor_topology = payload_parts[3:]
                if received_cluster_id == CLUSTER_ID:
                    continue
                if received_cluster_id not in list(cluster_graph_seq.keys()):
                    cluster_graph_seq[received_cluster_id] = 0
                if int(seq) > cluster_graph_seq[received_cluster_id]:
                    cluster_graph_seq[received_cluster_id] = int(seq)
                    forward_intracluster_graph(message.encode('ascii'), raw_socket, src_ip, lasthop)
                    topology_message = split_list(neighbor_topology, 2)
                    for item in topology_message:
                        if len(item) != 2:
                            continue
                        node_id = item[0]
                        neighbor_id = item[1]
                        if node_id not in list(global_graph.keys()):
                            global_graph[node_id] = manager.list()
                            if (neighbor_id, 10) not in global_graph[node_id]:
                                global_graph[node_id].append((neighbor_id, 10))
                        else:
                            if (neighbor_id, 10) not in global_graph[node_id]:
                                global_graph[node_id].append((neighbor_id, 10))
                    



    except KeyboardInterrupt:
        print("Stopped receiving packets.")
    except socket.error as e:
        print(f"Error receiving packet: {e}")

def main():
    raw_socket = create_raw_socket()
    if raw_socket is None:
        return
    print("Listening for IPv6 packets...")
    periodic_process = multiprocessing.Process(target=periodic_update_intracluster_routing, args=(raw_socket, src_ip, 10))
    periodic_process.start()
    
    receive_ipv6_packet(raw_socket)
    raw_socket.close()

if __name__ == "__main__":
    NODE_ID = sys.argv[1]
    HEAD_IP = ''
    HEAD_ID = ''
    status = "MEO"
    CLUSTER_ID = sys.argv[2]
    node_ip_seq = {}
    node_ip_seq[CLUSTER_ID] = 1
    cluster_graph_seq = {}
    neighbor_list = []
    cluster_neighbor_list = []
    cluster_neighbor_description = {}
    #head_ip_list = sys.argv[2:]  # 从命令行参数获取簇首IP列表
    cluster_id_list = []
    ip_addr_output = subprocess.check_output(['ip', '-6', 'addr'], text=True)
    ip_addresses = re.findall(r'inet6\s+([0-9a-fA-F:]+)(?:/\d+)?', ip_addr_output)
    manager = multiprocessing.Manager()
    lock = multiprocessing.Lock()
    intra_cluster_graph = manager.dict()   #簇内拓扑图，形式为{node1:[(neighbor1, weight1), (neighbor2, weight2)]}
    global_graph = manager.dict()          #全局拓扑图，形式为{node1:[(neighbor1, weight1), (neighbor2, weight2)]}
    member_list = manager.list()        #成员列表，e.g. ["test1", "test2"]
    #member_ip_list = manager.dict()    #成员IP列表，由簇首维护，e.g. {'test1': '2001:db8:1::101', 'test2': '2001:db8:1::102'}
    node_ip_dict = manager.dict()
    member_bridge_ip_list = manager.list()  
    #ip_addresses = [ip for ip in ip_addresses if not ip.startswith(('2001:db8', 'fe80::'))]  # 过滤掉特定的IPv6地址
    MEO_ip = ip_addresses[1] # 源IPv6地址
    global_ip_addresses = [ip for ip in ip_addresses if ip.startswith(('fd00:'))]
    src_ip = global_ip_addresses[0] # 源IPv6地址
    member_ip_dict = manager.dict()
    neighbor_ip_list = get_neighbor_ips()
    main()
