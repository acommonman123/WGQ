#本文件用于创建docker容器，每个容器对应一个节点
from concurrent.futures import thread
import multiprocessing.pool
import os
import subprocess
import pymysql
import redis
import multiprocessing
from sqlalchemy import create_engine, text
import pandas as pd
import time
import threading
import psutil
import re


#f = open('/home/wspn05/WGQ/192/walker_192.csv')
#link_f = open("link.txt")
routing_protocol = ["ospfd", "bgpd"]
docker_num = 0
ip_2 = 18
ip_3 = 1
network_id = 1
port_id = 1
line = ""
src_tar = []
thread_list = []
db = pymysql.connect(host='10.101.169.132',
                     user='root',
                     password='123456'
                     )
cursor = db.cursor()
cursor.execute("use routing_database")

def subscriber():
    # 连接到本地 Redis 服务器
    r = redis.Redis(host='10.101.169.132', port=6379, db=0)

    # 创建一个 Pub/Sub 对象
    pubsub = r.pubsub()
    pubsub.subscribe('initing_vue')  # 订阅 'channel1'

    print("Waiting for messages...")

    # 接收消息
    for message in pubsub.listen():
        # print(message)
        # 订阅成功时返回的系统信息
        # {'type': 'subscribe', 'pattern': None, 'channel': b'channel1', 'data': 1}

        # 消息队列，注意'type' 'channel' 'data'字段
        # 'data'值为String，注意读取格式
        # {'type': 'message', 'pattern': None, 'channel': b'channel1', 'data': b'Hello, Redis!'}
        # {'type': 'message', 'pattern': None, 'channel': b'channel1', 'data': b'1'}

        if message['type'] == 'message': 
            print(f"Received message: {message['data'].decode()}")
            break

def create_container(container):
    #os.system("docker run -d --privileged -v /home/wspn02/mega/WGQ/convergence_test:/files --name  " + container + " cluster_router_dgm_1")
    #os.system("docker run -d --privileged -v /home/wspn02/mega/WGQ/convergence_test:/files --name  " + container + " cluster_router_walker:1.0")
    os.system("docker run -d --privileged -v /home/wspn02/mega/WGQ/convergence_test:/files --name  " + container + " cluster_router:4.0")
    os.system("docker exec -i " + container + " sysctl -w net.ipv6.conf.all.forwarding=1")

def disconnect_bridge(container):
    os.system('docker network disconnect bridge ' + container)

def enable_ospf(container):
    os.system("docker exec -it " + container + " sed -i 's/" + routing_protocol[0] + "=no/" + routing_protocol[0] + "=yes/g' /etc/frr/daemons")

def enable_bgp(container):
    os.system("docker exec -it " + container + " sed -i 's/" + routing_protocol[1] + "=no/" + routing_protocol[1] + "=yes/g' /etc/frr/daemons")

def restart_container(container):
    os.system("docker restart " + container)

def disconnect_bridge(container):
    os.system("docker network disconnect bridge " + container)

def complete_message():
    print("create container successfully")

def upload_bridge_ip(container):
    temp_db = pymysql.connect(host='10.101.169.132',
                     user='root',
                     password='123456'
                     )
    temp_cursor = temp_db.cursor()
    temp_cursor.execute("use cluster_routing_database")
    # 停止容器
    ip_addr_output = subprocess.check_output(['docker', 'exec', '-i', container, 'ip', '-6', 'addr'], text=True)
    ip_addresses = re.findall(r'inet6\s+([0-9a-fA-F:]+)(?:/\d+)?', ip_addr_output)
    #ip_addresses = [ip for ip in ip_addresses if not ip.startswith(('2001:db8', 'fe80::'))]  # 过滤掉特定的IPv6地址
    bridge_ip = ip_addresses[1] # 源IPv6地址
    lock = threading.Lock()
    lock.acquire()
    temp_cursor.execute("insert into bridge_ip_table values ('%s', '%s')" %(container, bridge_ip))
    temp_db.commit()
    lock.release()
    temp_db.close()

def create_docker(line):
    if docker_num < 900:
        #创建容器
        create_thread = threading.Thread(target=create_container, args=(line.split()[0], ))
        create_thread.start()
        create_thread.join()
        #上传bridge_ip
        upload_thread = threading.Thread(target=upload_bridge_ip, args=(line.split()[0], ))
        upload_thread.start()
        upload_thread.join()
        #os.system('docker network disconnect bridge ' + line.split()[0])
        '''#断开与bridge网桥的连接
        enable_thread = threading.Thread(target=disconnect_bridge, args=(line.split()[0], ))
        enable_thread.start()
        enable_thread.join()'''
        '''#启用ospf
        enable_thread = threading.Thread(target=enable_ospf, args=(line.split()[0], ))
        enable_thread.start()
        enable_thread.join()
        enable_thread = threading.Thread(target=enable_ospf, args=(line.split()[0], ))
        enable_thread.start()
        enable_thread.join()
        #启用bgp
        enable_thread = threading.Thread(target=enable_bgp, args=(line.split()[0], ))
        enable_thread.start()
        enable_thread.join()
        #time.sleep(0.1)
        #os.system("docker exec -it " + line.split()[0] + " /etc/init.d/frr restart")
        #重启容器
        restart_thread = threading.Thread(target=restart_container, args=(line.split()[0], ))
        restart_thread.start()
        restart_thread.join()
        #一个冗余线程，确保前面的所有步骤都已执行
        restart_thread = threading.Thread(target=complete_message, args=())
        restart_thread.start()
        restart_thread.join()'''
    else:
        os.system("docker run -d --privileged --name " + line.split()[0] + " cluster_router:1.1")
        #os.system('docker network disconnect bridge ' + line.split()[0])
        os.system("docker exec -it " + line.split()[0] + " sed -i 's/" + routing_protocol + "=no/" + routing_protocol + "=yes/g' /etc/frr/daemons")
        time.sleep(0.1)
        os.system("docker exec -it " + line.split()[0] + " /etc/init.d/frr restart")
        os.system("docker restart " + line.split()[0])

def monitor_resource():
    time = 0
    while is_finished == False:
        cpu_usage = psutil.cpu_percent(interval=1)
        print(f"CPU Usage: {cpu_usage}%")
        memory = psutil.virtual_memory()
        print(f"Memory Usage: {memory.percent}%")
        lock = threading.Lock()
        lock.acquire()
        cursor.execute("insert into resource_table values (%d, %f, %f, '%s')" %(time, cpu_usage, memory.percent, "create_container"))
        db.commit()
        lock.release()
        time = time + 1

if __name__ == "__main__":
    #subscriber()
    is_finished = False
    #monitor_process = multiprocessing.Process(target=monitor_resource)
    #monitor_process.start()
    start_time = time.time()
    lines = []
    #pool = multiprocessing.pool(Processes=10)
    engine = create_engine('mysql+mysqlconnector://root:123456@10.101.169.132:3306/Starlink')

    query_parameter1 = text("SELECT name FROM walker_sop where starsign = 'xw'")
    query_parameter2 = text("SELECT name FROM walker_sop where starsign = 'DGM'")
    # 执行查询并将结果加载到 Pandas DataFrame
    df1 = pd.read_sql(query_parameter1, engine)
    df2 = pd.read_sql(query_parameter2, engine)
    #df = pd.concat([df1, df2], ignore_index = True)
    df = df2
    # 获取 name 列的所有数据
    name_list = df['name'].tolist()
    df = pd.read_csv('/home/wspn02/mega/WGQ/LXM/walker_dyd.csv')
    name_list = df['satellite name'].tolist()
    # 打印结果
    name_list = ['MEO-1', 'MEO-2', 'MEO-3', 'MEO-4', 'MEO-5', 'MEO-6', 'MEO-7', 'MEO-8'] + name_list
    print(name_list)
    args = []
    # 创建进程池，批量创建容器
    for l in name_list:
        #lines.append(l)
        args.append((l))
        #thread = threading.Thread(target = create_docker, args=(l,))
        #thread.start()
        docker_num = docker_num + 1
        #thread_list.append(thread)
    #pool.map(create_docker, lines)
    '''for t in thread_list:
        t.join()'''
    with multiprocessing.Pool(processes=8) as pool:
        pool.map(create_docker, args)
    #f.close()
    end_time = time.time()
    creating_container_time = end_time - start_time 
    print("创建容器所需时间为：", creating_container_time)
    lock = threading.Lock()
    lock.acquire()
    cursor.execute("insert into time_table values ('%s', %f)" % ("creating_container_time", creating_container_time))
    db.commit()
    lock.release()
    db.close()
    is_finished = True
    #monitor_process.terminate()
    #monitor_process.join()
    #os.system("python3 /home/wspn02/mega/WGQ/create_link.py")

