import os
import pymysql
import multiprocessing
import subprocess
container=subprocess.Popen("docker ps -q",universal_newlines=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out,errs=container.communicate()
container.stdin.close()
containers = out.split('\n')
rm_container = ""
process_list = []
db = pymysql.connect(host='10.101.169.132',
                     user='root',
                     password='123456'
                     )
cursor = db.cursor()
cursor.execute("use cluster_routing_database")
def stop_container():
    os.system("docker stop " + rm_container)
    print(rm_container)


for rm_container in containers:
    process = multiprocessing.Process(target=stop_container)
    process.start()
    process_list.append(process)
for p in process_list:
    p.join()

#os.system("ovs-vsctl del-br brConn")
os.system("docker rm $(docker ps -qa)")
#os.system("docker start $(docker ps -qa)")
cursor.execute("delete from ip_table")
cursor.execute("delete from link_table")
cursor.execute("delete from bridge_ip_table")
cursor.execute("delete from convergence_table")
cursor.execute("delete from overhead_table")
cursor.execute("delete from cluster_result_table")
db.commit()                                         
db.close()
