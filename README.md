## Sniff-Paste: OSINT Pastebin Harvester

<p align="center">
    <img src="res/sniff-paste-pic.jpg" width="400"></img>
</p>

Multithreaded pastebin scraper, scrapes to mysql database, then reads pastes for noteworthy information.

Use run.sh  to go through the entire process of collection, logging, and harvest automatically. The scraper can be set to a paste limit of 0 to scrape indefinitely. If scraped indefinitely, press ctrl + c to stop scraping and start analysis. 

There are various tools for handling the harvested lists in the util folder.

## Installation

`sudo apt install libxslt-dev python3-lxml nmap xsltproc fping mysql-server`

`pip3 install -r requirements.txt`

 - Create database named pastes in mysql server
 - Fill in settings.ini

`./run.sh`

This will scrape pastebin for the latest number of pastes, then run analysis for ip addresses, emails, and phone numbers. It filters out duplicates and runs scans on some of the harvested data.
