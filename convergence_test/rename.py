#本文件用于重命名docker容器的端口，方便后续设置时延
import os
import subprocess
import threading
import pymysql
import multiprocessing
from py2neo import Graph
from datetime import datetime, timedelta
import time

link_f = open("/home/wspn02/mega/WGQ/link.txt")
docker_num = 0
network_id = 1
ip_2 = 18
ip_3 = 1
port_id = 1
line = ""
src_tar = []
db = pymysql.connect(host='10.101.169.132',
                     user='root',
                     password='123456'
                     )
cursor = db.cursor()
cursor.execute("use cluster_routing_database")
process_list = []
source_ips = []
target_ips = []
ISL_ip = ""
source_ip = ""
target_ip = ""
source_id = ""
target_id = ""
links = []

graph=Graph("neo4j://localhost:7687",auth=("neo4j","lst123456"))

#-----------------------------------------------------------------------
start_time_str = '2024-12-01_00-00-00' #仿真初始时间
end_time_str = '2024-12-01_00-00-30' #仿真结束时间
start_str='00-00-00_00-00-00' #同轨建链时间->不变
#-----------------------------------------------------------------------

start_time = datetime.strptime(start_time_str, '%Y-%m-%d_%H-%M-%S')
end_time = datetime.strptime(end_time_str, '%Y-%m-%d_%H-%M-%S')
time_slot = timedelta(seconds=10)
current_time= start_time

def read_startend_neo4j(current_time): #读取开始和结束卫星
    current_time_str = current_time.strftime('%Y-%m-%d_%H-%M-%S')
    query_1 =f"""
    MATCH (s:Satellite)-[r:start]->(t:Time {{time_slot: '{current_time_str}'}})
    RETURN s.name AS start_sat
    """
    result_start = graph.run(query_1).data()

    query_2 =f"""
    MATCH (s:Satellite)-[r:end]->(t:Time {{time_slot: '{current_time_str}'}})
    RETURN s.name AS end_sat
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

def read_link_neo4j(current_time, time_slot): #读取每个时隙的拆建链

    search_time1 = current_time
    search_time1_str = search_time1.strftime('%Y-%m-%d_%H-%M-%S')
    query=f'''MATCH (a)-[r:connected]->(b)
    WHERE r.time_slot = '{search_time1_str}'
    RETURN a.name as sat1, b.name as sat2'''
    link1 = graph.run(query).data()

    search_time2 = current_time + time_slot
    search_time2_str = search_time2.strftime('%Y-%m-%d_%H-%M-%S')
    query=f'''MATCH (a)-[r:connected]->(b)
    WHERE r.time_slot = '{search_time2_str}'
    RETURN a.name as sat1, b.name as sat2'''
    link2 = graph.run(query).data()

    # 转换列表中的字典为 frozenset
    set1 = {frozenset(item.items()) for item in link1}
    set2 = {frozenset(item.items()) for item in link2}

    # 计算新增和移除的链接
    new_links = set2 - set1  # 在 link2 中有，但 link1 中没有
    removed_links = set1 - set2  # 在 link1 中有，但 link2 中没有

    new_links = [dict(link) for link in new_links]
    removed_links = [dict(link) for link in removed_links]

    return new_links,removed_links

def set_down(src_id, target_interface):
    #print("docker exec -d " + src_id + " ip link set dev " + target_interface + " down")
    os.system("docker exec -d " + src_id + " ip link set dev " + target_interface + " down")
        
def set_name(src_id, target_interface, tar_id):
    os.system("docker exec -d " + src_id + " ip link set dev " + target_interface + " name " + "eth-" + tar_id.split('-')[1])
    #print("docker exec -d " + src_id + " ip link set dev " + target_interface + " name " + "eth-" + tar_id.split('-')[1])

def set_up(src_id, tar_id):
    os.system("docker exec -d " + src_id + " ip link set dev " + "eth-" + tar_id.split('-')[1] + " up")
    print("docker exec -d " + src_id + " ip link set dev " + "eth-" + tar_id.split('-')[1] + " up")


#重命名端口
def rename(args):
    src_id, tar_id, src_ip = args
    #更改端口名称
    with os.popen(
            "docker exec -it " + src_id +
            " ip -6 addr | grep -B 1 " + src_ip +
            "| awk -F: '{ print $2 }' | tr -d [:blank:]") as f:
        ifconfig_output = f.readline()
        target_interface = str(ifconfig_output).split("@")[0]
        #print('target_interface:', target_interface)
        #print(tar_id.split('-')[1])
        #关闭端口
        down_thread = threading.Thread(target=set_down, args=(src_id, target_interface))
        down_thread.start()
        down_thread.join()  #等待线程完成
        #重命名端口
        set_name_thread = threading.Thread(target=set_name, args=(src_id, target_interface, tar_id))
        set_name_thread.start()
        set_name_thread.join()  #等待线程完成
        #重启端口
        up_thread = threading.Thread(target=set_up, args = (src_id, tar_id))
        up_thread.start()
        up_thread.join()    #等待线程完成
        #确保重启端口
        up_thread = threading.Thread(target=set_up, args = (src_id, tar_id))
        up_thread.start()
        up_thread.join()    #等待线程完成
        os.system(f"docker exec -d {src_id} ip -6 addr add {src_ip}/64 dev eth-{tar_id.split('-')[1]}")

if __name__ == "__main__":
    #os.system("ulimit -n 2048")
    args = []
    thread_list = []

    cursor.execute("select * from link_table")  #读取链路信息
    db.commit()
    start_link = cursor.fetchall()

    for link in start_link:
        source_ip = link[4]
        source_id = link[0]
        target_ip = link[5]
        target_id = link[1]
        args.append((source_id, target_id, source_ip))
        args.append((target_id, source_id, target_ip))
        #process = multiprocessing.Process(target=rename, args=(src_tar, ISL_ip, source_ip, target_ip, network_id))
        #process.start()
        #process_list.append(process)
        #thread = threading.Thread(target=rename, args = (source_id, target_id, source_ip))
        #thread_list.append(thread)
        network_id = network_id + 1
    with multiprocessing.Pool(processes=5) as pool:
        pool.map(rename, args)
    time.sleep(5)
    db.close()
    '''for thread in thread_list:
        thread.start()
    for thread in thread_list:
        thread.join()'''
    #os.system("python3 /home/wspn02/mega/WGQ/conf_ospf.py")
