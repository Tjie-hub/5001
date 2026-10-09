#!/bin/bash
# KSEI monthly Balancepos (holding composition by investor type, local/foreign). Public archive.
# Last trading day of each month: try day 31 down to 18, keep the first real zip.
cd "$(dirname "$0")"
for y in $(seq 2008 2026); do for m in 01 02 03 04 05 06 07 08 09 10 11 12; do
  [ "$y$m" -gt 202609 ] && continue
  ls BalanceposEfek$y$m??.zip >/dev/null 2>&1 && continue
  got=""
  for d in 31 30 29 28 27 26 25 24 23 22 21 20 19 18; do
    f=BalanceposEfek$y$m$d.zip
    curl -s -f -A "Mozilla/5.0" "https://web.ksei.co.id/Download/$f" -o "$f.part" && [ $(stat -c%s "$f.part") -gt 5000 ] && unzip -tq "$f.part" >/dev/null 2>&1 && { mv "$f.part" "$f"; got=$f; break; }
    rm -f "$f.part"; sleep 0.3
  done
  echo "$y-$m ${got:-MISSING}"
done; done
