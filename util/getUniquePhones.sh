awk '!seen[$0]++' ../out/pastebin-phone-numbers.txt >> ../out/unique-phone-numbers.txt
