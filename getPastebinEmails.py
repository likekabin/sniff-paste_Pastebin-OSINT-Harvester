import pymysql
import socket
import re
import config

conn = pymysql.connect(config.config["db-ip"],config.config['db-user'], config.config['db-pass'],config.config['db'])

cur = conn.cursor() # get a cursor

results = cur.execute('select data from pastes;')
emailLog = open('out/pastebin-emails.txt','w')

for row in cur.fetchall():
    
    emails = re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+",str( row) )
    for email in emails:
       # response = os.system("ping -c 1 " + ip)
       # if(response == 0):
        try:
            emailLog.write(email+"\n")
            print(email)
        except:
            print("Invalid IP")
emailLog.close()
