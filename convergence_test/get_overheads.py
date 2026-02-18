import subprocess
import re
from sqlalchemy import create_engine, text
import pandas as pd
import pymysql
import threading

db = pymysql.connect(host='10.101.169.132',
                     user='root',
                     password='123456'
                     )
cursor = db.cursor()
cursor.execute("use cluster_routing_database")
# 获取 ifconfig 输出
def get_ifconfig_output(container):
    process = subprocess.Popen(f"docker exec -i {container} ifconfig",universal_newlines=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, errs = process.communicate() 
    # 提取并求和
    rx_bytes_list = re.findall(r'RX bytes:(\d+)', out)
    total_rx_bytes = sum(int(b) for b in rx_bytes_list)
    return total_rx_bytes


def get_routing_overhead():
    lock = threading.Lock()
    lock.acquire()
    cursor.execute("select * from overhead_table")
    db.commit()
    lock.release()
    result = cursor.fetchall()
    ini_overhead = int(result[-3][0])
    final_overhead = int(result[-1][0])
    print("Routing Overhead: ", (final_overhead - ini_overhead)/(1024*1024), "MB")

container_name = "WALKERdgm-3101"  # 替换为你的容器名称
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
get_routing_overhead()