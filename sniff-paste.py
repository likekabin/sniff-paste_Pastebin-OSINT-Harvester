import pymysql
import socket
import re
import configparser

debug=False


config = configparser.ConfigParser()
if(debug):
    config.read('settings.debug.ini')
else:
    config.read('settings.ini')
     
conf_mysql = config['MYSQL']

conn = pymysql.connect(conf_mysql['Host'],conf_mysql['Username'], conf_mysql['Password'],conf_mysql['TableName'])

cur = conn.cursor() # get a cursor

results = cur.execute('select data from pastes;')
emailLog = open('out/pastebin-emails.txt','w')
phoneLog = open('out/pastebin-phone-numbers.txt','w')
ipLog = open('out/pastebin-ips.txt','w')

for row in cur.fetchall():
    ips = re.findall(r'[0-9]+(?:\.[0-9]+){3}',str( row) )
    emails = re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+",str( row) )
    phoneNumbers= re.findall(r"\(?\b[2-9][0-9]{2}\)?[-. ]?[2-9][0-9]{2}[-. ]?[0-9]{4}\b",str(row))

    for email in emails:
       # response = os.system("ping -c 1 " + ip)
       # if(response == 0):
        try:
            emailLog.write(email+"\n")
            print(email)
        except:
            print("Invalid Email")

    for number in phoneNumbers:
        try:
            if( ' ' in number or '-' in number or '(' in number or ')' in number):
                phoneLog.write(number+"\n")
                print("Phone: "+number) 
        except:
            print("Invalid Phone Number: "+str(e))

    for ip in ips:
        try:
            socket.inet_aton(ip)
            ipLog.write(ip+"\n")
            print("IP: "+ip)
        except:
            print("Invalid IP")
     
emailLog.close()
phoneLog.close()
ipLog.close
