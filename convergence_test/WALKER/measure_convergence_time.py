import os
import os
import psutil
from multiprocessing import Process, process
import pymysql
import threading
import redis
import time
import multiprocessing
from sqlalchemy import create_engine, text
import pandas as pd
import time
import random

db = pymysql.connect(host='10.101.169.132',
                     user='root',
                     password='123456'
                     )
cursor = db.cursor()
cursor.execute("use cluster_routing_database")
#container_list = ['WALKERdgm-3106', 'WALKERdgm-3306', 'WALKERdgm-3606', 'WALKERdgm-3906', 'WALKERdgm-3101', 'WALKERdgm-3301', 'WALKERdgm-3601', 'WALKERdgm-3901', 'WALKERdgm-3103', 'WALKERdgm-3303', 'WALKERdgm-3603', 'WALKERdgm-3903']
#container_list = ['WALKERXW-5106', 'WALKERXW-5306']
98
def route_monitor(container):
    os.system("docker exec -it %s ./route_monitor" %(container))

def record_time():
    current_time = time.ctime()
    lock = threading.Lock()
    lock.acquire()
    cursor.execute("select * from convergence_table")
    db.commit()
    lock.release()
    result = cursor.fetchall()
    if len(result) > 0:
        convergence_time = float(current_time) - float(result[0][0])
    else:
        convergence_time = 0.0
    lock = threading.Lock()
    lock.acquire()
    print(time.time())
    cursor.execute("insert into convergence_table values ('%s', '%f')" %(str(current_time), float(convergence_time)))
    db.commit()
    lock.release()

def get_convergence_time():
    '''temp_db = pymysql.connect(host='10.101.169.132',
                     user='root',
                     password='123456'
                     )
    temp_cursor = db.cursor()
    temp_cursor.execute("use routing_database")'''
    lock = threading.Lock()
    lock.acquire()
    cursor.execute("select * from convergence_table")
    db.commit()
    lock.release()
    result = cursor.fetchall()
    convergence_time = float(result[-1][1])
    print("收敛时间：", convergence_time)  
    db.close()  

def route_listener():
    channel = 'route_changes'
    # 连接到本地 Redis 服务器
    r = redis.Redis(host='10.200.1.61', port=6379, db=0)

    # 创建一个 Pub/Sub 对象
    pubsub = r.pubsub()
    pubsub.subscribe(channel)  # 订阅 'channel1'

    print("Waiting for messages for configuration...")

    # 接收消息
    while True:
        for message in pubsub.listen():
            if message['type'] == 'message': 
                #print(f"Received message: {message['data'].decode()}")
                record_time()
                break

def cluster_routing():
    os.system('~/anaconda3/envs/be2/bin/python /home/wspn02/mega/WGQ/convergence_test/WALKER/cluster_routing.py')

if __name__ == "__main__":
    engine = create_engine('mysql+mysqlconnector://root:123456@10.101.169.132:3306/Starlink')

    query_parameter1 = text("SELECT name FROM walker_sop where starsign = 'xw'")
    query_parameter2 = text("SELECT name FROM walker_sop where starsign = 'DGM'")
    # 执行查询并将结果加载到 Pandas DataFrame
    df1 = pd.read_sql(query_parameter1, engine)
    df2 = pd.read_sql(query_parameter2, engine)
    #df = pd.concat([df1, df2], ignore_index = True)
    df = df1
    # 获取 name 列的所有数据
    name_list = df['name'].tolist()
    
    #df = pd.read_csv('/home/wspn02/mega/WGQ/convergence_test/144/walker_144.csv')
    df = pd.read_csv('/home/wspn02/mega/WGQ/LXM/walker_dyd.csv')
    name_list = df['satellite name'].tolist()
    container_list = random.sample(name_list, 149)
    route_monitor_list = []
    for container in name_list:
        route_monitor_process = multiprocessing.Process(target=route_monitor, args=(container, ))
        route_monitor_process.start()
        route_monitor_list.append(route_monitor_process)
    cluster_routing()
    #process5 = Process(target=cluster_routing)
    #print("start routing protocol configuration")
    #process5.start()
    #process5.join()
    #record_time()
    #time.sleep(60)  #停止主进程60s，用于获取路由收敛时间
    #process5.terminate()
    #杀死容器中的路由监听命令
    '''for container in container_list:
        os.system('docker exec -it ' + container + " pkill ./route_monitor")'''
    get_convergence_time()