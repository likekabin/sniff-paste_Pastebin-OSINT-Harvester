import pymysql
import socket
import re

debug=False

if (debug):
    import configdebug as config
else:
    import config

conn = pymysql.connect(config.config["db-ip"],config.config['db-user'], config.config['db-pass'],config.config['db'])

cur = conn.cursor() # get a cursor

results = cur.execute('select data from pastes;')
emailLog = open('out/pastebin-emails.txt','w')
ipLog = open('out/pastebin-ips.txt','w')

for row in cur.fetchall():
    
    ips = re.findall(r'[0-9]+(?:\.[0-9]+){3}',str( row) )
    emails = re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+",str( row) )
    for email in emails:
       # response = os.system("ping -c 1 " + ip)
       # if(response == 0):
        try:
            emailLog.write(email+"\n")
            print(email)
        except:
            print("Invalid Email")

    for ip in ips:
        try:
            socket.inet_aton(ip)
            ipLog.write(ip+"\n")
            print("IP: "+ip)
        except:
            print("Invalid IP")

emailLog.close()
ipLog.close
