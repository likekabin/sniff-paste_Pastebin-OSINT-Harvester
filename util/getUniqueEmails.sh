awk '!seen[$0]++' ../out/pastebin-emails.txt >> ../out/unique-pastebin-emails.txt
