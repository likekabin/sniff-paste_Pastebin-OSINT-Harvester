## Sniff-Paste: OSINT Pastebin Harvester

<p align="center">
    <img src="res/sniff-paste-pic.jpg" width="400"></img>
</p>

Multithreaded pastebin scraper, scrapes to mysql database, then reads pastes for noteworthy information.

Use sniff-paste.py  to go through the entire process of collection, logging, and harvest automatically. The scraper can be set to a paste limit of 0 to scrape indefinitely. If scraped indefinitely, press ctrl + c to stop scraping, any useful information will be in the database, along with a link back to the original paste it was found in.


## Installation

`sudo apt install libxslt-dev python3-lxml python3-nmap xsltproc mysql-server`

`pip3 install -r requirements.txt`

 - Create database named `sniff_paste` in mysql server
 - Fill in settings.ini

`python3 sniff-paste.py`

This will scrape pastebin for the latest number of pastes, then run analysis for ip addresses, emails, and phone numbers. It filters out duplicates and runs scans on some of the harvested data.

## Database Structure 
- `sniff_paste` -- root db
	- `pastes` -- stores paste with full text, date, link, title, and language
	- `emails` -- stores emails with extension to paste
	- `links` -- stores urls with extension to paste
	- `ip` -- stores ip with connectivity and extension to paste
	- `phones` -- stores phone unmbers with extension to paste
	- `secrets` -- stores secret type with extension to paste
	- `ports` -- stores port scan info (port, status, service, version, ip)
	- `cryptos` -- stores cryptocurrency findings with extension to paste


**Note**

- Please contribute! If there's an error let me know -- even better if you can fix it :)
	- Regex Contributions would be very helpful, and should be pretty easy to add!
- Please don't use this project maliciously, it is meant to be an analysis tool
