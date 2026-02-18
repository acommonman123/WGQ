import os
import threading
from sqlalchemy import create_engine, text
import pandas as pd
import pymysql
import time
import subprocess
import re

db = pymysql.connect(host='10.101.169.132',
                     user='root',
                     password='123456'
                     )
cursor = db.cursor()
cursor.execute("use cluster_routing_database")

def enable_cluster_routing(container, meo_ip):
    os.system("docker exec -it " + container + " python3 socket_recv_LEO.py " + container)

def enable_hello(container):
    os.system("docker exec -it " + container + " python3 hello.py " + container + " 1")

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
    print("start_time:", current_time)

def enable_cluster_routing_MEO(meo_id,belonged_head_ip_list):
    os.system(f"docker exec -it {meo_id} python3 socket_recv_MEO.py {meo_id} " + " ".join(belonged_head_ip_list))
    print(f"docker exec -it {meo_id} python3 socket_recv_MEO.py {meo_id} " + " ".join(belonged_head_ip_list))

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
        orbit = orbit + 2
    return cluster_heads

def get_deleted_nodes(orbit = ['39', '40']):
    deleted_nodes = []
    for o in orbit:
        for p in range(1, 16):
            if p < 10:
                node = "WALKERdyd-" + str(o) + "0" + str(p)
            else:
                node = "WALKERdyd-" + str(o) + str(p)
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
    print('recording overhead...')
    query_parameter1 = text("SELECT name FROM walker_sop where starsign = 'xw'")
    query_parameter2 = text("SELECT name FROM walker_sop where starsign = 'DGM'")
    # 执行查询并将结果加载到 Pandas DataFrame
    df1 = pd.read_sql(query_parameter1, engine)
    df2 = pd.read_sql(query_parameter2, engine)
    #df = pd.concat([df1, df2], ignore_index = True)
    df = df2
    # 获取 name 列的所有数据
    #name_list = df['name'].tolist()
    df = pd.read_csv('/home/wspn02/mega/WGQ/LXM/walker_dyd.csv')
    name_list = df['satellite name'].tolist()
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
    engine = create_engine('mysql+mysqlconnector://root:123456@10.101.169.132:3306/Starlink')

    query_parameter1 = text("SELECT name FROM walker_sop where starsign = 'xw'")
    query_parameter2 = text("SELECT name FROM walker_sop where starsign = 'DGM'")
    #record_overhead()
    # 执行查询并将结果加载到 Pandas DataFrame
    df1 = pd.read_sql(query_parameter1, engine)
    df2 = pd.read_sql(query_parameter2, engine)
    #df = pd.concat([df1, df2], ignore_index = True)
    df = df2
    # 获取 name 列的所有数据
    name_list = df['name'].tolist()
    df = pd.read_csv('/home/wspn02/mega/WGQ/LXM/walker_dyd.csv')
    name_list = df['satellite name'].tolist()
    #deleted_nodes = get_deleted_nodes(orbit = ['19'])
    #for dl in deleted_nodes:
    #    name_list.remove(dl)
    # 打印结果
    print(name_list)
    thread_list = []
    
    #time.sleep(5)  # 等待5秒钟，确保所有线程都已启动
    #head_id_list = ['WALKERXW-5102', 'WALKERXW-5105', 'WALKERXW-5108', 'WALKERXW-5402','WALKERXW-5405', 'WALKERXW-5408', 'WALKERXW-5702', 'WALKERXW-5705','WALKERXW-5708', 'WALKERXW-6002', 'WALKERXW-6005', 'WALKERXW-6008']
    #head_id_list = ['WALKERXW-5102', 'WALKERXW-5105', 'WALKERXW-5108', 'WALKERXW-5302','WALKERXW-5305', 'WALKERXW-5308', 'WALKERXW-5502', 'WALKERXW-5505','WALKERXW-5508', 'WALKERXW-5702', 'WALKERXW-5705', 'WALKERXW-5708', 'WALKERXW-5902', 'WALKERXW-5905', 'WALKERXW-5908','WALKERXW-6102', 'WALKERXW-6105', 'WALKERXW-6108']
    #150颗dgm
    #head_id_list = ['WALKERdgm-3101', 'WALKERdgm-3106', 'WALKERdgm-3111', 'WALKERdgm-3301', 'WALKERdgm-3306', 'WALKERdgm-3311', 'WALKERdgm-3501', 'WALKERdgm-3506', 'WALKERdgm-3511', 'WALKERdgm-3701', 'WALKERdgm-3706', 'WALKERdgm-3711', 'WALKERdgm-3901', 'WALKERdgm-3906', 'WALKERdgm-3911']
    #head_id_list = ['WALKERdgm-3101', 'WALKERdgm-3106', 'WALKERdgm-3111', 'WALKERdgm-3401', 'WALKERdgm-3406', 'WALKERdgm-3411', 'WALKERdgm-3701', 'WALKERdgm-3706', 'WALKERdgm-3711', 'WALKERdgm-3901', 'WALKERdgm-3906', 'WALKERdgm-3911']
    #135颗dgm
    #head_id_list = ['WALKERdgm-3101', 'WALKERdgm-3106', 'WALKERdgm-3111', 'WALKERdgm-3401', 'WALKERdgm-3406', 'WALKERdgm-3411', 'WALKERdgm-3701', 'WALKERdgm-3706', 'WALKERdgm-3711']
    #120颗dgm
    #head_id_list = ['WALKERdgm-3101', 'WALKERdgm-3106', 'WALKERdgm-3111', 'WALKERdgm-3301', 'WALKERdgm-3306', 'WALKERdgm-3311', 'WALKERdgm-3501', 'WALKERdgm-3506', 'WALKERdgm-3511', 'WALKERdgm-3701', 'WALKERdgm-3706', 'WALKERdgm-3711']
    #head_id_list = get_cluster_heads()
    #head_id_list = ['WALKER192-1002', 'WALKER192-1005', 'WALKER192-1008', 'WALKER192-1011', 'WALKER192-1014', 'WALKER192-1016', 'WALKER192-1202', 'WALKER192-1205', 'WALKER192-1208', 'WALKER192-1211', 'WALKER192-1214', 'WALKER192-1216', 'WALKER192-1402', 'WALKER192-1405', 'WALKER192-1408', 'WALKER192-1411', 'WALKER192-1414', 'WALKER192-1416', 'WALKER192-1602', 'WALKER192-1605', 'WALKER192-1608', 'WALKER192-1611', 'WALKER192-1614', 'WALKER192-1616', 'WALKER192-1802', 'WALKER192-1805', 'WALKER192-1808', 'WALKER192-1811', 'WALKER192-1814', 'WALKER192-1816', 'WALKER192-2002', 'WALKER192-2005', 'WALKER192-2008', 'WALKER192-2011', 'WALKER192-2014', 'WALKER192-2016']
    #head_id_list = ['WALKER192-1002', 'WALKER192-1005', 'WALKER192-1008', 'WALKER192-1011', 'WALKER192-1014', 'WALKER192-1016', 'WALKER192-1302', 'WALKER192-1305', 'WALKER192-1308', 'WALKER192-1311', 'WALKER192-1314', 'WALKER192-1316', 'WALKER192-1602', 'WALKER192-1605', 'WALKER192-1608', 'WALKER192-1611', 'WALKER192-1614', 'WALKER192-1616', 'WALKER192-1902', 'WALKER192-1905', 'WALKER192-1908', 'WALKER192-1911', 'WALKER192-1914', 'WALKER192-1916']
    #head_id_list = ['WALKER144-1002', 'WALKER144-1005', 'WALKER144-1008', 'WALKER144-1011', 'WALKER144-1202','WALKER144-1205', 'WALKER144-1208', 'WALKER144-1211', 'WALKER144-1402', 'WALKER144-1405','WALKER144-1408', 'WALKER144-1411', 'WALKER144-1602', 'WALKER144-1605', 'WALKER144-1608', 'WALKER144-1611', 'WALKER144-1802', 'WALKER144-1805', 'WALKER144-1808', 'WALKER144-1811','WALKER144-2002', 'WALKER144-2005', 'WALKER144-2008', 'WALKER144-2011']
    #head_id_list = ['WALKER144-1002', 'WALKER144-1005']
    #head_id_list = ['WALKERdyd-1001', 'WALKERdyd-1006', 'WALKERdyd-1011', 'WALKERdyd-1201', 'WALKERdyd-1206', 'WALKERdyd-1211', 'WALKERdyd-1401', 'WALKERdyd-1406', 'WALKERdyd-1411', 'WALKERdyd-1601', 'WALKERdyd-1606', 'WALKERdyd-1611', 'WALKERdyd-1801', 'WALKERdyd-1806', 'WALKERdyd-1811']
    #150颗WALKER
    #head_id_list = ['WALKERdyd-1002', 'WALKERdyd-1005', 'WALKERdyd-1008', 'WALKERdyd-1011', 'WALKERdyd-1014', 'WALKERdyd-1202', 'WALKERdyd-1205', 'WALKERdyd-1208', 'WALKERdyd-1211', 'WALKERdyd-1214', 'WALKERdyd-1402', 'WALKERdyd-1405', 'WALKERdyd-1408', 'WALKERdyd-1411', 'WALKERdyd-1414', 'WALKERdyd-1602', 'WALKERdyd-1605', 'WALKERdyd-1608', 'WALKERdyd-1611', 'WALKERdyd-1614', 'WALKERdyd-1802', 'WALKERdyd-1805', 'WALKERdyd-1808', 'WALKERdyd-1811', 'WALKERdyd-1814']
    #head_id_list = ['WALKERdyd-1002', 'WALKERdyd-1005', 'WALKERdyd-1008', 'WALKERdyd-1011', 'WALKERdyd-1014', 'WALKERdyd-1302', 'WALKERdyd-1305', 'WALKERdyd-1308', 'WALKERdyd-1311', 'WALKERdyd-1314', 'WALKERdyd-1502', 'WALKERdyd-1505', 'WALKERdyd-1508', 'WALKERdyd-1511', 'WALKERdyd-1514', 'WALKERdyd-1702', 'WALKERdyd-1705', 'WALKERdyd-1708', 'WALKERdyd-1711', 'WALKERdyd-1714']
    #head_id_list = ['WALKERdyd-1002', 'WALKERdyd-1005', 'WALKERdyd-1008', 'WALKERdyd-1011', 'WALKERdyd-1014', 'WALKERdyd-1202', 'WALKERdyd-1205', 'WALKERdyd-1208', 'WALKERdyd-1211', 'WALKERdyd-1214', 'WALKERdyd-1402', 'WALKERdyd-1405', 'WALKERdyd-1408', 'WALKERdyd-1411', 'WALKERdyd-1414', 'WALKERdyd-1602', 'WALKERdyd-1605', 'WALKERdyd-1608', 'WALKERdyd-1611', 'WALKERdyd-1614']
    head_id_list = get_cluster_heads()
    head_ip_dict = {}
    head_ip_list = []
    # 获取簇首IP地址
    for head_id in head_id_list:
        cursor.execute("select * from bridge_ip_table where id = '%s'" % head_id)
        result = cursor.fetchone()[1]
        if result:
            head_ip_dict[head_id] = result
            head_ip_list.append(result)
            print(f"Head ID: {head_id}, IP: {result}")
        else:
            print(f"No IP found for Head ID: {head_id}")
    time.sleep(5)
    MEO_IDS = ['MEO-1', 'MEO-2', 'MEO-3', 'MEO-4', 'MEO-5', 'MEO-6', 'MEO-7', 'MEO-8']
    MEO_IPs = []
    #获取 MEO IP地址
    for meo_id in MEO_IDS:
        cursor.execute("select * from bridge_ip_table where id = '%s'" % meo_id)
        result = cursor.fetchone()[1]
        if result:
            MEO_ip = result
            MEO_IPs.append(MEO_ip)
            print(f"MEO ID: {meo_id}, IP: {result}")
        else:
            print(f"No IP found for MEO ID: {meo_id}")
    # 启动MEO
    belonged_head_id_lists = split_list(head_id_list, 3)
    #belonged_head_id_lists.pop()
    belonged_head_id_lists.pop()
    #belonged_head_id_lists[-1].append('WALKERdyd-1914')
    #belonged_head_id_lists[-2].append('WALKERdyd-1911')
    #belonged_head_id_lists[-3].append('WALKERdyd-1908')
    belonged_head_id_lists[-4].append('WALKERdyd-1814')
    k = 0
    #belonged_head_id_lists = [['WALKERdyd-1002']]
    for item in belonged_head_id_lists:
        belonged_head_ips = []
        for head_id in item:
            belonged_head_ips.append(head_ip_dict[head_id])
            thread = threading.Thread(target=enable_cluster_routing, args=(head_id,MEO_IPs[k]))
            thread.start()
        MEO_thread = threading.Thread(target=enable_cluster_routing_MEO, args=(MEO_IDS[k],belonged_head_ips))
        MEO_thread.start()
        k += 1
    time.sleep(5)
    print("head_ip_list: ", head_ip_list)
    # MEO通知簇首
    os.system("docker exec -it MEO-1 python3 head_inform.py " + " ".join(head_ip_list))
    '''with open('output.txt', 'a') as file:
        file.write(str(head_ip_list) + '\n')'''
    #name_list = ['WALKERdyd-1001','WALKERdyd-1003', 'WALKERdyd-1004', "WALKERdyd-1101", 'WALKERdyd-1102', 'WALKERdyd-1103', 'WALKERdyd-1104','WALKERdyd-1115', 'WALKERdyd-1114', 
    #             'WALKERdyd-1901', 'WALKERdyd-1902', 'WALKERdyd-1903', 'WALKERdyd-1904', 'WALKERdyd-1914', 'WALKERdyd-1915']  #非簇首节点列表
    for container in name_list:
        # 创建线程来执行 enable_cluster_routing 函数
        if container in head_id_list:
            continue
        thread = threading.Thread(target=enable_cluster_routing, args=(container,MEO_IPs[0]))
        thread.start()
        #time.sleep(0.1)
        #thread_list.append(thread)
    record_time()
    #time.sleep(30)
    #get_routing_overhead()
    time.sleep(60)
    get_routing_overhead()
    db.close()
    