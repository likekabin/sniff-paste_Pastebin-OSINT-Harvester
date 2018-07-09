echo "Scraping Pastes to database (set max limit in setttings.ini)..."
python3 scraper.py
sleep 2

echo "Harvesting Information from paste database..."
python3 sniff-paste.py
sleep 2 

cd util
echo "Getting Unique Emails..."
source getUniqueEmails.sh

echo "Getting Phone Numbers..."
source getUniquePhones.sh


echo "Getting Unique IP addresses..."
source getUniqueIPs.sh


echo "Getting Online IP addresses..."
sleep 2 
source getOnlineIPs.sh


echo "Getting Nmap Results..."
sleep 2 
source getNmapResults.sh


echo "Converting to HTML..."
sleep 2 
source generateNmapHTML.sh

