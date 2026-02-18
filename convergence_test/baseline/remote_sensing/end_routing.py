import threading
import os
from sqlalchemy import create_engine, text
import pandas as pd

def disable_cluster_routing(container):
    # 停止容器
    os.system('docker exec -it ' + container + ' pkill python3')
    os.system('docker exec -it ' + container + ' pkill route_monitor')

if __name__ == "__main__":
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
    
    '''dataframe = pd.read_csv('/home/wspn02/mega/WGQ/convergence_test/192/walker_192.csv')
    name_list = dataframe['satellite name'].tolist() + ['MEO']'''
    MEO_IDs = ['MEO-1', 'MEO-2', 'MEO-3', 'MEO-4', 'MEO-5', 'MEO-6', 'MEO-7', 'MEO-8']
    #df = pd.read_csv('/home/wspn02/mega/WGQ/LXM/walker_dyd.csv')
    #name_list = df['satellite name'].tolist()
    # 打印结果
    name_list = ['MEO-1', 'MEO-2', 'MEO-3', 'MEO-4', 'MEO-5', 'MEO-6', 'MEO-7', 'MEO-8'] + name_list
    print(name_list)
    thread_list = []
    for container in name_list:
        # 创建线程来执行 disable_cluster_routing 函数
        thread = threading.Thread(target=disable_cluster_routing, args=(container,))
        thread.start()
        thread_list.append(thread)
    for thread in thread_list:
        thread.join()
    for MEO_ID in MEO_IDs:
        os.system('docker exec -it ' + MEO_ID + ' rm intra_cluster_graph.txt')
        os.system('docker exec -it ' + MEO_ID + ' rm global_graph.txt')
        os.system('docker exec -it ' + MEO_ID + ' rm routing_database.txt')