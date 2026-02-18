#本文件用于初始化时延
import os
import subprocess
import pymysql
import multiprocessing
from py2neo import Graph
from datetime import datetime, timedelta
import time
import threading
import redis
from sqlalchemy import create_engine, text, inspect
import pandas as pd

graph=Graph("neo4j://localhost:7687",auth=("neo4j","lst123456"))

network_id = 1
ip_2 = 0
ip_3 = 0
port_id = 1
line = ""
src_tar = []
process_list = []

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

def publisher():
    # 连接到本地 Redis 服务器
    r = redis.Redis(host='10.101.169.132', port=6379, db=0)

    # 发送消息到 Redis 的 'channel1'
    message = "Hello, Redis!"
    print(f"Publishing: {message}")
    r.publish('initing_be', message)

def delay(delay, container, interface):
    os.system("docker exec -d %s tc qdisc add dev eth-%s root handle 1: tbf rate 1gbit burst 1mbit latency 50ms" %(container, interface))
    os.system("docker exec -d %s tc qdisc add dev eth-%s parent 1:1 handle 10: netem delay %sms" %(container, interface, delay))
    print("docker exec -d %s tc qdisc add dev eth-%s parent 1:1 handle 10: netem delay %sms" %(container, interface, delay))


if __name__ == "__main__":
    engine = create_engine('mysql+mysqlconnector://root:123456@10.101.169.132:3306/Starlink')
    start_time_str, end_time_str, time_slot_second= read_character('test')
    start_time = datetime.strptime(start_time_str, '%Y-%m-%d_%H-%M-%S')
    end_time = datetime.strptime(end_time_str, '%Y-%m-%d_%H-%M-%S')
    time_slot = timedelta(seconds=10)
    current_time= start_time
    os.system("ulimit -n")
    query1=f'''MATCH (a)-[r:xwlink]->(b) 
    WHERE r.time_slot = '{start_str}'
    RETURN a.name as sat1, b.name as sat2, r.delay as delay
    '''
    start_link1 = graph.run(query1).data() #传输星座的建链

    query2=f'''MATCH (a)-[r:dgmlink]->(b)
    WHERE r.time_slot = '{start_time_str}'
    RETURN a.name as sat1, b.name as sat2, r.delay as delay
    '''
    start_link2 = graph.run(query2).data() #传感星座的建链"""

    start_link = start_link1#初始拓扑

    thread_list = []
    df = pd.read_csv('/home/wspn02/mega/WGQ/LXM/link_dyd.csv')
    sat_list = df[['source', 'target', 'delay']].rename(columns={'source': 'sat1', 'target': 'sat2', 'delay': 'delay'})
    #start_link = sat_list.to_dict('records')
    for link in start_link:
        src_tar = link
        delay_thread = threading.Thread(target = delay, args = (src_tar['delay'], src_tar['sat1'], src_tar['sat2'].split('-')[1]))
        thread_list.append(delay_thread)
    for delay_thread in thread_list:
        delay_thread.start()
    for delay_thread in thread_list:
        delay_thread.join()
    
    publisher()
    #os.system("python3 /home/wspn02/mega/WGQ/update.py")
    df = pd.read_csv('/home/wspn02/mega/WGQ/LXM/walker_dyd.csv')
    name_list = df['satellite name'].tolist()
    # 打印结果
    name_list = ['MEO-1', 'MEO-2', 'MEO-3', 'MEO-4', 'MEO-5', 'MEO-6', 'MEO-7', 'MEO-8'] + name_list
    for container in name_list:
        os.system("docker exec -d %s tc qdisc add dev eth0 root handle 1: tbf rate 100kbit burst 1mbit latency 50ms" %(container))


