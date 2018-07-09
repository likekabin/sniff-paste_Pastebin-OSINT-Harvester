## Sniff-Paste: OSINT Pastebin Harvester

<p align="center">
    <img src="res/sniff-paste-pic.jpg" width="400"></img>
</p>

Multithreaded pastebin scraper, scrapes to mysql database. Settings for the scraper itself are in settings.ini, while settings for the harvesters are in config.py

Use run.sh  to go through the entire process of collection, logging, and harvest automatically. The scraper can be set to a paste limit of 0 to scrape indefinitely. 

There are various tools for handling the harvested lists in the util folder.

## Installation

`sudo apt install 'nmap fping'`

`pip3 install -r requirements.txt`

 - Create database pastes in mysql server
 - Fill in config.py and settings.ini

`./run.sh`

This will scrape pastebin for the latest number of pastes, then run analysis for ip addresses, emails, and phone numbers. It filters out duplicates and runs scans on some of the harvested data.
