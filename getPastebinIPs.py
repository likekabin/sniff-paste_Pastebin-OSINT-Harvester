import pymysql
import socket
import re
import config

conn = pymysql.connect(config.config["db-ip"],config.config['db-user'], config.config['db-pass'],config.config['db'])

cur = conn.cursor() # get a cursor

results = cur.execute('select data from pastes;')
iplog = open('out/pastebin-ips.txt','w')

for row in cur.fetchall():
    
    ips = re.findall( r'[0-9]+(?:\.[0-9]+){3}',str( row) )
    for ip in ips:
       # response = os.system("ping -c 1 " + ip)
       # if(response == 0):
        try:
            socket.inet_aton(ip)
            iplog.write(ip+"\n")
            print(ip)
        except:
            print("Invalid IP")
iplog.close()
