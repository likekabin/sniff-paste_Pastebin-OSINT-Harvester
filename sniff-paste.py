import pymysql
import socket
import re
import configparser

debug=True


config = configparser.ConfigParser()
if(debug):
    config.read('settings.debug.ini')
else:
    config.read('settings.ini')
     
conf_mysql = config['MYSQL']

conn = pymysql.connect(conf_mysql['Host'],conf_mysql['Username'], conf_mysql['Password'],conf_mysql['TableName'])

cur = conn.cursor() # get a cursor

urlLog= open('out/pastebin-urls.txt','w')
emailLog = open('out/pastebin-emails.txt','w')
phoneLog = open('out/pastebin-phone-numbers.txt','w')
ipLog = open('out/pastebin-ips.txt','w')


results = cur.execute('select data, link  from pastes;')
for row in cur.fetchall():
    ips = re.findall(r'[0-9]+(?:\.[0-9]+){3}',str( row) )
    emails = re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+",str( row) )
    phoneNumbers= re.findall(r"\(?\b[2-9][0-9]{2}\)?[-. ]?[2-9][0-9]{2}[-. ]?[0-9]{4}\b",str(row))

    urls = re.findall('https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', str(row))

    urls += re.findall('http?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', str(row))

    print("Pastebin link: https://pastebin.com/" +row[1])

    for url in urls:
        try:
            urlLog.write(url+"\n")
            print("\tWebsite: "+url)
        except:
            print("Invalid Website")


    for email in emails:
       # response = os.system("ping -c 1 " + ip)
       # if(response == 0):
        try:
            emailLog.write(email+"\n")
            print("\tEmail: "+email)
        except:
            print("Invalid Email")

    for number in phoneNumbers:
        try:
            if( ' ' in number or '-' in number or '(' in number or ')' in number):
                phoneLog.write(number+"\n")
                print("\tPhone: "+number) 
        except:
            print("Invalid Phone Number: "+str(e))

    for ip in ips:
        try:
            socket.inet_aton(ip)
            ipLog.write(ip+"\n")
            print("\tIP: "+ip)
        except:
            print("\tInvalid IP")


    if(len(emails)>0): print("Emails Scraped: "+str(len(emails)))
    if(len(ips)>0): print("IPs Scraped: "+str(len(ips)))
    if(len(urls)>0): print("Urls Scraped: "+str(len(urls)))
    if(len(phoneNumbers)>0): print("Phone Numbers Scraped: "+str(len(phoneNumbers)))


    emails = None
    ips = None
    phoneNumbers = None
    urls= None
     
emailLog.close()
phoneLog.close()
ipLog.close()
urlLog.close()
