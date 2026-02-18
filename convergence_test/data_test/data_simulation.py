# 控制网络中开始传输数据块

import os
import threading
from sqlalchemy import create_engine, text
import pandas as pd
import pymysql
import time
import subprocess
import re
import redis
import random


db = pymysql.connect(host='10.101.169.132',
                     user='root',
                     password='123456'
                     )
cursor = db.cursor()
cursor.execute("use cluster_routing_database")

def deal_with_data(container):
    os.system("docker exec -it " + container + " python3 deal_data.py " + container)

def generate_data(container, dest_ip):
    os.system("docker exec -it " + container + " python3 generate_data.py " + dest_ip + " " + container)

def record_time():
    temp_cursor = db.cursor()
    temp_cursor.execute("use cluster_routing_database")
    current_time = time.time()
    lock = threading.Lock()
    lock.acquire()
    temp_cursor.execute("select * from convergence_table")
    db.commit()
    lock.release()
    result = temp_cursor.fetchall()
    if len(result) > 0:
        convergence_time = float(current_time) - float(result[0][0])
    else:
        convergence_time = 0.0
    lock = threading.Lock()
    lock.acquire()
    print(time.time())
    temp_cursor.execute("insert into convergence_table values ('%s', '%f')" %(str(current_time), float(convergence_time)))
    db.commit()
    lock.release()
    print('record time')

def listen_for_cluster():
    # 连接 Redis
    r = redis.Redis(host='10.101.169.132', port=6379, db=0)
    channel = 'create_cluster'
    pubsub = r.pubsub()
    pubsub.subscribe(channel)  # 监听 channel

    print("Waiting for Signal of Service ...")

    # 接收消息
    for message in pubsub.listen():
        if message['type'] == 'message': 
            return message['data'].decode()

def enable_cluster_routing_MEO(meo_id,belonged_head_ip_list):
    os.system(f"docker exec -it {meo_id} python3 socket_recv_MEO.py {meo_id} " + " ".join(belonged_head_ip_list))
    print(f"docker exec -it {meo_id} python3 socket_recv_MEO.py {meo_id} " + " ".join(belonged_head_ip_list))

def get_cluster_heads():
    orbit = 10
    sat = 2
    cluster_heads = []
    while orbit < 21:
        while sat < 16:
            if sat < 10:
                cluster_head = "WALKER192-" + str(orbit) + "0" + str(sat)
            else:
                cluster_head = "WALKER192-" + str(orbit) + str(sat)
            cluster_heads.append(cluster_head)
            sat = sat + 3
        sat = 2
        orbit = orbit + 20
    return cluster_heads

def get_deleted_nodes(orbit = ['39', '40']):
    deleted_nodes = []
    for o in orbit:
        for p in range(1, 16):
            if p < 10:
                node = "WALKERdgm-" + str(o) + "0" + str(p)
            else:
                node = "WALKERdgm-" + str(o) + str(p)
            deleted_nodes.append(node)
    return deleted_nodes

def get_ifconfig_output(container):
    process = subprocess.Popen(f"docker exec -i {container} ifconfig",universal_newlines=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, errs = process.communicate() 
    # 提取并求和
    rx_bytes_list = re.findall(r'RX bytes:(\d+)', out)
    total_rx_bytes = sum(int(b) for b in rx_bytes_list)
    return total_rx_bytes

def record_overhead():
    #engine = create_engine('mysql+mysqlconnector://root:123456@10.101.169.132:3306/Starlink')
    query_parameter1 = text("SELECT name FROM walker_sop where starsign = 'xw'")
    query_parameter2 = text("SELECT name FROM walker_sop where starsign = 'DGM'")
    # 执行查询并将结果加载到 Pandas DataFrame
    df1 = pd.read_sql(query_parameter1, engine)
    df2 = pd.read_sql(query_parameter2, engine)
    #df = pd.concat([df1, df2], ignore_index = True)
    df = df2
    # 获取 name 列的所有数据
    name_list = df['name'].tolist()
    total_rx_bytes = 0
    name_list = ['MEO-1', 'MEO-2', 'MEO-3', 'MEO-4', 'MEO-5', 'MEO-6', 'MEO-7', 'MEO-8'] + name_list
    for container_name in name_list:
        total_rx_bytes += get_ifconfig_output(container_name)
    #total_rx_bytes += get_ifconfig_output('MEO')
    lock = threading.Lock()
    lock.acquire()
    cursor.execute("insert into overhead_table values ('%s')" %(str(total_rx_bytes)))
    db.commit()
    lock.release()

def get_routing_overhead():
    record_overhead()
    lock = threading.Lock()
    lock.acquire()
    cursor.execute("select * from overhead_table")
    db.commit()
    lock.release()
    result = cursor.fetchall()
    ini_overhead = int(result[-2][0])
    final_overhead = int(result[-1][0])
    print("Routing Overhead: ", (final_overhead - ini_overhead)/(1024*1024), "MB")

def split_list(lst, chunk_size):
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]



if __name__ == "__main__":
    os.system('rm /home/wspn02/mega/WGQ/convergence_test/arrived_pkts.txt')
    os.system('rm /home/wspn02/mega/WGQ/convergence_test/total_pkts.txt')
    #监听簇配置参数，包括簇半径和簇数量
    '''message = listen_for_cluster()
    print("Received message:", message)
    cluster_radius = message.split(',')[0]
    cluster_counts = message.split(',')[1]
    print("cluster_radius:", cluster_radius)
    print("cluster_counts:", cluster_counts)'''
    
    #os.system('rm /home/wspn02/mega/WGQ/convergence_test/cluster_result.txt')
    engine = create_engine('mysql+mysqlconnector://root:123456@10.101.169.132:3306/Starlink')
    #record_overhead()
    query_parameter1 = text("SELECT name FROM walker_sop where starsign = 'xw'")
    query_parameter2 = text("SELECT name FROM walker_sop where starsign = 'DGM'")
    # 执行查询并将结果加载到 Pandas DataFrame
    df1 = pd.read_sql(query_parameter1, engine)
    df2 = pd.read_sql(query_parameter2, engine)
    #df = pd.concat([df1, df2], ignore_index = True)
    df = df2
    # 获取 name 列的所有数据
    name_list = df['name'].tolist()
    '''df = pd.read_csv('/home/wspn02/mega/WGQ/convergence_test/192/walker_192.csv')
    name_list = df['satellite name'].tolist()'''
    for container in name_list:
        threading.Thread(target=deal_with_data, args=(container,)).start()
    
    #threading.Thread(target=generate_data, args=('WALKERdgm-3104','fd00:abcd:17::20')).start()
    container_list = random.sample(name_list, 10)
    container_list = ['WALKERdgm-3104', 'WALKERdgm-3703', 'WALKERdgm-4003', 'WALKERdgm-3311', 'WALKERdgm-3708', 'WALKERdgm-3204', 'WALKERdgm-3905', 'WALKERdgm-3203', 'WALKERdgm-3509', 'WALKERdgm-3402']
    print(container_list)
    time.sleep(5)
    #end_list = random.sample(name_list, 5)
    for i in range(5):
        cursor.execute("select * from ip_table where ip_satid = '%s'" % container_list[i + 5])
        end_ip = cursor.fetchone()[1]
        threading.Thread(target=generate_data, args=(container_list[i],end_ip)).start()
    time.sleep(60)
    os.system("~/anaconda3/envs/be2/bin/python /home/wspn02/mega/WGQ/convergence_test/end_routing.py")
    os.system('~/anaconda3/envs/be2/bin/python /home/wspn02/mega/WGQ/convergence_test/data_test/cal_delay.py')
    #threading.Thread(target=generate_data, args=('WALKERdgm-4004','fd00:abcd:b::20')).start()
    

    