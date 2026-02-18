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

def split_list(lst, chunk_size):
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def create_ipv6_header(src_ip, dst_ip, payload_len, hop_limit):
    src_ip_packed = socket.inet_pton(socket.AF_INET6, src_ip)
    dst_ip_packed = socket.inet_pton(socket.AF_INET6, dst_ip)
    ipv6_header = struct.pack('!4sHsB16s16s', b'\x60\x00\x00\x00',payload_len, b'\x3b', hop_limit, src_ip_packed,dst_ip_packed)
    return ipv6_header

def send_in_cluster(sock, node_id, src_ip, dest_ip, local_ips):
    data = b"in_cluster " + node_id.encode('ascii') + b" " +  local_ips.encode('ascii') # in_cluster <node_id> <head_id> <ip1> <ip2> ...
    data_len = len(data)
    header = create_ipv6_header(src_ip, dest_ip, data_len, 64)
    packet = header + data
    try:
        sock.sendto(packet, (dest_ip, 0))
        print(f"{NODE_ID} in_cluster sent to {dest_ip}")
    except socket.error as e:
        print(f"{NODE_ID} Error sending in_cluster packet: {e}")

def send_member_ip(sock, node_id, src_ip, dest_ip, local_ips):
    data = b"member_ip " + node_id.encode('ascii') + b" " +  local_ips.encode('ascii') # in_cluster <node_id> <head_id> <ip1> <ip2> ...
    data_len = len(data)
    header = create_ipv6_header(src_ip, dest_ip, data_len, 64)
    packet = header + data
    try:
        sock.sendto(packet, (dest_ip, 0))
        print(f"{NODE_ID} member_ip sent to {dest_ip}")
    except socket.error as e:
        print(f"{NODE_ID} Error sending in_cluster packet: {e}")

def forward_incluster_inform(sock, neighbor_ip_list, source_ip, head_id, cluster_id, head_ip, ttl, route_to_head):
    data = b"incluster_inform " + head_id.encode('ascii') + b" " + cluster_id.encode('ascii') + b" " + head_ip.encode('ascii') + b" " + ttl.encode('ascii')  + b" " + route_to_head.encode('ascii')#incluster_inform <node_id> <cluster_id> <head_ip> <hop_limit>
    data_len = len(data)
    # 发送数据包
    for dest_ip in neighbor_ip_list:
        # 创建 IP 头部
        header = create_ipv6_header(source_ip, dest_ip, data_len, hop_limit=64)

        # 构造完整的数据包
        packet = header + data
        try:
            sock.sendto(packet, (dest_ip, 0))
        except socket.error as e:
            print(f"{NODE_ID} Error sending incluster_inform packet to {dest_ip}: {e}")
        #print("incluster_inform sent successfully")

def call_hello(node_id, cluster_id):
    try:
        os.system('python3 hello.py ' + node_id + ' ' + cluster_id)
        print(f"{node_id} call hello , cluster_id: {cluster_id}")
    except Exception as e:
        print(f"{node_id} Error in call_hello:", e)

def call_incluster_inform(node_id, cluster_id):
    os.system('python3 incluster_inform.py ' + node_id + ' ' + cluster_id)

def new_cluster_neighbor(sock, head_ip, cluster_neighbor_id, src_ip, node_id, link_subnet):
    data = b"new_cluster_neighbor " + cluster_neighbor_id.encode('ascii') + b" " + node_id.encode('ascii') + b" " + link_subnet.encode('ascii') # new_cluster_neighbor <cluster_neighbor_id> <node_id>
    data_len = len(data)
    header = create_ipv6_header(src_ip, MEO_ip, data_len, hop_limit=64)
    packet = header + data
    try:
        sock.sendto(packet, (MEO_ip, 0))
    except socket.error as e:
        print(f"{NODE_ID} Error sending new_cluster_neighbor packet to {MEO_ip}: {e}")
        with open('error_log.txt', 'a') as f:
            result = f"Error sending new_cluster_neighbor packet to {MEO_ip}: {e}\n"
            f.write(result)
    #print(f"New cluster neighbor packet sent to {head_ip}")

'''def cluster_description(sock, dest_ip, cluster_id, head_id, cluster_member_list, src_ip):
    data = b"cluster_description " + b" " + cluster_id.encode('ascii') + b" " + head_id + b" ".join(cluster_member_list).encode('ascii')                
    data_len = len(data)
    header = create_ipv6_header(src_ip, dest_ip, data_len, hop_limit=64)
    packet = header + data
    sock.sendto(packet, (dest_ip, 0))
    #print(f"Cluster description packet sent to {dest_ip}")'''

# 簇首发送簇更新信息，发给MEO卫星
def cluster_update_head(sock, src_ip, cluster_id, member_ips, ttl, seq):
    global MEO_ip
    '''cluster_members = list(cluster_member_ip_list.values())
    member_ips = ""
    for item in cluster_members:
        for ip in item:
            member_ips += ip + " "
    member_ips = member_ips.strip()'''
    data = b"cluster_update" + b" " + cluster_id.encode('ascii') + b" " + ttl.encode('ascii') + b" " + seq.encode('ascii') + b" " + member_ips.encode('ascii')  # cluster_update <cluster_member_list>
    data_len = len(data)
    # 创建 IP 头部
    ip_header = create_ipv6_header(src_ip, MEO_ip, data_len, hop_limit=64)

    # 构造完整的数据包
    packet = ip_header + data
    while True:
        try:
            sock.sendto(packet, (MEO_ip, 0))
            break
        except socket.error as e:
            print(f"{NODE_ID} Error sending cluster_update packet to MEO: {e}")
            with open('error_log.txt', 'a') as f:
                result = f"Error sending cluster_update packet to MEO: {e}\n"
                f.write(result)
    #print("cluster_update sent successfully")

def cluster_update_MEO(sock, src_ip, cluster_id, cluster_neighbor):
    for dest_ip in head_ip_list:
        data = b"cluster_neighbor_update " + str(cluster_id).encode('ascii') + b" " + cluster_neighbor.encode('ascii') # cluster_update <cluster_id> <ttl> <seq> <cluster_member_list>
        data_len = len(data)
        # 创建 IP 头部
        ip_header = create_ipv6_header(src_ip, dest_ip, data_len, hop_limit=64)

        # 构造完整的数据包
        packet = ip_header + data
        sock.sendto(packet, (dest_ip, 0))
        #print("cluster_neighbor_update sent successfully")

# 簇内成员发送簇更新信息，发给簇内成员
def cluster_update_member(sock, src_ip, cluster_id, neighbor_ip_list, cluster_member_list, ttl, seq):
    global MEO_ip
    cluster_members = " ".join(cluster_member_list)
    data = b"cluster_update" + b" " + cluster_id.encode('ascii') + b" " + ttl.encode('ascii') + b" " + seq.encode('ascii') + b" " + cluster_members.encode('ascii')  # cluster_update <cluster_member_list>
    data_len = len(data)
    # 发送数据包
    for dest_ip in neighbor_ip_list:
        # 创建 IP 头部
        ip_header = create_ipv6_header(src_ip, dest_ip, data_len, hop_limit=64)

        # 构造完整的数据包
        packet = ip_header + data
        sock.sendto(packet, (dest_ip, 0))
        #print("cluster_update sent successfully")

def cluster_neighbor_update(sock, src_ip, cluster_id, cluster_neighbor):
    global MEO_ip
    data = b"cluster_neighbor_update " + cluster_id.encode('ascii') + b" " + cluster_neighbor.encode('ascii')  # cluster_neighbor_update <cluster_id> <neighbor_list>
    data_len = len(data)
    # 创建 IP 头部
    ip_header = create_ipv6_header(src_ip, MEO_ip, data_len, hop_limit=64)

    # 构造完整的数据包
    packet = ip_header + data
    while True:
        try:
            sock.sendto(packet, (MEO_ip, 0))
            break
        except socket.error as e:
            print(f"{NODE_ID} Error sending cluster_neighbor_update packet to MEO(IP: {MEO_ip}): {e}")
            with open('error_log.txt', 'a') as f:
                result = f"Error sending cluster_neighbor_update packet to MEO: {e}\n"
                f.write(result)
    #print("cluster_neighbor_update sent successfully")

def node_update(sock, src_ip, node_id, update_type, neighbor_id):
    data = b"node_update " + node_id.encode('ascii') + b" " + update_type.encode('ascii') + b" " + neighbor_id.encode('ascii') # Node_status <node_id> NEW/DEL <neighbor_id> <seq>
    data_len = len(data)
    # 创建 IP 头部
    ip_header = create_ipv6_header(src_ip, MEO_ip, data_len, hop_limit=64)

    # 构造完整的数据包
    packet = ip_header + data
    while True:
        try:
            sock.sendto(packet, (MEO_ip, 0))
            break
        except socket.error as e:
            print(f"{NODE_ID} Error sending node_update packet to MEO(IP: {MEO_ip}): {e}")
            with open('error_log.txt', 'a') as f:
                result = f"Error sending node_update packet to MEO: {e}\n"
                f.write(result)
    #print("node_update sent successfully")

# 将路由更新信息发送给成员节点
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
    #print("routing_update sent successfully")

# 将簇内路由更新信息发送给成员节点
def edge_update(sock, src_ip, edge_ip, cluster_neighbor, dest_ips):
    data = b"edge_update" + b" " + cluster_neighbor.encode('ascii') + b" " + dest_ips.encode('ascii')  # edge_update <cluster_neighbor> <dest_ip1> <dest_ip2> ...
    data_len = len(data)
    # 创建 IP 头部
    ip_header = create_ipv6_header(src_ip, edge_ip, data_len, hop_limit=64)

    # 构造完整的数据包
    packet = ip_header + data
    while True:
        try:
            sock.sendto(packet, (edge_ip, 0))
            break
        except socket.error as e:
            print(f"{NODE_ID} Error sending edge_update packet to {edge_ip}: {e}")
            with open('error_log.txt', 'a') as f:
                result = f"Error sending edge_update packet to {edge_ip}: {e}\n"
                f.write(result)
    #print("routing_update sent successfully")

# 将簇间路由更新信息发送给成员节点
def inter_cluster_routing_update(sock, src_ip, edge_id, edge_ip, dest_subnets):
    data = b"inter_cluster_routing_update" + b" " + edge_ip.encode('ascii') + b" " + dest_subnets.encode('ascii')  # inter_cluster_routing_update <edge_ip> <dest_subnet1> <dest_subnet2> ...
    data_len = len(data)
    local_member_ip_list = {key: list(member_ip_list[key]) for key in member_ip_list.keys()}
    for member in member_list:
        with open('send_inter_log.txt', 'a') as f:
            result = f"sending inter_cluster_routing_update to {member}\n" + data.decode('ascii') + '\n'
            f.write(result)
        if member == edge_id or member == NODE_ID:
            continue
        member_ip = local_member_ip_list[member][0]
        # 创建 IP 头部
        ip_header = create_ipv6_header(src_ip, member_ip, data_len, hop_limit=64)
        # 构造完整的数据包
        packet = ip_header + data
        try:
            sock.sendto(packet, (member_ip, 0))
        except socket.error as e:
            print(f"{NODE_ID} Error sending inter_cluster_routing_update packet to {member_ip}: {e}")
            with open('error_log.txt', 'a') as f:
                result = f"Error sending inter_cluster_routing_update packet to {member_ip}: {e}\n"
                f.write(result)

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


def generate_intracluster_routing_table(Graph, sock, src_ip):
    '''global member_ip_list
    global neighbor_list
    global member_list
    global NODE_ID'''
    
    with lock:
        local_member_ip_list = {key: list(member_ip_list[key]) for key in member_ip_list.keys()}
        local_neighbor_list = {key: neighbor_list[key] for key in neighbor_list.keys()}
        local_member_list = list(local_member_ip_list.keys())
    print("graph keys:", list(Graph.keys()))
    print('member_ip_list keys:', list(member_ip_list.keys()))
    # 簇首更新路由表
    for end in list(Graph.keys()):
        if end == NODE_ID or end not in list(member_ip_list.keys()):
            #print(f"Skipping {end}, either it's the current node or not in member_ip_list.")
            continue
        path, cost = dijkstra(Graph, NODE_ID, end)
        if cost == float('inf'):
            #(f"{end} 不可达")
            continue
        print("new route to", end, ":", path, "cost:", cost)
        nexthop = path[1]
        if nexthop not in local_neighbor_list:
            #print(f"Next hop {nexthop} not in neighbor list, skipping route addition.")
            continue
        nexthop_ip = local_neighbor_list[nexthop]
        end_ips = member_ip_list[end]
        for ip in end_ips: 
            if ip in list(local_neighbor_list.values()):
                continue
            prefix = ip.split('::')[0]
            subnet = prefix + '::/64'
            os.system('ip -6 route replace ' + subnet + ' via ' + nexthop_ip)
    
    #计算其他节点的路由表
    for start in member_list:
        if start == NODE_ID:
            continue
        update_message = ""
        for end in list(Graph.keys()):
            if start == end or end not in list(member_ip_list.keys()):
                #print(f"Skipping {start} to {end}, either it's the current node or not in member_ip_list.")
                continue
            path, cost = dijkstra(Graph, start, end)
            if cost == float('inf'):
                print(f"{start} to {end} 不可达")
                continue
            nexthop = path[1]
            end_ips = member_ip_list[end]
            for ip in end_ips: 
                update_message += ip + " " + nexthop + " "
        start_ip = member_ip_list[start][0]  # 获取起始节点的第1个IP地址
        routing_update_thread = threading.Thread(target=routing_update, args=(sock, src_ip, start_ip, update_message))
        routing_update_thread.start()
        intracluster_routing_info[start] = update_message
            #routing_update(sock, src_ip, start_ip, update_message) # 将路由更新信息发送给成员节点
    '''for start in list(Graph.keys()):
        if start == NODE_ID:
            continue
        for end in list(Graph.keys()):
            if start == end:
                continue
            path, cost = dijkstra(Graph, start, end)
            nexthop = path[1]
            #nexthop_ip = neighbor_list[nexthop]
            end_ips = member_ip_list[end]
            for ip in end_ips: 
                os.system('ip -6 route add ' + ip + ' via ' + nexthop_ip)'''

def periodic_update_intracluster_routing(sock, src_ip, interval):
    #global intra_cluster_graph
    #global last_update_intracluster_time
    
    while True:
        try:
            current_time = time.time()
            time_diff = current_time - last_update_intracluster_time.value
            '''with open("intra_update_time.txt", "a") as file:
                file.write(f'{NODE_ID} intra time diff: {time_diff}\n')'''
            if (time_diff < interval):
                time.sleep(interval)
                continue
            if (time_diff > 2 * interval):
                time.sleep(interval)
                continue
            with lock:
                local_graph = {key: list(intra_cluster_graph[key]) for key in intra_cluster_graph.keys()}
                '''with open("output.txt", "a") as file:
                    result ='graph: ' + str(local_graph) #+ "\n" + str(node_id) + ":" + str(graph[node_id])
                    # 将结果写入文件
                    file.write(result + "\n")'''

            generate_routing_table_process = multiprocessing.Process(target=generate_intracluster_routing_table, args=(local_graph, sock, src_ip))    
            generate_routing_table_process.start()
            #generate_routing_table(local_graph, sock, src_ip)  # 更新路由表
            if interval - (time.time()-current_time) > 0:
                time.sleep(interval-(time.time()-current_time))
        except Exception as e:
            print("Error in periodic_update_intracluster_routing:", NODE_ID)
            print(e)
            with open("error_log.txt", "a") as file:
                file.write(f"Error in periodic_update_intracluster_routing: {NODE_ID}\n")
                file.write(str(e) + "\n")

def update_node_state(payload_parts,sock, src_ip):
    #global intra_cluster_graph
    #global member_neighbor
    node_id = payload_parts[1]
    update_type = payload_parts[2]
    neighbor_id = payload_parts[3]
    with lock:
        if node_id not in list(intra_cluster_graph.keys()):
            intra_cluster_graph[node_id] = manager.list()
            member_neighbor[node_id] = manager.list()
        if update_type == 'NEW':
            member_neighbor[node_id].append(neighbor_id)
            intra_cluster_graph[node_id].append((neighbor_id, weight))
            #last_update_intracluster_time.value = time.time()
            #member_nu_seq[node_id] = seq
            '''local_graph = {key: list(intra_cluster_graph[key]) for key in intra_cluster_graph.keys()}
            with open("output.txt", "a") as file:
                result ='graph: ' + str(local_graph) #+ "\n" + str(node_id) + ":" + str(graph[node_id])
                # 将结果写入文件
                file.write(result + "\n")
            
            generate_routing_table(local_graph, sock, src_ip)  # 更新路由表'''

# 成员节点更新路由表
def update_routing_database(update_message):
    #print("Received routing update:", update_message)
    # 解析更新信息
    #global nexthop_dict
    #global neighbor_list
    parts = update_message.split(" ")
    routing_message = split_list(parts, 2)
    threads = []
    for item in routing_message:
        if len(item) != 2:
            continue
        dest_ip = item[0]
        nexthop_id = item[1]
        with lock:
            nexthop_dict[dest_ip] = nexthop_id
        nexthop_ip = neighbor_list[nexthop_id]
        if dest_ip in list(neighbor_list.values()):
            continue
        prefix = dest_ip.split('::')[0]
        subnet = prefix + '::/64'
        #thread = multiprocessing.Process(target=replace_route, args=(subnet, nexthop_ip))
        #thread.start()
        while True:
            try:
                os.system('ip -6 route replace ' + subnet + ' via ' + nexthop_ip)
                break
            except Exception as e:
                #time.sleep(1)
                continue
        #os.system('ip -6 route replace ' + subnet + ' via ' + nexthop_ip)
        ##print(f"Route to {dest_ip} via {nexthop_ip} added.")
    for thread in threads:
        thread.join()

def generate_intercluster_routing_table(local_inter_graph, local_intra_graph, sock, src_ip, local_inter_cluster_links, ip_addresses):
    '''global intercluster_routing_info
    global cluster_list
    global cluster_edge_list
    global cluster_neighbor_list
    global inter_cluster_links'''

    for end in list(local_inter_graph.keys()):
        if end == CLUSTER_ID:
            continue
        intercluster_path, cost = dijkstra(local_inter_graph, CLUSTER_ID, end)
        if cost == float('inf'):
            print(f"簇 {end} 不可达")
            continue
        print("new route to cluster ", end, ":", intercluster_path, "cost:", cost)
        nextcluster = intercluster_path[1]
        if nextcluster not in cluster_neighbor_list:
            print(f"Next cluster {nextcluster} not in cluster neighbor list, skipping route addition.")
            continue
        cluster_edge_node = cluster_edge_list[nextcluster][0]
        edge_ip = member_ip_list[cluster_edge_node][0]
        '''path_to_edge, cost = dijkstra(local_intra_graph, NODE_ID, cluster_edge_node)
        if cost == float('inf'):
            print(f"边缘节点 {cluster_edge_node} 不可达")
            continue
        print("new route to", cluster_edge_node, ":", path_to_edge, "cost:", cost)
        next_hop = path_to_edge[1]
        if next_hop not in neighbor_list:
            print(f"Next hop {next_hop} not in neighbor list, skipping route addition.")
            continue
        next_hop_ip = neighbor_list[next_hop]'''
        nexthop_ip = get_nexthop_ip(edge_ip.split('::')[0] + '::/64')
        self_is_edge = False
        if edge_ip in list(neighbor_list.values()):
            nexthop_ip = edge_ip
        
        if nexthop_ip == None:
            if edge_ip in ip_addresses:
                self_is_edge = True
            else:
                print(f"Next hop IP for edge {edge_ip} is None, skipping route addition.")
                continue
        local_cluster_list = {key: list(cluster_list[key]) for key in cluster_list.keys()}
        if end not in local_cluster_list:
            print(f"Cluster {end} not in cluster list, skipping route addition.")
            continue
        end_ips = local_cluster_list[end]
        subnets = []
        for ip in end_ips:
            if ip in list(neighbor_list.values()):
                continue
            prefix = ip.split('::')[0]
            subnet = prefix + '::/64'
            if subnet in local_inter_cluster_links:
                continue
            if subnet in subnets:
                continue
            subnets.append(subnet)
            '''with open("output.txt", "a") as file:
                result = f"Route to {ip} via {next_hop_ip} added."
                file.write(result + '\n')'''
            if self_is_edge == True:
                continue
            else:
                os.system('ip -6 route replace ' + subnet + ' via ' + nexthop_ip)
        dest_subnets = " ".join(subnets)
        edge_update_process = multiprocessing.Process(target=edge_update, args=(sock, src_ip, edge_ip, nextcluster, dest_subnets))
        edge_update_process.start()
        #edge_update(sock, src_ip, edge_ip, nextcluster, dest_subnets) # 将路由更新信息发送给边缘节点
        intercluster_routing_update_process = multiprocessing.Process(target=inter_cluster_routing_update, args=(sock, src_ip, cluster_edge_node, edge_ip, dest_subnets))
        intercluster_routing_update_process.start()
        with lock:
            intercluster_routing_info[end] = (cluster_edge_node, edge_ip, dest_subnets)
            if cluster_edge_node not in edge_routing_info:
                edge_routing_info[cluster_edge_node] = manager.list()
            edge_routing_info[cluster_edge_node].append((end, nextcluster))
        #inter_cluster_routing_update(sock, src_ip, cluster_edge_node, edge_ip, dest_subnets) # 将路由更新信息发送给成员节点

def periodic_update_intercluster_routing(sock, src_ip, interval):
    '''global last_update_intercluster_time
    global inter_cluster_graph
    global intra_cluster_graph
    global NODE_ID'''
    global inter_cluster_links
    while True:
        try:    
            current_time = time.time()
            time_diff = current_time - last_update_intercluster_time.value
            '''with open("inter_update_time.txt", "a") as file:
                file.write(f'{NODE_ID} inter time diff: {time_diff}\n')'''
            if (time_diff < interval):
                if interval - (time.time()-current_time) > 0:
                    time.sleep(interval - (time.time()-current_time))
                continue
            if (time_diff > 2 * interval):
                send_route_dblen_process = multiprocessing.Process(target=send_route_dblen, args=(sock, src_ip))
                send_route_dblen_process.start()
                if interval - (time.time()-current_time) > 0:
                    time.sleep(interval - (time.time()-current_time))
                continue
            with lock:
                '''local_neighbor_list = {key: neighbor_list[key] for key in neighbor_list.keys()}
                local_member_ip_list = {key: list(member_ip_list[key]) for key in member_ip_list.keys()}
                local_cluster_list = {key: list(cluster_list[key]) for key in cluster_list.keys()}
                local_cluster_edge_list = {key: list(cluster_edge_list[key]) for key in cluster_edge_list.keys()}'''
                local_inter_graph = {key: list(inter_cluster_graph[key]) for key in inter_cluster_graph.keys()}
                local_intra_graph = {key: list(intra_cluster_graph[key]) for key in intra_cluster_graph.keys()}
            
            intercluster_routing_process = multiprocessing.Process(target=generate_intercluster_routing_table, args=(local_inter_graph, local_intra_graph, sock, src_ip, inter_cluster_links, ip_addresses))
            intercluster_routing_process.start()
            if interval - (time.time()-current_time) > 0:
                time.sleep(interval - (time.time()-current_time))
        except Exception as e:
            print("Error in periodic_update_intercluster_routing:", NODE_ID)
            print(e)
            with open("error_log.txt", "a") as file:
                file.write(f"Error in periodic_update_intercluster_routing: {NODE_ID}\n")
                file.write(str(e) + "\n")

def get_route_dblen():
    process = subprocess.Popen("ip -6 route",universal_newlines=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, errs = process.communicate()   
    #print(out)
    # 获取路由表的输出，并按行分割
    routes = out.split('\n')
    #print("当前路由表:",routes)
    # 返回路由条数
    return len(routes)

def send_route_dblen(sock, src_ip):
    '''global CLUSTER_ID'''
    global neighbor_ip_list
    db_length = get_route_dblen()
    dblen = str(db_length)
    ttl = '3'
    data = b"route_dblen " + dblen.encode('ascii') + b" " + CLUSTER_ID.encode('ascii') + b" " + ttl.encode('ascii') # route_dblen <dblen>
    data_len = len(data)
    for dest_ip in neighbor_ip_list:
        # 创建 IP 头部
        ip_header = create_ipv6_header(src_ip, dest_ip, data_len, hop_limit=64)
        # 构造完整的数据包
        packet = ip_header + data
        try:
            sock.sendto(packet, (dest_ip, 0))
        except socket.error as e:
            print(f"{NODE_ID} Error sending route_dblen packet to {dest_ip}: {e}")
            with open('error_log.txt', 'a') as f:
                result = f"Error sending route_dblen packet to {dest_ip}: {e}\n"
                f.write(result)
        #print("route_dblen sent successfully")

def dealwith_route_dblen(sock, src_ip, db_len, lasthop, ttl):
    global neighbor_ip_list
    global HEAD_IP
    self_db_length = get_route_dblen()
    #如果自身路由表长度小于等于发送节点，发送need_route请求，请求路由更新信息
    if self_db_length < int(db_len): 
        with open('route_dblen_log.txt', 'a') as f:
            result = f"{NODE_ID} route_dblen: {db_len}, self_db_length: {self_db_length}, lasthop: {lasthop}, ttl: {ttl}, need to send need_route to HEAD_IP: {HEAD_IP}\n"
            f.write(result)
        send_need_route(sock, src_ip, HEAD_IP)
    if ttl > 1:
        ttl -= 1
        ttl = str(ttl)
        data = b"route_dblen " + db_len.encode('ascii') + b" " + CLUSTER_ID.encode('ascii') + b" " + ttl.encode('ascii') # route_dblen <dblen>
        data_len = len(data)
        #转发给其他邻居节点
        for dest_ip in neighbor_ip_list:
            if dest_ip == lasthop:
                continue
            # 创建 IP 头部
            ip_header = create_ipv6_header(src_ip, dest_ip, data_len, hop_limit=64)
            # 构造完整的数据包
            packet = ip_header + data
            try:
                sock.sendto(packet, (dest_ip, 0))
            except socket.error as e:
                print(f"{NODE_ID} Error forwarding route_dblen packet to {dest_ip}: {e}")
                with open('error_log.txt', 'a') as f:
                    result = f"Error forwarding route_dblen packet to {dest_ip}: {e}\n"
                    f.write(result)
            #print("route_dblen sent successfully")

def send_need_route(sock, src_ip, head_ip):
    #global HEAD_IP
    #global NODE_ID
    try:
        data = b"need_route " + NODE_ID.encode('ascii')  # need_route <cluster_id>
        data_len = len(data)
        # 创建 IP 头部
        ip_header = create_ipv6_header(src_ip, head_ip, data_len, hop_limit=64)

        # 构造完整的数据包
        packet = ip_header + data
        sock.sendto(packet, (head_ip, 0))
    except Exception as e:
        print("Error in send_need_route:", NODE_ID)
        print(e)
        print("head ip:", head_ip, "src_ip:", src_ip)
        with open("error_log.txt", "a") as file:
            result = f"Error in send_need_route: {NODE_ID}, head ip: {head_ip}\n"
            file.write(result)
    

def dealwith_need_route(sock, src_ip, member_id):
    '''global intracluster_routing_info
    global intercluster_routing_info
    global member_ip_list'''
    with lock:
        local_member_ip_list = {key: list(member_ip_list[key]) for key in member_ip_list.keys()}
        local_intercluster_routing_info = {key: intercluster_routing_info[key] for key in intercluster_routing_info.keys()}
        local_intracluster_routing_info = {key: intracluster_routing_info[key] for key in intracluster_routing_info.keys()}
        local_edge_routing_info = {key: list(edge_routing_info[key]) for key in edge_routing_info.keys()}
        local_cluster_list = {key: list(cluster_list[key]) for key in cluster_list.keys()}
    member_ip = local_member_ip_list[member_id][0]
    if member_id in local_intracluster_routing_info:
        intra_routing_message = local_intracluster_routing_info[member_id]
        #routing_update_process = multiprocessing.Process(target=routing_update, args=(sock, src_ip, member_ip, intra_routing_message))
        #routing_update_process.start()
        thread = threading.Thread(target=routing_update, args=(sock, src_ip, member_ip, intra_routing_message))
        thread.start()
        with open('need_route.txt', 'a') as f:
            f.write(f'send intra_routing_update to {member_id} : {member_ip} ' + '\n')

        #routing_update(sock, src_ip, member_ip, intra_routing_message) # 将路由更新信息发送给成员节点
    for cluster in local_intercluster_routing_info:
        edge_id, edge_ip, dest_subnets = local_intercluster_routing_info[cluster]
        if member_id == edge_id:
            continue
        data = b"inter_cluster_routing_update" + b" " + edge_ip.encode('ascii') + b" " + dest_subnets.encode('ascii')  # inter_cluster_routing_update <edge_ip> <dest_subnet1> <dest_subnet2> ...
        data_len = len(data)
        # 创建 IP 头部
        ip_header = create_ipv6_header(src_ip, member_ip, data_len, hop_limit=64)

        # 构造完整的数据包
        packet = ip_header + data
        while True:
            try:
                sock.sendto(packet, (member_ip, 0))
                break
            except Exception as e:
                print(f'{NODE_ID} sending intercluster_routing_update error: {e}, member_ip: {member_ip}' + '\n')
                with open('error_log.txt', 'a') as f:
                    f.write(f'{NODE_ID} sending intercluster_routing_update error: {e}, member_ip: {member_ip}' + '\n')
        with open('need_route.txt', 'a') as f:
            f.write(f'send inter_routing to {member_id} : {member_ip} ' + '\n')
            f.write(f'update_message: {dest_subnets}')

    if member_id in list(local_edge_routing_info.keys()):
        info = local_edge_routing_info[member_id]
        for end, nextcluster in info:
            end_ips = local_cluster_list[end]
            subnets = []
            for ip in end_ips:
                if ip in list(neighbor_list.values()):
                    continue
                prefix = ip.split('::')[0]
                subnet = prefix + '::/64'
                if subnet in inter_cluster_links:
                    continue
                if subnet in subnets:
                    continue
                subnets.append(subnet)
                '''with open("output.txt", "a") as file:
                    result = f"Route to {ip} via {next_hop_ip} added."
                    file.write(result + '\n')'''
            dest_subnets = " ".join(subnets)
            edge_update_process = multiprocessing.Process(target=edge_update, args=(sock, src_ip, member_ip, nextcluster, dest_subnets))
            edge_update_process.start()
            with open('need_route.txt', 'a') as f:
                f.write(f'send edge_update to {member_id} : {member_ip} ' + '\n')


def update_cluster_neighbor(payload_parts):
    #global inter_cluster_graph
    received_cluster_id = payload_parts[1]
    received_cluster_neighbor = payload_parts[2]
    #print('received_cluster_id: ', received_cluster_id)
    #print('received_cluster_neighbor: ', received_cluster_neighbor)
    '''with open("output.txt", "a") as file:
        result = 'received_cluster_id: ' + str(received_cluster_id) + ', received_cluster_neighbor: ' + str(received_cluster_neighbor)
        file.write(result + '\n')'''
    with lock:
        if received_cluster_id not in list(inter_cluster_graph.keys()):
            inter_cluster_graph[received_cluster_id] = manager.list()
        if received_cluster_id != CLUSTER_ID:
            inter_cluster_graph[received_cluster_id].append((received_cluster_neighbor, weight))  # 添加当前节点到邻簇图中
    #cluster_neighbor_description[received_cluster_id] = received_cluster_neighbor
    ##print(cluster_neighbor_description)
    #cluster_neighbors = " ".join(received_cluster_neighbor)
    
    
def get_nexthop_ip(dest_ip):
    # 使用 subprocess 调用系统命令
    process = subprocess.Popen("ip -6 route",universal_newlines=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, errs = process.communicate()   
    # 获取路由表的输出，并按行分割
    routes = out.split('\n')
    pattern = dest_ip + r" via ([\da-f:]+) dev"
    match = re.search(pattern, out)
    if match:
        #print("下一跳IP:", match.group(1))
        nexthop_ip = match.group(1)
        return nexthop_ip
    else:
        return None

def replace_route(subnet, nexthop_ip):
    os.system('ip -6 route replace ' + subnet + ' via ' + nexthop_ip)
    '''with open("route_log.txt", "a") as file:
            result = f"Route to {subnet} via {nexthop_ip} added."
            file.write(result + '\n')'''

# 簇内成员更新簇间路由表
def update_inter_routing(payload_parts):
    #global neighbor_list
    edge_ip = payload_parts[1]
    edge_subnet = edge_ip.split('::')[0] + '::/64'
    dest_subnets = payload_parts[2:]
    nexthop_ip = get_nexthop_ip(edge_subnet)
    if edge_ip in list(neighbor_list.values()):
        nexthop_ip = edge_ip
    if nexthop_ip == None:
        with open("inter_cluster_routing_update.txt", "a") as file:
            result = f"Cannot find route to edge node {edge_subnet}."
            file.write(result + '\n')
        return
    threads = []
    for subnet in dest_subnets:
        '''thread = multiprocessing.Process(target=replace_route, args=(subnet, nexthop_ip))
        thread.start()
        thread.join()'''
        while True:
            try:
                os.system('ip -6 route replace ' + subnet + ' via ' + nexthop_ip)
                break
            except Exception as e:
                #time.sleep(1)
                continue
        '''with open("route_log.txt", "a") as file:
            result = f"Route to {subnet} via {nexthop_ip} added."
            file.write(result + '\n')'''

# 簇边缘节点更新簇内路由表
def update_edge_routing(payload_parts):
    #global cluster_neighbor_dict
    cluster_neighbor = payload_parts[1]
    dest_subnets = payload_parts[2:]
    nexthop_id = cluster_neighbor_dict[cluster_neighbor][0]
    nexthop_ip = neighbor_list[nexthop_id]
    threads = []
    for subnet in dest_subnets:
        '''thread = multiprocessing.Process(target=replace_route, args=(subnet, nexthop_ip))
        thread.start()
        thread.join()'''
        os.system('ip -6 route replace ' + subnet + ' via ' + nexthop_ip)
        with open("route_log.txt", "a") as file:
            result = f"Route to {subnet} via {nexthop_ip} added."
            file.write(result + '\n')

def hello_react(raw_socket, neighbor_id, neighbor_ip, neighbor_cluster_id):
    if neighbor_id not in neighbor_id_list and status == 'MEMBER':
        with lock:
            neighbor_list[neighbor_id] = neighbor_ip
            neighbor_id_list.append(neighbor_id)
        neighbors = " ".join(neighbor_id_list)
        node_update(raw_socket, src_ip, NODE_ID, 'NEW', neighbor_id)
        #print('new neighbor_id: ', neighbor_id)
    elif neighbor_id not in neighbor_id_list and status == 'HEAD':
        with lock:
            neighbor_list[neighbor_id] = neighbor_ip
            neighbor_id_list.append(neighbor_id)
            if NODE_ID not in list(member_neighbor.keys()):
                member_neighbor[NODE_ID] = manager.list()
                intra_cluster_graph[NODE_ID] = manager.list()
            member_neighbor[NODE_ID].append(neighbor_id)
            intra_cluster_graph[NODE_ID].append((neighbor_id, weight))
        #print('new neighbor_id: ', neighbor_id)
        '''with open("output.txt", "a") as file:
            result = str(neighbor_list)
            file.write(result + '\n')'''
    
    #print('neighbor_list: ', neighbor_list)
    
    #如果是簇边缘节点接收到临簇的包, 告知簇首邻簇信息
    if neighbor_cluster_id != CLUSTER_ID and status == "MEMBER" and neighbor_cluster_id not in cluster_neighbor_list:
        #print('neighbor_cluster_id: ', neighbor_cluster_id)
        with lock:
            neighbor_list[neighbor_id] = neighbor_ip
            neighbor_id_list.append(neighbor_id)
            inter_cluster_link_subnet = neighbor_ip.split('::')[0] + '::/64'
            new_cluster_neighbor(raw_socket, HEAD_IP, neighbor_cluster_id, src_ip, NODE_ID, inter_cluster_link_subnet)
            with open("edge.txt", "a") as file:
                result = 'new_cluster_neighbor_id: ' + str(neighbor_cluster_id) + ', edge_node: ' + str(neighbor_id)
                file.write(result + '\n')
            cluster_neighbor_list.append(neighbor_cluster_id)
            if neighbor_cluster_id not in list(cluster_neighbor_dict.keys()):
                cluster_neighbor_dict[neighbor_cluster_id] = manager.list()
            cluster_neighbor_dict[neighbor_cluster_id].append(neighbor_id)
        #print('cluster_neighbor_list: ', cluster_.neighbor_list)

def dealwith_new_cluster_neighbor(raw_socket, src_ip, payload_parts):
    '''global cluster_neighbor_list
    global cluster_edge_list
    global inter_cluster_links
    global inter_cluster_graph'''
    new_cluster_neighbor_id = payload_parts[1]
    edge_node = payload_parts[2]
    inter_cluster_link_subnet = payload_parts[3]
    '''with lock:
        local_intercluster_info = {key: intercluster_routing_info[key] for key in intercluster_routing_info.keys()}
        local_intra_cluster_graph = {key: list(intra_cluster_graph[key]) for key in intra_cluster_graph.keys()}
        local_neighbor_list = {key: neighbor_list[key] for key in neighbor_list.keys()}
    if new_cluster_neighbor_id in local_intercluster_info:
        cluster_edge_node, edge_ip, dest_subnets =local_intercluster_info[new_cluster_neighbor_id]
        dest_subnets_list = dest_subnets.split(" ")
        if inter_cluster_link_subnet in dest_subnets_list:
            dest_subnets_list.remove(inter_cluster_link_subnet)
            with lock:
                intercluster_routing_info[new_cluster_neighbor_id] = (cluster_edge_node, edge_ip, " ".join(dest_subnets_list))
            # 更新簇首到簇间链路的路由
            while True:
                if edge_node == NODE_ID or edge_node not in list(member_ip_list.keys()):
                    #print(f"Skipping {end}, either it's the current node or not in member_ip_list.")
                    break
                path, cost = dijkstra(local_intra_cluster_graph, NODE_ID, edge_node)
                if cost == float('inf'):
                    #(f"{end} 不可达")
                    break
                print("new route to", edge_node, ":", path, "cost:", cost)
                nexthop = path[1]
                if nexthop not in local_neighbor_list:
                    #print(f"Next hop {nexthop} not in neighbor list, skipping route addition.")
                    break
                nexthop_ip = local_neighbor_list[nexthop]
                os.system('ip -6 route replace ' + inter_cluster_link_subnet + ' via ' + nexthop_ip)
                break
            # 更新其他节点到簇间链路的路由
            for start in member_list:
                if start == NODE_ID:
                    continue
                update_message = ""
                #end = edge_node
                if start == edge_node or edge_node not in list(member_ip_list.keys()):
                    #print(f"Skipping {start} to {end}, either it's the current node or not in member_ip_list.")
                    continue
                path, cost = dijkstra(local_intra_cluster_graph, start, edge_node)
                if cost == float('inf'):
                    print(f"{start} to {edge_node} 不可达")
                    continue
                nexthop = path[1]
                end_ips = member_ip_list[edge_node]
                for ip in end_ips: 
                    update_message += ip + " " + nexthop + " "
                start_ip = member_ip_list[start][0]  # 获取起始节点的第1个IP地址
                routing_update_thread = threading.Thread(target=routing_update, args=(raw_socket, src_ip, start_ip, update_message))
                routing_update_thread.start()'''

    with open("output.txt", "a") as file:
        result = 'new_cluster_neighbor_id: ' + str(new_cluster_neighbor_id) + ', edge_node: ' + str(edge_node)
        file.write(result + '\n')
    inter_cluster_links.append(inter_cluster_link_subnet)
    if new_cluster_neighbor_id not in list(cluster_edge_list.keys()):
        cluster_neighbor_list.append(new_cluster_neighbor_id)
        #print('cluster_neighbor_list: ', cluster_neighbor_list)
        #cluster_neighbors = " ".join(cluster_neighbor_list)
        cluster_neighbor_update(raw_socket, src_ip, CLUSTER_ID, new_cluster_neighbor_id)#发给MEO簇邻居信息
        with lock:
            if CLUSTER_ID not in list(inter_cluster_graph.keys()):
                inter_cluster_graph[CLUSTER_ID] = manager.list()
            inter_cluster_graph[CLUSTER_ID].append((new_cluster_neighbor_id, weight))
        cluster_edge_list[new_cluster_neighbor_id] = [edge_node]  # 初始化邻簇边缘成员列表
        #print('cluster_edge_list: ', cluster_edge_list)
    else:
        cluster_edge_list[new_cluster_neighbor_id].append(edge_node)  # 添加边缘成员到邻簇边缘成员列表
        #print('cluster_edge_list: ', cluster_edge_list)

def send_incluster_comfirm(sock, src_ip, head_id, cluster_id, head_ip, member_id, route_to_member):
    route_to_member_str = " ".join(route_to_member)
    data = b"incluster_confirm " + head_id.encode('ascii') + b" " + cluster_id.encode('ascii') + b" " + head_ip.encode('ascii') + b" " + member_id.encode('ascii') + b" " + route_to_member_str.encode('ascii')  # incluster_confirm <cluster_id> <member_id> <route_to_member>
    print('incluster_comfirm message: ', data.decode('ascii'))
    data_len = len(data)
    nexthop = route_to_member[0]
    '''if nexthop in ip_addresses:
        ip_parts = nexthop.split(':')
        if ip_parts[-1] == '10':
            ip_parts[-1] = '20'
            nexthop = ':'.join(ip_parts)
        elif ip_parts[-1] == '20':
            ip_parts[-1] = '10'
            nexthop = ':'.join(ip_parts)'''
    # 创建 IP 头部
    ip_header = create_ipv6_header(src_ip, nexthop, data_len, hop_limit=64)
    # 构造完整的数据包
    packet = ip_header + data
    try:   
        sock.sendto(packet, (nexthop, 0))
    except Exception as e:
        print("Error in send_incluster_comfirm:", NODE_ID)
        print(e)
        print("nexthop ip:", nexthop, "src_ip:", src_ip)
        with open("error_log.txt", "a") as file:
            result = f"Error in send_incluster_comfirm: {NODE_ID}, nexthop: {nexthop}\n"
            file.write(result)

def dealwith_incluster(payload_parts, raw_socket, src_ip):
    '''global member_list
    global member_ip_list
    global cluster_list'''
    global NODE_ID
    global CLUSTER_ID
    global HEAD_ID
    #print('new cluster member')
    print(f"{NODE_ID} received in_cluster payload_parts: ", payload_parts)
    new_member = payload_parts[1]
    member_ip_len = int(payload_parts[3])
    member_ips = []
    if new_member not in member_list:
        member_list.append(new_member)               # 添加新成员到簇成员列表
        member_ips = payload_parts[4:4+member_ip_len]  # 获取新成员的IP列表
        print("member_ips: ", member_ips)
        member_ip_list[new_member] = member_ips  # 更新成员IP列表
        cluster_list[CLUSTER_ID].extend(member_ips)  # 更新全局簇信息中本簇成员列表
    #neighbor_ip_list = get_neighbor_ips()
    cluster_update_head(raw_socket, src_ip, CLUSTER_ID, " ".join(member_ips), '2', '1')
    route_to_head = payload_parts[4+member_ip_len:]
    route_to_member = []
    for ip in route_to_head:
        ip_parts = ip.split(':')
        if ip_parts[-1] == '10':
            ip_parts[-1] = '20'
            hop_ip = ':'.join(ip_parts)
            route_to_member.append(hop_ip)
        elif ip_parts[-1] == '20':
            ip_parts[-1] = '10'
            hop_ip = ':'.join(ip_parts)
            route_to_member.append(hop_ip)
    print("route_to_member: ", route_to_member)
    send_incluster_comfirm(raw_socket, src_ip, HEAD_ID, CLUSTER_ID, HEAD_IP, new_member, route_to_member)
    #print('member_ip_list: ', member_ip_list)
    ##print('member_list: ', member_list)
    with open("output.txt", "a") as file:
        result = str(payload_parts)
        file.write(result + '\n')
        result = 'member_ip_list: ' + str(member_ip_list) 
        # 将结果写入文件
        file.write(result + "\n")
        result = 'member_list:' + str(member_list)
        file.write(result + '\n')

def receive_ipv6_packet(raw_socket):
    global neighbor_list
    global status
    global member_list
    global cluster_neighbor_list
    global cluster_neighbor_dict
    global cluster_list
    global cluster_id_list
    global member_neighbor
    global cluster_edge_list
    global head_ip_list
    global cluster_neighbor_description
    global neighbor_id_list
    global intra_cluster_graph
    global inter_cluster_graph
    global member_ip_list
    global HEAD_ID
    global HEAD_IP
    global NODE_ID
    global CLUSTER_ID
    global incluster_time
    global neighbor_ip_list

    neighbor_cluster_id = ''

    try:
        while True:
            packet, addr = raw_socket.recvfrom(65535)  # IPv6 MTU
            #print("received_packet")
            #print(f"{NODE_ID} Received packet from {addr}")
            # 解析IPv6头
            ipv6_header = packet[:40]
            payload = packet[40:]
            #print(f"IPv6 Header: {ipv6_header}")
            #print(f"Payload: {payload.decode('ascii')}")
            payload_parts = payload.decode('ascii').split(" ")  
            #接收到hello包
            if payload_parts[0] == "hello":
                neighbor_id = payload_parts[1]
                neighbor_ip = addr[0]  # 获取邻居IP
                neighbor_cluster_id = payload_parts[2]
                if neighbor_id not in neighbor_id_list and status == 'MEMBER':
                    with lock:
                        neighbor_list[neighbor_id] = neighbor_ip
                        neighbor_id_list.append(neighbor_id)
                    neighbors = " ".join(neighbor_id_list)
                    node_update(raw_socket, src_ip, NODE_ID, 'NEW', neighbor_id)
                    #print('new neighbor_id: ', neighbor_id)
                elif neighbor_cluster_id == CLUSTER_ID and neighbor_id not in neighbor_id_list and status == 'HEAD':
                    with lock:
                        neighbor_list[neighbor_id] = neighbor_ip
                        neighbor_id_list.append(neighbor_id)
                        if NODE_ID not in list(member_neighbor.keys()):
                            member_neighbor[NODE_ID] = manager.list()
                            intra_cluster_graph[NODE_ID] = manager.list()
                        member_neighbor[NODE_ID].append(neighbor_id)
                        intra_cluster_graph[NODE_ID].append((neighbor_id, weight))
                    #print('new neighbor_id: ', neighbor_id)
                    with open("output.txt", "a") as file:
                        result = str(neighbor_list)
                        file.write(result + '\n')
                
                #print('neighbor_list: ', neighbor_list)
                
                #如果是簇边缘节点接收到临簇的包, 告知簇首邻簇信息
                '''if neighbor_cluster_id != CLUSTER_ID and neighbor_id not in neighbor_id_list and (status == "MEMBER" or status == "HEAD") and neighbor_cluster_id not in cluster_neighbor_list:
                    #print('neighbor_cluster_id: ', neighbor_cluster_id)
                    with lock:
                        neighbor_list[neighbor_id] = neighbor_ip
                        neighbor_id_list.append(neighbor_id)
                        inter_cluster_link_subnet = neighbor_ip.split('::')[0] + '::/64'
                        new_cluster_neighbor(raw_socket, MEO_ip, neighbor_cluster_id, src_ip, NODE_ID, inter_cluster_link_subnet)
                        with open("edge.txt", "a") as file:
                            result = 'new_cluster_neighbor_id: ' + str(neighbor_cluster_id) + ', edge_node: ' + str(neighbor_id)
                            file.write(result + '\n')
                        cluster_neighbor_list.append(neighbor_cluster_id)
                        if neighbor_cluster_id not in list(cluster_neighbor_dict.keys()):
                            cluster_neighbor_dict[neighbor_cluster_id] = manager.list()
                        cluster_neighbor_dict[neighbor_cluster_id].append(neighbor_id)'''
                '''elif neighbor_cluster_id != CLUSTER_ID and status == "HEAD" and cluster_neighbor_list not in cluster_neighbor_list:
                     with lock:
                        neighbor_list[neighbor_id] = neighbor_ip
                        neighbor_id_list.append(neighbor_id)
                        cluster_neighbor_list.append(neighbor_cluster_id)
                        inter_cluster_link_subnet = neighbor_ip.split('::')[0] + '::/64'
                        inter_cluster_links.append(inter_cluster_link_subnet)'''

            #成员接收到路由更新信息
            if payload_parts[0] == "routing_update":
                update_message = " ".join(payload_parts[1:])
                with open('routing_update.txt', 'a') as f:
                    f.write(f"Received routing_update: {payload_parts}\n")
                process = multiprocessing.Process(target=update_routing_database, args=(update_message,))
                process.start()
            
            if payload_parts[0] == "incluster_inform":
                if status == "IDLE":
                    send_in_cluster(raw_socket, NODE_ID, src_ip, MEO_ip, local_ips)
            
            if payload_parts[0] == "incluster_confirm":
                status = "MEMBER"
                CLUSTER_ID = payload_parts[2]
                hello_process = multiprocessing.Process(target=call_hello, args=(NODE_ID, CLUSTER_ID))
                hello_process.start()

    except KeyboardInterrupt:
        print("Stopped receiving packets.")
    except socket.error as e:
        print(f"Error receiving packet: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e} in {NODE_ID}")
        with open("error_log.txt", "a") as file:
            result = f"An unexpected error occurred: {e}\n"
            file.write(result)

def main():
    raw_socket = create_raw_socket()
    if raw_socket is None:
        return
    send_member_ip(raw_socket, NODE_ID, src_ip, MEO_ip, local_ips)
    print("Listening for IPv6 packets...")
    receive_ipv6_packet(raw_socket)

    raw_socket.close()

if __name__ == "__main__":
    ip_addr_output = subprocess.check_output(['ip', '-6', 'addr'], text=True)
    ip_addresses = re.findall(r'inet6\s+([0-9a-fA-F:]+)(?:/\d+)?', ip_addr_output)
    ip_addresses = [ip for ip in ip_addresses if ip.startswith(('fd00:'))]  # 过滤掉2001和fe80开头的地址
    incluster_time = float('inf')
    manager = multiprocessing.Manager()
    lock = multiprocessing.Lock()
    intra_cluster_graph = manager.dict()   #簇内拓扑图，形式为{node1:[(neighbor1, weight1), (neighbor2, weight2)]}
    inter_cluster_graph = manager.dict()
    member_neighbor = manager.dict()      #邻居列表，e.g. {'test1': ['2001:db8:1::101'], 'test2': ['2001:db8:1::102']}
    last_update_intercluster_time = manager.Value('d', time.time())
    last_update_intracluster_time = manager.Value('d', time.time())
    last_update_intercluster_time.value = float('inf')
    last_update_intracluster_time.value = float('inf')
    NODE_ID = sys.argv[1]   #节点ID
    HEAD_IP = ''            #簇首IP
    HEAD_ID = ''            #簇首ID
    status = "IDLE"         #节点状态
    CLUSTER_ID = sys.argv[3]         #簇ID
    neighbor_list = manager.dict()      #邻居列表，e.g. {'test1': ['2001:db8:1::101'], 'test2': ['2001:db8:1::102']}
    neighbor_id_list = manager.list()   #邻居id列表，e.g. ["test1", "test2"]
    member_list = manager.list()        #成员列表，e.g. ["test1", "test2"]
    member_ip_list = manager.dict()     #成员IP列表，由簇首维护，e.g. {'test1': '2001:db8:1::101', 'test2': '2001:db8:1::102'}
    cluster_neighbor_list = manager.list()  #簇邻居列表，e.g. ["1", "2"]
    cluster_edge_list = manager.dict()      #簇边缘列表，由簇首维护，e.g.{<邻居簇1>: [<边缘成员1>, <边缘成员2>], <邻居簇2>: [<边缘成员3>]}
    cluster_neighbor_dict = manager.dict()   #簇邻居字典，由边缘节点维护, e.g. {1: ["test2", "test3"]}
    cluster_neighbor_description = {}   #簇邻居描述，只由MEO维护, e.g. {1: [2,3]}
    head_ip_list = []        #簇首IP列表，只由MEO维护
    cluster_id_list = []     #全局簇ID列表，由簇首维护
    cluster_list = manager.dict()        #全局簇ip信息列表，由簇首维护，e.g. {1: ['2001:db8:1::101', '2001:db8:1::102'], 2: ['2001:db8:2::101', '2001:db8:2::102']}
    inter_cluster_links = manager.list() #簇间链路列表，由MEO维护， e.g.['2001:db8:1::/64', '2001:db8:2::/64']
    MEO_ip = sys.argv[2]     #MEO卫星IP地址
    #member_nu_seq = {}      #成员节点的NU_seq，形式为{node1:2,node2:3 }
    nexthop_dict = manager.dict()      #下一跳字典，形式为{dest1: nexthop1, dest2: nexthop2}
    weight = 10
    local_ips = " ".join(ip_addresses)  # 获取本地IP地址列表
    #print("ip_addrs:", local_ips)
    src_ip = ip_addresses[0] # 源IPv6地址
    member_ip_list[NODE_ID] = ip_addresses  # 初始化成员IP列表，添加自己的IP地址
    intercluster_routing_info = manager.dict()  #簇间路由信息，由簇首维护
    intracluster_routing_info = manager.dict()
    edge_routing_info = manager.dict()
    neighbor_ip_list = get_neighbor_ips()
    main()
