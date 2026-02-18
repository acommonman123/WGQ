
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

def ini_load(container, load):
    os.system(f"docker exec -it {container} bash -c 'echo {load} > /load.txt'")

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
    df = pd.concat([df1, df2], ignore_index = True)
    df = df2
    # 获取 name 列的所有数据
    name_list = df['name'].tolist()
    #df = pd.read_csv('/home/wspn02/mega/WGQ/convergence_test/144/walker_144.csv')
    #name_list = df['satellite name'].tolist()
    # 打印结果
    #name_list = ['MEO-1', 'MEO-2', 'MEO-3', 'MEO-4', 'MEO-5', 'MEO-6', 'MEO-7', 'MEO-8'] + name_list
    print(name_list)
    args = []
    # 创建进程池，批量创建容器
    for l in name_list:
        #lines.append(l)
        load = 0
        if l in ['WALKERdgm-3101', 'WALKERdgm-3201', 'WALKERdgm-4001', 'WALKERdgm-3103', 'WALKERdgm-3104', 'WALKERdgm-3111', 'WALKERdgm-3203', 'WALKERdgm-3204', 'WALKERdgm-3211', 'WALKERdgm-4003', 'WALKERdgm-4004', 'WALKERdgm-4011']:
            load = 0.9
        args.append((l, load))
        #thread = threading.Thread(target = create_docker, args=(l,))
        #thread.start()
        docker_num = docker_num + 1
        #thread_list.append(thread)
    for t in args:
        thread = threading.Thread(target = ini_load, args=(t[0], t[1],))
        thread.start()
        thread_list.append(thread)
    for t in thread_list:
        t.join()
    