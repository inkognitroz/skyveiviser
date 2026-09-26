# Teststatus – avtale- og kundeutvidelsen

Dato: 26. september 2026. Denne leveransen utvider den lokale demonstratoren med avtaleinformasjon, avropsveiledning, spørsmål/svar og et datert kundelisteoppslag.

## Faktisk kjørt

- `python3 -m unittest discover -s tests -v`: 71 tester bestått. De opprinnelige 40 testtilfellene er beholdt; testen som krevde nøyaktig fem kilder er oppdatert til å kreve at de fem opprinnelige er beholdt og at antallet nå er 24.
- `python3 evaluate.py --output evaluation.local.json`: 10/10 gjenfinningskontroller. Spørsmålet om laveste pris er nå en positiv gjenfinning av FAQ-en som sier at leverandørprisene ikke ligger i demoen. Det er ikke en prisrangering. Det gamle kontrollsettet ga først 9/10 fordi de nye kildene også inneholder prisord.
- `python3 -m py_compile app.py engine.py customers.py evaluate.py tools/package.py`: bestått.
- `node --check web/app.js`: bestått.
- Kundelisteoppslag over ekte lokal HTTP: DFØ-organisasjonsnummer og alle sju råverdier returnert uten modell. Ukjente treff, doble navn, tomme felt, Via-oppføringer og VM-status er dekket av tester.
- Seks grensesnittkontroller i Chromium med simulerte HTTP-svar: kundetabell, sletting av tidligere svar ved feil, VM-forbehold, mobilbredde, ukjent treff og CIPS-kildesøk. Ingen JavaScript-feil observert.

## Datakontroll

620 rader fra den offentlig tilgjengelige kundetabellen er lagret, med ni felter per rad. Dataene er en avskrift, ikke en uavhengig avtaleforvalter-godkjenning. Råverdier og synlige uoverensstemmelser er bevart. Kildedato 11.11.2025 og lesedato 26.09.2026 er forskjellige og vises separat. Testene bekrefter håndtering av data, ikke at den offentlig publiserte tabellen er feilfri eller oppdatert.

Avtalespesifikke etiketter hindrer at søk om avrop på én navngitt avtale henter en annen avtales særregler. Uspesifiserte avropsspørsmål får en navigasjonsforklaring. Dette er ikke en semantisk sannhetsgaranti.

## Ikke utført

Ingen virkelig modellkjøring, installasjon på brukeres maskiner eller betalte kall. Ingen faglig vurdering av nye genererte svar. Direkte Chromium-navigasjon til localhost ble forsøkt, men blokkert av testmiljøet; derfor er nettleserkontrollene over eksplisitt simulert. Python-HTTP-testene er reelle lokale kall.

Dette er fortsatt en énbruker-demo for åpne opplysninger på egen maskin. Ingen kundeavrop utføres, ingen rettigheter tildeles, og nettsidene oppdateres ikke automatisk.
