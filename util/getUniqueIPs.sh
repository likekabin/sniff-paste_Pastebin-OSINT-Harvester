awk '!seen[$0]++' ../out/pastebin-ips.txt >> ../out/unique-pastebin-ips.txt
