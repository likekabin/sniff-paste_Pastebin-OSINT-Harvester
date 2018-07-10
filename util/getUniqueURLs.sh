awk '!seen[$0]++' ../out/pastebin-urls.txt >> ../out/unique-pastebin-urls.txt
