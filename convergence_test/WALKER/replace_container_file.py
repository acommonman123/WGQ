import os
import threading
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

if __name__ == "__main__":
    engine = create_engine('mysql+mysqlconnector://root:123456@10.101.169.132:3306/Starlink')

    query_parameter1 = text("SELECT name FROM walker_sop where starsign = 'xw'")
    query_parameter2 = text("SELECT name FROM walker_sop where starsign = 'DGM'")
    # 执行查询并将结果加载到 Pandas DataFrame
    df1 = pd.read_sql(query_parameter1, engine)
    df2 = pd.read_sql(query_parameter2, engine)
    #df = pd.concat([df1, df2], ignore_index = True)
    df = pd.read_csv('/home/wspn02/mega/WGQ/LXM/walker_dyd.csv')
    name_list = df['satellite name'].tolist()
    MEO_IDs = ['MEO-1', 'MEO-2', 'MEO-3', 'MEO-4', 'MEO-5', 'MEO-6', 'MEO-7', 'MEO-8']
    for container in name_list:
        os.system("docker cp /home/wspn02/mega/WGQ/convergence_test/socket_recv_LEO.py " + container + ":/")
        os.system("docker cp /home/wspn02/mega/WGQ/convergence_test/WALKER/incluster_inform.py " + container + ":/")
        os.system("docker cp /home/wspn02/mega/WGQ/convergence_test/WALKER/hello.py " + container + ":/")
        #os.system("docker exec -it " + container + " rm cluster_info.txt cluster_ip_list.txt cluster_neighbor.txt edge.txt edge_update.txt error_log.txt "
        #"inter_cluster_routing_update.txt need_route.txt output.txt routing_update.txt send_inter_log.txt ")
    for container in MEO_IDs:
        os.system("docker cp /home/wspn02/mega/WGQ/convergence_test/WALKER/socket_recv_MEO.py " + container + ":/")
    
    