# Skyveiviser

En veiviser til skyen for norske virksomheter, helt lokalt. 

Disclaimer: 
Dette er ikke en offisiell applikasjon, men en ufoffisiell veileder i beta versjon, veilederen kan innheholde feilaktige og utdaterte opplysninger. 

**Spør om skyanskaffelser. Se kildene. Kjør modellen lokalt.**

Et lite Python-program med lokale kildesammendrag om skyanskaffelser. 
En datert kundeliste og valgfri språkmodell gjennom Ollama. 
Klargjort for lokal utprøving med åpne opplysninger — ikke for offentlig webdrift.

## Kom i gang på Mac

Du trenger **Python 3.10+**, **Ollama som kjører**, og **en installert lokal modell** på samme maskin. Ingen ekstra Python-pakker trengs.

1. **[Last ned Skyveiviser-delingspakke.zip](downloads/Skyveiviser-delingspakke.zip?raw=true)** og pakk den ut i **Nedlastinger**. Har du allerede pakket den ut, gå til neste steg.
2. Åpne **Terminal** og kjør én gang:

   ```bash
   cd "$HOME/Downloads/Skyveiviser-delingspakke/skyveiviser" && python3 app.py --ollama
   ```

3. Åpne **http://127.0.0.1:8765** i nettleseren, velg en modell og still spørsmålet.

La Terminal stå åpen. Stopp med **Ctrl + C**. `--ollama` kobler til modellmotoren; det installerer eller laster ikke ned noe.

**Eksempel:** «Hvordan forbereder vi en markedsdialog?»

Pakket ut et annet sted? Skriv `cd ` med mellomrom, dra **skyveiviser**-mappen inn i Terminal og trykk Enter. Kjør deretter `python3 app.py --ollama`. Ikke start to kopier.

## Avtaler, avrop og kundeliste

Kildeutvalget dekker seks inngåtte avtaleområder: CIPS, Cloud R&A, CRS, Training & Awareness, TPP og CTI. Avropsveiledninger og vanlige spørsmål er lagt til. Dette er korte sammendrag av offentlige kilder, ikke endelige kontrakter eller priser.

**Prøv:** «Hvilke avtaler har MPS inngått?», «Hvordan gjør vi avrop på CIPS?» eller «Hva gjelder CTI-avtalen?»

**Kundeliste:** Velg «Kundeliste – uten KI». Skriv virksomhetsnavn eller organisasjonsnummer. Skriv for eksempel `CIPS` for å se rader merket Ja eller Via for dette avtaleområdet. Oppslaget bruker vanlig kode, aldri språkmodellen. Navnesøk kan gi flere treff; kontroller organisasjonsnummer.

Alle data ligger i `corpus.json`: `sources` er 24 sammendrag; `customer_register` inneholder 620 tabellrader fra den offentlige kundelisten. Kolonnene beskrives i `columns`, og Ja, Nei, Via og tomme felt beholdes. Det er **620 rader, ikke 620 bekreftede avtalebrukere**. Like navn er ikke slått sammen.

Kundekopien er lest 26.09.2026; kildesiden oppgir selv oppdatertdato 11.11.2025. Ny lesedato er ikke garanti for oppdatert innhold. Kontroller originaltabellen og gjeldende kontraktsgrunnlag før avrop. «Via» må avklares med den angitte enheten. Manglende treff eller tomt felt er ukjent, ikke avslag. VM-kolonnen er bevart, men **VM er ikke bekreftet inngått** i dette kildegrunnlaget. CRS sin gjeldende forlengelse må også bekreftes.

For å ta i bruk oppdateringen: stopp den gamle appen med Ctrl+C, pakk ut den nye pakken og start som før. Bruk hele pakken for kundelistefunksjonen; å erstatte bare JSON-filen i en gammel app gjør ikke kundelisteoppslaget synlig. Ingen installasjoner eller ekstra Python-pakker er lagt til.

## Første gang / problemer

Installer [Python](https://www.python.org/downloads/) og [Ollama](https://ollama.com/download) etter lokale IT-rutiner. `python3 --version` viser Python-versjonen. `ollama list` viser installerte modeller. En modell må lastes ned separat og passe maskinen.

| Problem | Løsning |
|---|---|
| `permission denied` etter mappestien | Skriv `cd ` foran stien. |
| Ingen modeller i menyen | Start Ollama. Kontroller `ollama list`. Bare lokale GGUF-modeller vises. |
| Porten er opptatt | Stopp din tidligere start, eller bruk `--port 8766` og åpne port 8766. |
| Tregt eller ugyldig modellsvar | Prøv et kort eksempel og en mindre modell. Feilen vises uten å sende spørsmålet til en skytjeneste. |

**Uten modell:** Kjør `python3 app.py` fra programmappen. Da får du bare kildetreff.

## Hva den gjør

Spørsmål → ordsøk i lokale sammendrag → inntil tre kilder → valgfritt lokalt modellkall → kontroll av svarformat/kilde-ID-er → visning.

Den leser **ikke nettstedene på nytt**, og modellen er **ikke trent på MPS**. Kildegrunnlaget sendes sammen med hvert spørsmål. Ingen samtalehistorikk sendes til neste spørsmål.

Bruk bare åpne testopplysninger. Appen lagrer ikke samtaler automatisk; eksport er et aktivt valg. Kilde-ID-kontroll er ikke faglig faktasjekk. Les originalkildene før bruk. Dette er ikke en offisiell DFØ-tjeneste eller juridisk rådgivning.

Serveren er begrenset til egen maskin (`127.0.0.1`). Ikke åpne den for LAN eller internett. Kontroller at den separate Ollama-tjenesten har skyfunksjoner deaktivert; se [Ollamas veiledning](https://docs.ollama.com/faq). Appen endrer ikke Ollama-oppsettet. Å åpne originalkildene krever nettverk.

## For den som vil forstå eller tilpasse

**[Slik virker koden](docs/KODEN_FORKLART.md)** · **[Kildeliste](docs/KILDER.md)** · **[Teststatus](reports/TESTSTATUS.md)**

```bash
python3 -m unittest discover -s tests -v
python3 evaluate.py --output reports/evaluation.local.json
```

Tester og kildesøk krever ikke en virkelig modell. Programkode og egen dokumentasjon er tilgjengelig under [MIT-lisensen](LICENSE). Eksterne kildesider og modellene har egne vilkår.

Vedlikeholder: `python3 tools/package.py` bygger den rene ZIP-pakken i `downloads/`. Den inneholder bare filene som trengs for å kjøre eksemplet, med kildehenvisninger og lisens.
