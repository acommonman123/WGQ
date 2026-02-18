import subprocess
import pymysql
import pandas as pd
from sqlalchemy import create_engine, text

db = pymysql.connect(host='10.101.169.132',
                     user='root',
                     password='123456'
                     )
cursor = db.cursor()
cursor.execute("use routing_database")

def get_route_count(container):
    # 使用 subprocess 调用系统命令
    process = subprocess.Popen(f"docker exec -i {container} ip -6 route",universal_newlines=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, errs = process.communicate()   
    #print(out)
    # 获取路由表的输出，并按行分割
    routes = out.split('\n')
    for i in range(len(routes)-1, -1, -1):
        if not routes[i].startswith('fd00'):
            del routes[i]
        else:
            break
    for i in range(len(routes)):
        if not routes[i].startswith('fd00'):
            del routes[i]
        else:
            break
    #print("当前路由表:",routes)
    # 返回路由条数
    return len(routes)

query_parameter1 = text("SELECT name FROM walker_sop where starsign = 'xw'")
query_parameter2 = text("SELECT name FROM walker_sop where starsign = 'DGM'")
engine = create_engine('mysql+mysqlconnector://root:123456@10.101.169.132:3306/Starlink')
# 执行查询并将结果加载到 Pandas DataFrame
df1 = pd.read_sql(query_parameter1, engine)
df2 = pd.read_sql(query_parameter2, engine)
#df = pd.concat([df1, df2], ignore_index = True)
df = df2
name_list = df['name'].tolist()

#df = pd.read_csv('/home/wspn02/mega/WGQ/convergence_test/144/walker_144.csv')
#name_list = df['satellite name'].tolist()
for name in name_list:
# 获取路由表的条数
    route_count = get_route_count(name)
    print(f"{name} 的路由表的条数: {route_count}")