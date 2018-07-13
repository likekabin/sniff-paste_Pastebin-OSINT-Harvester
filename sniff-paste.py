#!/usr/bin/env python3
import json

import logging
import socket
import logging.handlers
import os
import sys
import threading
import time
from datetime import datetime
from os import path
import re
import requests
from lxml import html

import nmap

import configparser
import queue
from colorlog import ColoredFormatter

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.dialects.mysql import LONGTEXT


debug = False

IPStack = []

nmapFilter= ["127.0.0.1","192.168.1.1","192.168.0.1","0.0.0.0","255.255.255.255","10.0.0.1","10.0.0.0",'192.168.1.256']
secretRegexes = {
    "Slack Token": "(xox[p|b|o|a]-[0-9]{12}-[0-9]{12}-[0-9]{12}-[a-z0-9]{32})",
    "RSA private key": "-----BEGIN RSA PRIVATE KEY-----",
    "SSH (OPENSSH) private key": "-----BEGIN OPENSSH PRIVATE KEY-----",
    "SSH (DSA) private key": "-----BEGIN DSA PRIVATE KEY-----",
    "SSH (EC) private key": "-----BEGIN EC PRIVATE KEY-----",
    "PGP private key block": "-----BEGIN PGP PRIVATE KEY BLOCK-----",
    "Facebook Oauth": "[f|F][a|A][c|C][e|E][b|B][o|O][o|O][k|K].*['|\"][0-9a-f]{32}['|\"]",
    "Twitter Oauth": "[t|T][w|W][i|I][t|T][t|T][e|E][r|R].*['|\"][0-9a-zA-Z]{35,44}['|\"]",
    "GitHub": "[g|G][i|I][t|T][h|H][u|U][b|B].*[['|\"]0-9a-zA-Z]{35,40}['|\"]",
    "Google Oauth": "(\"client_secret\":\"[a-zA-Z0-9-_]{24}\")",
    "AWS API Key": "AKIA[0-9A-Z]{16}",
    "Heroku API Key": "[h|H][e|E][r|R][o|O][k|K][u|U].*[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}",
    "Generic Secret": "[s|S][e|E][c|C][r|R][e|E][t|T].*['|\"][0-9a-zA-Z]{32,45}['|\"]"
}

cryptoRegexes={
    "bitcoin-address" : "[13][a-km-zA-HJ-NP-Z1-9]{25,34}" ,
    "bitcoin-uri" : "bitcoin:([13][a-km-zA-HJ-NP-Z1-9]{25,34})" ,
    "bitcoin-xpub-key" : "(xpub[a-km-zA-HJ-NP-Z1-9]{100,108})(\\?c=\\d*&h=bip\\d{2,3})?" ,
    "testnet-address" : "[mn2][a-km-zA-HJ-NP-Z1-9]{25,34}" ,
    "testnet-tpub-key": "(tpub[a-km-zA-HJ-NP-Z1-9]{100,108})(\\?c=\\d*&h=bip\\d{2,3})?" ,
    "testnet-uri" : "bitcoin:([mn2][a-km-zA-HJ-NP-Z1-9]{25,34})",
    "monero-address": "(?:^4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}$)",
    "ethereum-address": "(?:^0x[a-fA-F0-9]{40}$)",
    "litecoin-address":"(?:^[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}$)",
    "bitcoin-cash-address":"(?:^[13][a-km-zA-HJ-NP-Z1-9]{33}$)",
    "dash-address":"(?:^X[1-9A-HJ-NP-Za-km-z]{33}$)",
    "ripple-address":"(?:^r[0-9a-zA-Z]{33}$)",
    "neo-address":"(?:^A[0-9a-zA-Z]{33}$)",
    "dogecoin-address":"(?:^D{1}[5-9A-HJ-NP-U]{1}[1-9A-HJ-NP-Za-km-z]{32}$)"
}

class PasteDBConnector(object):
    supported = ('MYSQL')

    def __init__(self, db, **kwargs):
        try:
            self.logger = logging.getLogger('pastebin-scraper')
            from sqlalchemy.ext.declarative import declarative_base
        except ImportError:
            self.logger.error('SQLAlchemy import failed. Make sure the SQLAlchemy Python library '
                              'is installed! To check your existing installation run: '
                              'python3 -c "import sqlalchemy;print(sqlalchemy.__version__)"')
        self.db = db
        self.Base = declarative_base()
        self.engine = self._get_db_engine(**kwargs)
        self.session = self._get_db_session(self.engine)

        #Create tables for credentials
        self.paste_model = self._get_paste_model(self.Base, **kwargs)
        self.email_model = self._get_email_model(self.Base)
        self.link_model = self._get_link_model(self.Base)
        self.ip_model = self._get_ip_model(self.Base)
        self.phone_model = self._get_phone_model(self.Base)
        self.secret_model = self._get_secret_model(self.Base)
        self.crypto_model = self._get_crypto_model(self.Base)
        self.port_model = self._get_port_model(self.Base)
        self.Base.metadata.create_all(self.engine)

        #Nmap Worker
            
        nmapper = threading.Thread(target=self._scan_network)
        nmapper.setDaemon(True)
        nmapper.start()

    def _get_db_engine(self, **kwargs):
        from sqlalchemy import create_engine

        if self.db == 'MYSQL':
            # use the mysql-python connector
            location = 'mysql+pymysql://'
            location += '{username}:{password}@{host}:{port}'.format(
                host=kwargs.pop('host'),
                port=kwargs.pop('port'),
                username=kwargs.pop('username'),
                password=kwargs.pop('password'),
            )
            location += '/{table_name}?charset={charset}'.format(
                table_name=kwargs.pop('table_name'),
                charset='utf8'
            )
            
            self.logger.info('Using MySQL')
            return create_engine(location)
        
    def _get_db_session(self, engine):
        from sqlalchemy.orm import sessionmaker
        return sessionmaker(bind=engine)()

    def _get_paste_model(self, base, **kwargs):
        class Paste(base):
            __tablename__ = "pastes"

            id = Column(Integer, primary_key=True)
            name = Column('name', String(60))
            lang = Column('language', String(30))
            link = Column('link', String(28))  # Assuming format http://pastebin.com/XXXXXXXX
            date = Column('date', DateTime())
            
            data = Column('data', LONGTEXT(charset='utf8'))
      
            def __repr__(self):
                return "<Paste(id=%s, name='%s', lang='%s', link='%s', date='%s', data='%s')" %\
                       (self.id,
                        self.name,
                        self.lang,
                        self.link,
                        str(self.date),
                        self.data[:10])
        return Paste

    def _get_email_model(self, base):
        class Email(base):
            __tablename__ = "emails"
            id = Column(Integer, primary_key=True)
            email = Column('email', String(90))
            link = Column('link', String(28))  # Assuming format http://pastebin.com/XXXXXXXX
      
            def __repr__(self):
                return "<Email(id=%s, email='%s', link='%s')" %\
                       (self.id,
                        self.email,
                        self.link)
        return Email

    def _get_link_model(self, base):
        class Link(base):
            __tablename__ = "links"

            id = Column(Integer, primary_key=True)
            url = Column('url', String(60))
            link = Column('link', String(28))  # Assuming format http://pastebin.com/XXXXXXXX
      
            def __repr__(self):
                return "<Link(id=%s, url='%s', link='%s')" %\
                       (self.id,
                        self.url,
                        self.link)
        return Link

    def _get_phone_model(self, base):
        class Phone(base):
            __tablename__ = "phones"

            id = Column(Integer, primary_key=True)
            phone = Column('phone', String(60))
            link = Column('link', String(28))  # Assuming format http://pastebin.com/XXXXXXXX
      
            def __repr__(self):
                return "<Phone(id=%s, phone='%s', link='%s')" %\
                       (self.id,
                        self.phone,
                        self.link)
        return Phone

    def _get_secret_model(self, base):
        class Secret(base):
            __tablename__ = "secrets"

            id = Column(Integer, primary_key=True)
            secret = Column('secret', String(60))
            link = Column('link', String(28))  # Assuming format http://pastebin.com/XXXXXXXX
      
            def __repr__(self):
                return "<Secret(id=%s, secret='%s', link='%s')" %\
                       (self.id,
                        self.secret,
                        self.link)
        return Secret

    def _get_crypto_model(self, base):
        class Crypto(base):
            __tablename__ = "cryptos"

            id = Column(Integer, primary_key=True)
            genre = Column('genre', String(60))
            content = Column('content', String(60))
            link = Column('link', String(28))  # Assuming format http://pastebin.com/XXXXXXXX
      
            def __repr__(self):
                return "<Crypto(id=%s, genre='%s', content='%s', link='%s' )" %\
                       (self.id,
                        self.genre,
                        self.content,
                        self.link
                       )
        return Crypto



    def _get_port_model(self, base):
        class Port(base):
            __tablename__ = "ports"

            id = Column(Integer, primary_key=True)
            ip = Column('ip', String(60))
            port = Column('port', String(10))      
            service = Column('service', String(60))
            status = Column('status', String(40))
            version= Column('version', String(60))
            def __repr__(self):
                return "<Port(id=%s, ip='%s', port='%s', service='%s', status='%s', version='%s')" %\
                    (self.id,
                     self.ip,
                     self.port,
                     self.service,
                     self.status,
                     self.version
                    )
        return Port

    def _get_ip_model(self, base):
        class IP(base):
            __tablename__ = "ips"

            id = Column(Integer, primary_key=True)
            ip = Column('ip', String(60))
            online = Column('online', Boolean())      
            link = Column('link', String(28))  # Assuming format http://pastebin.com/XXXXXXXX
            def __repr__(self):
                return "<IP(id=%s, ip='%s', online='%s', link='%s')" %\
                       (self.id,
                        self.ip,
                        self.online,
                        self.link)
        return IP

    def harvest(self,pasteLink, data):
        
        print("Harvesting Data From: "+pasteLink)
        ips = re.findall( r'[0-9]+(?:\.[0-9]+){3}', str(data ) )
        emails = re.findall( r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", str(data ) )
        phoneNumbers= re.findall( r"\(?\b[2-9][0-9]{2}\)?[-. ]?[2-9][0-9]{2}[-. ]?[0-9]{4}\b", str(data))

        urls = re.findall( 'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', str(data))
        urls += re.findall( 'http?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', str(data))
        
        secrets = None

        
        # Remove all duplicates
        ips = list(set(ips))
        emails= list(set(emails))
        phoneNumbers = list(set(phoneNumbers))
        urls= list(set(urls))


        for finding in urls:
            url_model = self.link_model(
                url=finding,
                link=pasteLink
            )
            try:
                self.session.add(url_model)
                self.session.commit()
            except:
                print("Error: Url model not committed, session rollback")
                self.session.rollback()
            #ADD TO SQL +=url_model
 
        for finding in ips:
            #print("IP: "+finding)
            try:
                socket.inet_aton(finding)
                IPStack.append((finding, pasteLink))
            except socket.error:
                print("Invalid ip: "+finding)
                #ret = os.system("ping -o -c 2 -W 500 "+finding)
                #pingRes = ret != 0 

        for finding in emails:
            email_model = self.email_model(
                email=finding,
                link=pasteLink
            )
            try:
                self.session.add(email_model)
                self.session.commit()
            except:
                print("Error: Email model not committed, session rollback")
                self.session.rollback()

        for finding in phoneNumbers:
            try:
                if( ' ' in finding or '-' in finding or '(' in finding or ')' in finding):
                    phone_model = self.phone_model(
                        phone=finding,
                        link=pasteLink
                    )
                try:
                    self.session.add(phone_model)
                    self.session.commit()
                except:
                    print("Error: Phone model not committed, session rollback")
                    self.session.rollback()

            except:
               print("Error: Phone number submission")  

        totalSecrets= 0 
        for key, value in secretRegexes.items():
            secrets = re.findall(value, str(data))
            
            for secret in secrets:
                totalSecrets+=1
                print("\t"+key+": "+secret)
                secret_model = self.secret_model(
                    secret=key,
                    link=pasteLink
                )
                try:
                    self.session.add(secret_model)
                    self.session.commit()
                except:
                    print("Error: Secret model not committed, session rollback")
                    self.session.rollback()


        totalCryptoFindings= 0 
        for key, value in cryptoRegexes.items():
            findings = re.findall(value, str(data))
            
            for finding in findings:
                totalCryptoFindings+=1
                print("\t"+key+": "+finding)
                crypto_model = self.crypto_model(
                    genre=key,
                    content=finding,
                    link=pasteLink
                )
                try:
                    self.session.add(crypto_model)
                    self.session.commit()
                except:
                    print("Error: Crypto model not committed, session rollback")
                    self.session.rollback()



                   
        print("IPS: "+str(len(ips)))
        print("Emails: "+str(len(emails)))
        print("URLS: "+str(len(urls)))
        print("Phones: "+str(len(phoneNumbers)))
        print("Secrets: "+str(totalSecrets))
        print("Cryptos: "+str(totalCryptoFindings))
        print("\n\n")

    def add(self, paste, data):
        paste_model = self.paste_model(
            name=paste[0],
            lang=paste[1],
            link=paste[2],
            date=datetime.now(),
            data=data.content.replace(b'\\', b'\\\\').decode('unicode-escape')
        )

        #Start Harvest Here
        self.logger.debug('Harvesting From model ' + str(paste_model))
        self.harvest(paste[2], data.content.replace(b'\\', b'\\\\').decode('unicode-escape'))

        try:
            self.session.add(paste_model)
            self.session.commit()
        except:
            self.logger.error(
                'An error occurred while adding a paste to %s: %s' %
                (self.db, sys.exc_info()[0])
            )

    def _scan_network(self):
        
        nm = nmap.PortScanner()

        while True:

            if(IPStack): #Check for connectivity, parse nmap if valid

                finding, pasteLink = IPStack.pop()
                
                print("NMAP WORKER CALLED ["+finding+"]")
                print("Left on stack: " +str(len(IPStack)))
                if(finding not in nmapFilter):

                    self.logger.debug('Nmap scan on IP: ' + finding)
                    nm.scan(finding, arguments='-sV')

                    print("Nmap Scan ["+finding+"] Complete")
                    try:
                        state= nm[finding]['status']['state']
                    except:
                        state= "down"

                    if("up" in state):
                        portScan= nm[finding]['tcp']

                        self.logger.debug(finding+": up\tports: "+str(portScan))
                
                        for key, value in portScan.items():
                            print(finding+":"+str(key))

                            product= value['product']
                            ver= value['version']
                            state= value['state']
                            name= value['name']

                            try:
                 
                                print("Name: "+name+"\n\tProduct: "+product+"\n\tVersion: "+ver+"\n\tState: "+state)

                                port_model = self.port_model(
                                    ip = finding,
                                    port = key,
                                    service = product,
                                    status = state,
                                    version = ver
                                )

                                try:
                                    self.session.add(port_model)
                                    self.session.commit()
                                except:
                                    self.session.rollback()
                                    print("Error: Port Commit Issue, session rollback")
                            except Exception as e:
                                print("Exception error while pushing port model: "+str(e))

                            try:
                                ip_model = self.ip_model(
                                ip=finding,
                                online= True,
                                link=pasteLink
                                )
                                try:
                                    self.session.add(ip_model)
                                    self.session.commit()
                                except:
                                    self.session.rollback()
                                    print("Error pushing to mysql: "+ str(e))
                            except:
                                print("Error: IP Model issue")

                    else: #Else put a normal entry in for pastebin
                        self.logger.debug("IP["+finding+"] down")
                        try:
                            ip_model = self.ip_model(
                                ip=finding,
                                online= False,
                                link=pasteLink
                            )
                            try:
                                self.session.add(ip_model)
                                self.session.commit()
                            except:
                                self.session.rollback()
                                print("Error: IP Commit Issue, session rollback")

                        except Exception as e:
                            print("Error pushing to mysql: "+ str(e))                    

        else: #Else put a nmap filtered kentry for pastebin
            self.logger.debug("IP["+finding+"] is a filtered address")
            try:
                ip_model = self.ip_model(
                    ip=finding,
                    online= False,
                    link=pasteLink
                )
                try:
                    self.session.add(ip_model)
                    self.session.commit()
                except:
                    self.session.rollback()
                    print("Error: IP Commit Issue, session rollback")

            except Exception as e:
                print("Error pushing to mysql: "+ str(e))                    



class PastebinScraper(object):
    def __init__(self):
        # Read and split config
        self.config = configparser.ConfigParser()
        if(debug):
            self.config.read('settings.debug.ini')
        else:
            self.config.read('settings.ini')

        self.conf_general = self.config['GENERAL']
        self.conf_logging = self.config['LOGGING']
        self.conf_stdout = self.config['STDOUT']
        self.conf_mysql = self.config['MYSQL']

        # Internals
        self.unlimited_pastes = self.conf_general.getint('PasteLimit') == 0
        self.pastes = queue.Queue(maxsize=8)
        self.pastes_seen = set()

        # Init the logger
        self.logger = logging.getLogger('pastebin-scraper')
        self.logger.setLevel(logging.DEBUG)

        # Set up log rotation
        rotation = logging.handlers.RotatingFileHandler(
            filename=self.conf_logging['RotationLog'],
            maxBytes=self.conf_logging.getint('MaxRotationSize'),
            backupCount=self.conf_logging.getint('RotationBackupCount')
        )
        rotation.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s|%(levelname)-8s| %(message)s')
        rotation.setFormatter(formatter)
        self.logger.addHandler(rotation)

        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = ColoredFormatter(
            '%(log_color)s%(asctime)s|[%(levelname)-4s] %(message)s%(reset)s', '%H:%M:%S'
        )
        console.setFormatter(formatter)
        self.logger.addHandler(console)

        if not (self.conf_stdout.getboolean('Enable') or self.conf_mysql.getboolean('Enable')):
            self.logger.error('No output method specified! Please set at least one output method '
                              'in the settings.ini to \'yes\'.')
            raise RuntimeError('No output method specified!')


        # DB connectors if needed
        self.mysql_conn = None
        if self.conf_mysql.getboolean('Enable'):
            self.logger.debug('Initializing MySQL connector')
            self.mysql_conn = PasteDBConnector(
                db='MYSQL',
                host=self.conf_mysql['Host'],
                port=self.conf_mysql['Port'],
                username=self.conf_mysql['Username'],
                password=self.conf_mysql['Password'],
                table_name=self.conf_mysql['TableName']
            )
     
    def _get_paste_data(self):
        paste_limit = self.conf_general.getint('PasteLimit')
        pb_link = self.conf_general['PBLINK']
        paste_counter = 0
        self.logger.info('No scrape limit set - scraping indefinitely' if self.unlimited_pastes
                        else 'Paste limit: ' + str(paste_limit))

        while self.unlimited_pastes or (paste_counter < paste_limit):
            page = self._handle_data_download(pb_link)

            self.logger.debug('Got {} - {} from {}'.format(
                page.status_code,
                page.reason,
                pb_link
            ))
            tree = html.fromstring(page.content)
            pastes = tree.cssselect('ul.right_menu li')
            for paste in pastes:
                if not self.unlimited_pastes \
                   and (paste_counter >= paste_limit):
                    # Break for limits % 8 != 0
                    break
                name_link = paste.cssselect('a')[0]
                name = name_link.text_content().strip()
                href = name_link.get('href')[1:]  # Get rid of leading /
                data = paste.cssselect('span')[0].text_content().split('|')
                language = None
                if len(data) == 2:
                    # Got language
                    language = data[0].strip()
                paste_data = (name, language, href)
                self.logger.debug('Paste scraped: ' + str(paste_data))
                if paste_data[2] not in self.pastes_seen:
                    # New paste detected
                    self.logger.debug('Scheduling new paste:' + str(paste_data))
                    self.pastes_seen.add(paste_data[2])
                    self.pastes.put(paste_data)
                    delay = self.conf_general.getint('NewPasteCheckInterval')
                    time.sleep(delay)
                    paste_counter += 1
                    self.logger.debug('Paste counter now at ' + str(paste_counter))
                    if paste_counter % 100 == 0:
                        self.logger.info('Scheduled %d pastes' % paste_counter)



    def _download_paste(self):
        while True:
            paste = self.pastes.get()  # (name, lang, href)
            self.logger.debug('Fetching raw paste ' + paste[2])
            link = self.conf_general['PBLink'] + 'raw/' + paste[2]
            data = self._handle_data_download(link)

            self.logger.debug('Fetched {} with {} - {}'.format(
                link,
                data.status_code,
                data.reason
            ))
            if self.conf_stdout.getboolean('Enable'):
                self._write_to_stdout(paste, data)
            if self.conf_mysql.getboolean('Enable'):
                self._write_to_mysql(paste, data)

    def _handle_data_download(self, link):
        while True:
            try:
                data = requests.get(link)
            except:
                retry = self.conf_general.getint('ConnectionRetryInterval')
                self.logger.debug(
                    'Error connecting to %s: Retry in %ss, TRACE: %s' %
                    (link, retry, sys.exc_info())
                )
                self.logger.info('Connection problems - trying again in %ss' % retry)
                time.sleep(retry)
            else:
                if data.status_code == 403 and b'Pastebin.com has blocked your IP' in data.content:
                    self.logger.info('Our IP has been blocked. Trying again in an hour.')
                    time.sleep(self.conf_general.getint('IPBlockedWaitTime'))
                return data

    def _assemble_output(self, conf, paste, data):
        output = ''
        if conf.getboolean('ShowName'):
            output += 'Name: %s\n' % paste[0]
        if conf.getboolean('ShowLang'):
            output += 'Lang: %s\n' % paste[1]
        if conf.getboolean('ShowLink'):
            output += 'Link: %s\n' % (self.conf_general['PBLink'] + paste[2])
        if conf.getboolean('ShowData'):
            encoding = conf['DataEncoding']
            limit = conf.getint('ContentDisplayLimit')
            if limit > 0:
                output += '\n%s\n\n' % data.content.decode(encoding)[:limit]
            else:
                output += '\n%s\n\n' % data.content.decode(encoding)
        return output

    def _write_to_stdout(self, paste, data):
        output = self._assemble_output(self.conf_stdout, paste, data)
        sys.stdout.write(output)

    def _write_to_mysql(self, paste, data):
        self.mysql_conn.add(paste, data)


    def run(self):
        for i in range(self.conf_general.getint('DownloadWorkers')):
            t = threading.Thread(target=self._download_paste)
            t.setDaemon(True)
            t.start()

        s = threading.Thread(target=self._get_paste_data)
        s.start()
        s.join()


if __name__ == '__main__':
    ps = PastebinScraper()
    ps.run()
