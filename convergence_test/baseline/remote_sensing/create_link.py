#本文件用于创建链路，构建网络
import time
import os
import subprocess
from tracemalloc import start
import pandas as pd
import pymysql
import multiprocessing
from py2neo import Graph
from datetime import datetime, timedelta
import threading
import psutil
from sqlalchemy import create_engine, text, inspect
import re


#link_f = open("/home/wspn02/mega/WGQ/link.txt")
docker_num = 0
network_id = 10
ip_2 = 18
ip_3 = 10
port_id = 1
line = ""
src_tar = []
db = pymysql.connect(host='10.101.169.132',
                     user='root',
                     password='123456'
                     )
cursor = db.cursor()
cursor.execute("use cluster_routing_database")
engine = create_engine('mysql+mysqlconnector://root:123456@10.101.169.132:3306/Starlink')
process_list = []
source_ips = []
target_ips = []
ISL_ip_v6 = ""
source_ip_v6 = ""
target_ip_v6 = ""
ISL_ip_v4 = ""
source_ip_v4 = ""
target_ip_v4 = ""
source_id = ""
target_id = ""
links = []

graph=Graph("neo4j://10.101.169.132:7687",auth=("neo4j","lst123456"))

#-----------------------------------------------------------------------
start_str='00-00-00_00-00-00' #同轨建链时间->不变
#-----------------------------------------------------------------------


def read_character(scenename):
    queryread = "SELECT * FROM charactor WHERE user = %s"
    df_parameter = pd.read_sql(queryread, engine, params=(scenename,))

    start_time_str = df_parameter.loc[0, 'startime']
    end_time_str = df_parameter.loc[0, 'endtime']
    time_slot_second = int(df_parameter.loc[0, 'time_slot'])

    return(start_time_str, end_time_str, time_slot_second)

def read_startend_neo4j(current_time): #读取开始和结束卫星
    current_time_str = current_time.strftime('%Y-%m-%d_%H-%M-%S')
    query_1 =f"""
    MATCH (s:Satellite)-[r:start]->(t:Time {{time_slot: '{current_time_str}'}})
    RETURN s.name AS start_sat, r.start_delay AS start_delay
    """
    result_start = graph.run(query_1).data()

    query_2 =f"""
    MATCH (s:Satellite)-[r:end]->(t:Time {{time_slot: '{current_time_str}'}})
    RETURN s.name AS end_sat, r.end_delay As end_delay
    """
    result_end = graph.run(query_2).data()

    return result_start, result_end

def read_delay(current_time):
    search_time = current_time
    search_time_str = search_time.strftime('%Y-%m-%d_%H-%M-%S')
    query =f"""
    MATCH (a:Satellite)-[r:connected]->(b)
    WHERE r.time_slot = '{search_time_str}'
    RETURN a.name as sat1, b.name as sat2, r.delay as delay
    """
    link_delay = graph.run(query).data()
    return link_delay


def connect_ovs(sat_id, eth_id, sat_ip):
    os.system("ovs-docker add-port brConn eth-" + eth_id + " " + sat_id +  " --ipaddress=" + sat_ip + "/24")
    print("ovs-docker add-port brConn eth-" + eth_id + " " + sat_id +  " --ipaddress=" + sat_ip + "/24")

#创建链路
def create_link(args):
    src_tar, ISL_ip_v4, ISL_ip_v6, source_ip_v4, target_ip_v4, source_ip_v6, target_ip_v6, network_id = args
    #-------------------------------------------------------------------------------------------------------------#
    os.system("docker network create network" + str(network_id) + " --subnet " + ISL_ip_v4 + " --ipv6 --subnet " + ISL_ip_v6)
    os.system("docker network connect network" + str(network_id) + " " + src_tar['sat1'] + " --ip6 " + source_ip_v6)    #将卫星1连接到docker网络
    os.system("docker network connect network" + str(network_id) + " " + src_tar['sat2'] + " --ip6 " + target_ip_v6)    #将卫星2连接到docker网络
    #-------------------------------------------------------------------------------------------------------------#
'''
    src_id = src_tar["sat1"].split('-')[1]
    tar_id = src_tar["sat2"].split('-')[1]
    thread1 = threading.Thread(target=connect_ovs, args=(src_tar['sat1'], tar_id, source_ip))
    thread1.start()
    thread1.join()
    thread2 = threading.Thread(target=connect_ovs, args=(src_tar['sat2'], src_id, target_ip))
    thread2.start()
    thread2.join()
    '''
    #os.system("ovs-docker add-port brConn eth-" + tar_id + " " + src_tar['sat1'] +  " --ipaddress=" + source_ip + "/24")
    #os.system("ovs-docker add-port brConn eth-" + src_id + " " + src_tar['sat2'] +  " --ipaddress=" + target_ip + "/24")
        
def monitor_resource():
    time = 0
    while is_finished == False:
        cpu_usage = psutil.cpu_percent(interval=1)
        #print(f"CPU Usage: {cpu_usage}%")
        memory = psutil.virtual_memory()
        #print(f"Memory Usage: {memory.percent}%")
        lock = threading.Lock()
        lock.acquire()
        cursor.execute("insert into resource_table values (%d, %f, %f, '%s')" %(time, cpu_usage, memory.percent, "create_link"))
        db.commit()
        lock.release()
        time = time + 1

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
    name_list = df['name'].tolist()
    # 获取 name 列的所有数据
    #name_list = df['name'].tolist()
    #df = pd.read_csv('/home/wspn02/mega/WGQ/LXM/walker_dyd.csv')
    #name_list = df['satellite name'].tolist()
    MEO_IDs = ['MEO-1', 'MEO-2', 'MEO-3', 'MEO-4', 'MEO-5', 'MEO-6', 'MEO-7', 'MEO-8']
    name_list = MEO_IDs + name_list
    total_rx_bytes = 0
    for container_name in name_list:
        total_rx_bytes += get_ifconfig_output(container_name)
    #total_rx_bytes += get_ifconfig_output('MEO')
    lock = threading.Lock()
    lock.acquire()
    cursor.execute("insert into overhead_table values ('%s')" %(str(total_rx_bytes)))
    db.commit()
    lock.release()
    
def get_orbit_number(text):
    match = re.search(r"(\d{2})(\d{2})", text)
    if match:
        # 提取匹配的两组数字
        num1 = int(match.group(1))  # 提取第一组数字并转为整数
        num2 = int(match.group(2))  # 提取第二组数字并转为整数
    else:
        print("未找到匹配的数字")
    return num1, num2

def get_cluster(orbit):
    cluster_orbits = 4
    cluster_id = int((orbit - 30 + cluster_orbits - 1) / cluster_orbits)
    return cluster_id

if __name__ == "__main__":
    start_time_str, end_time_str, time_slot_second= read_character('test')
    start_time = datetime.strptime(start_time_str, '%Y-%m-%d_%H-%M-%S')
    end_time = datetime.strptime(end_time_str, '%Y-%m-%d_%H-%M-%S')
    time_slot = timedelta(seconds=10)
    current_time= start_time
    #os.system("ulimit -n 2048")
    is_finished = False
    #monitor_process = multiprocessing.Process(target=monitor_resource)
    #monitor_process.start()
    start_time = time.time()
    pool = multiprocessing.Pool()
    args = []
    #读取建链关系
    query1=f'''MATCH (a)-[r:xwlink]->(b) 
    WHERE r.time_slot = '{start_str}'
    RETURN a.name as sat1, b.name as sat2, r.delay as delay
    '''
    start_link1 = graph.run(query1).data() #星座1建链

    query2=f'''MATCH (a)-[r:dgmlink]->(b) 
    WHERE r.time_slot = '{start_str}'
    RETURN a.name as sat1, b.name as sat2, r.delay as delay
    '''
    start_link2 = graph.run(query2).data() #星座2建链
    """query2=f'''MATCH (a)-[r:connected]->(b)
    WHERE r.time_slot = '{start_time_str}'
    RETURN a.name as sat1, b.name as sat2, r.delay as delay
    '''
    start_link2 = graph.run(query2).data() #第一个时隙的异轨道建链"""
    #print(" 初始建链关系共 :   ", len(start_link2)," 条\n")
    '''start_link = start_link1#初始拓扑
    print(start_link)
    print(" 初始建链关系共 :   ", len(start_link)," 条\n")'''
    df = pd.read_csv('/home/wspn02/mega/WGQ/convergence_test/dgm/dgm_link_nnn.csv')
    sat_list = df[['source', 'target']].rename(columns={'source': 'sat1', 'target': 'sat2'})
    start_link = sat_list.to_dict('records')
    added_links = [{'sat1': 'WALKERdgm-3901', 'sat2': 'WALKERdgm-3101'}, {'sat1': 'WALKERdgm-3906', 'sat2': 'WALKERdgm-3106'}, {'sat1': 'WALKERdgm-3911', 'sat2': 'WALKERdgm-3111'}]
    #start_link.extend(added_links)
    print(start_link)
    #根据建链关系创建链路，构建网络
    for link in start_link:
        src_tar = link
        ISL_ip_v4 = "172."+ str(ip_2) + "." + str(ip_3) + ".0/24"
        ISL_ip_v6 = 'fd00:abcd:' + hex(network_id)[2:] + "::0/64"  #docker network的网段，每个docker network的是一个网桥，连接到该网桥的端口可以直接通信
        source_ip_v4 = "172."+ str(ip_2) + "." + str(ip_3) + ".20"  #卫星1的IPv4地址
        target_ip_v4 = "172."+ str(ip_2) + "." + str(ip_3) + ".30"  #卫星2的IPv4地址
        source_ip_v6 = 'fd00:abcd:' + hex(network_id)[2:] + "::10" #卫星1的IPv6地址
        target_ip_v6 = 'fd00:abcd:' + hex(network_id)[2:] + "::20" #卫星2的IPv6地址
        args.append((src_tar, ISL_ip_v4, ISL_ip_v6, source_ip_v4, target_ip_v4, source_ip_v6, target_ip_v6, network_id))    #将参数添加到args列表中，用于多进程创建链路
        #process = multiprocessing.Process(target=create_link, args=(src_tar, ISL_ip, source_ip, target_ip, network_id))
        #process.start()
        #sat_orbit1, sat_num1 = get_orbit_number(src_tar['sat1'])
        #sat_orbit2, sat_num2 = get_orbit_number(src_tar['sat2'])
        cursor.execute("insert into ip_table values('%s', '%s')" % (src_tar['sat1'], source_ip_v6))    #将卫星1的IP地址插入数据库
        cursor.execute("insert into ip_table values('%s', '%s')" % (src_tar['sat2'], target_ip_v6))
        '''if sat_num1 == 6 and sat_num2 == 6:
            cursor.execute("insert into ip_table_area0 values('%s', '%s')" % (src_tar['sat1'], source_ip))    
            cursor.execute("insert into ip_table_area0 values('%s', '%s')" % (src_tar['sat2'], target_ip))
        if sat_orbit1 == sat_orbit2:    
            cursor.execute("insert into ip_table values('%s', '%s')" % (src_tar['sat1'], source_ip))    #将卫星1的IP地址插入数据库
            cursor.execute("insert into ip_table values('%s', '%s')" % (src_tar['sat2'], target_ip))    #将卫星2的IP地址插入数据库'''
        print("insert into link_table values('%s', '%s', 'network%s', '%s')" % (src_tar['sat1'], src_tar['sat2'], str(network_id), ISL_ip_v6))
        cursor.execute("insert into link_table values('%s', '%s', 'network%s', '%s', '%s', '%s')" % (src_tar['sat1'], src_tar['sat2'], str(network_id), ISL_ip_v6, source_ip_v6, target_ip_v6))
        db.commit()
        if ip_3 < 255:
            ip_3 = ip_3 + 1
        else:
            ip_3 = 1
            ip_2 = ip_2 + 1
        if ip_2 == 3 and ip_3 == 8:
            ip_3 = ip_3 + 2
        network_id = network_id + 1
        #process_list.append(process)
    #多进程创建链路
    with multiprocessing.Pool(processes=10) as pool:
        pool.map(create_link, args)
    end_time = time.time()
    creating_link_time = end_time - start_time
    print("创建链路所需时间：", creating_link_time)
    lock = threading.Lock()
    lock.acquire()
    cursor.execute("insert into time_table values ('%s', %f)" % ('create_link_time', creating_link_time))
    db.commit()
    lock.release()
    is_finished = True
    #record_overhead()
    db.close()
    #os.system("python3 /home/wspn02/mega/WGQ/rename.py")
    #os.system("python3 /home/wspn02/mega/WGQ/conf_rip.py")
