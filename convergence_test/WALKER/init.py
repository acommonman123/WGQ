import threading
import os

def create_container():
    os.system("~/anaconda3/envs/be2/bin/python /home/wspn02/mega/WGQ/convergence_test/WALKER/create_container.py")

def create_link():
    os.system("~/anaconda3/envs/be2/bin/python /home/wspn02/mega/WGQ/convergence_test/WALKER/create_link.py")

#重命名容器的网络接口+
def rename():
    os.system('~/anaconda3/envs/be2/bin/python /home/wspn02/mega/WGQ/convergence_test/WALKER/rename.py')

#初始化时延

def ini_delay():
    os.system('~/anaconda3/envs/be2/bin/python /home/wspn02/mega/WGQ/convergence_test/WALKER/ini_delay.py')

if __name__ == "__main__":
    thread1 = threading.Thread(target=create_container)
    thread2 = threading.Thread(target=create_link)
    thread3 = threading.Thread(target=rename)
    thread4 = threading.Thread(target=ini_delay)
    
    thread1.start()
    thread1.join()
    thread2.start()    
    thread2.join()
    #thread3.start()
    #thread3.join()
    #thread4.start()
    #thread4.join()
    
    print("容器创建和链路创建完成")