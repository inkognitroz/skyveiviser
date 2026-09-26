# Skyveiviser 0.4 – teststatus

Kontrollert 26. september 2026, Linux / Python 3.13.5.

- `python3 -m unittest discover -s tests -q`: **90 tester bestått**.
- `python3 evaluate.py --output evaluation.local.json`: **10/10** kontroller på det eksisterende utviklingssettet.
- `node --check web/app.js` og Python-kompilering: bestått.
- Chromium: **13 grensesnittkontroller bestått** for menyrekkefølge, ettklikks avtaleoversikt, CIPS, VM, kundesøk, naturlig Asker-spørsmål, Bærum, Via-verdier, ukjent/manglende virksomhet, gamle resultater, mobilbredde og JavaScript-feil.

Nettleserens direkte tilgang til localhost var blokkert av testmiljøets policy. Grensesnittprøven brukte derfor simulert `fetch` som ble koblet til ekte lokale HTTP-kall fra Python. Dette er ikke en full prøve av nettleserens native nettverk. Ingen virkelig LLM eller betalt API ble kjørt.

De nye oppslagene trenger ikke en modell. Egne regresjonstester avviser enhver modellkontakt ved tilslutning, avtaleoversikt og VM-status. Asker kommune gjengis med sju Nei som i tabellen; Bærum har egne Ja/Nei-verdier; VM regnes ikke som inngått selv når kundelisten sier Ja. Flere navnetreff beholdes, og manglende virksomhetsnavn gir et oppklaringsspørsmål.

Oktober 2026 er tydelig merket som foreløpig planopplysning, ikke offentlig kildebekreftet tildeling. Kundelistens 620 rå rader er uendret. VM-informasjonen ligger i `vm.json`; den er inkludert i kildeversjonens fingeravtrykk og delingspakken.

GitHub-nedlastingen er nå det automatisk genererte kildearkivet fra main. Den inneholder programfiler, tester og dokumentasjon fra samme versjon. Oppstart fra mappen skyveiviser-main er kontrollert lokalt; den eksterne nedlastingstjenesten er ikke en del av programtestene.

Dette er teknisk verifikasjon av en lokal demonstrator, ikke en generell kvalitets-, avrops- eller produksjonsgodkjenning. Kontroller svar og datert kildegrunnlag ved bruk.
