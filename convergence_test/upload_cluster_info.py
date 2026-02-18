from unittest import result
import pymysql
import pandas as pd


db = pymysql.connect(host='10.101.169.132',
                     user='root',
                     password='123456'
                     )
cursor = db.cursor()
cursor.execute("use cluster_routing_database")

result = []
def update_cluster_result():
    # 打开并读取文件
    with open('/home/wspn02/mega/WGQ/convergence_test/cluster_result.txt', 'r', encoding='utf-8') as file:
        for line in file:
            # 去除行尾的换行符，并按逗号分割
            parts = line.strip().split(',')
            # 将分割后的列表添加到结果中
            cursor.execute("insert into cluster_result_table values ('%s', '%s', '%s', '%s')" %(parts[0], parts[1], parts[2], parts[3]))
            db.commit()

update_cluster_result()