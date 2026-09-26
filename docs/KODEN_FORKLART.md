# Slik virker Skyveiviser

## Forklaringen på 30 sekunder

> Skyveiviser er et lite Python-program som leter i et avgrenset, lokalt kildegrunnlag. Det finner relevant tekst og kan sende teksten sammen med spørsmålet til en språkmodell på samme maskin. Modellen blir bedt om å formulere et svar med kilde-ID-er. Programmet kontrollerer svarformat og at ID-ene er fra grunnlaget, før svaret vises med lenker til originalene.

**Programmet velger kilder og håndterer flyten. Modellen formulerer teksten.** Det er ikke en nytrent modell, og det er ingen automatisk innhenting fra nettet.

## 1. Delene og filene

| Fil | Ansvar |
|---|---|
| `app.py` | Starter webserveren på egen maskin, mottar spørsmål og returnerer svar. |
| `engine.py` | Leser kilder, finner relevante sammendrag, kaller Ollama og kontrollerer svaret. |
| `corpus.json` | 24 lagrede kildesammendrag og en separat kundetabell med ID, tittel, lenke, dato og søkeord. |
| `web/index.html` | Sidens innhold: spørsmål, modellvalg, knapper og resultatområde. |
| `web/style.css` | Hvordan siden ser ut, også på en smal skjerm. |
| `web/app.js` | Reagerer på klikk, sender spørsmålet til Python og viser resultatet. |
| `tests/test_demo.py` | Automatiske kontroller av programmet med simulerte modellsvar. |
| `evaluate.py` | Prøver ti forhåndsdefinerte spørsmål og skriver en lokal resultatfil. |

Ollama og modellfilene ligger **utenfor** denne pakken. Ollama er programmet som laster og kjører modellen. Qwen er ett mulig modellvalg, ikke en del av selve Python-programmet.

## 2. Hva startkommandoen betyr

```bash
cd "$HOME/Downloads/skyveiviser-main" && python3 app.py --ollama
```

`cd` betyr «gå til denne mappen». `$HOME` er hjemmemappen til den innloggede brukeren. Anførselstegnene sørger for at mellomrom i stien ikke deler den opp. `&&` betyr at neste kommando bare kjøres hvis bytte av mappe lyktes. `python3 app.py` kjører Python-filen. `--ollama` er et valg som gir appen lov til å kontakte den lokale modellmotoren.

GitHubs «Last ned»-lenke gir mappen `skyveiviser-main`. Den valgfrie, lokalt bygde delingspakken fra `tools/package.py` bruker i stedet `Skyveiviser-delingspakke/skyveiviser`; kommandoen må peke på mappen som inneholder `app.py`.

Kommandoen starter allerede programmet; den skal ikke kjøres to ganger. Åpning av nettleseren starter ikke Python på nytt.

I `app.py` skjer dette:

```python
if __name__ == "__main__":
    main()
```

Dette betyr at `main()` kjøres når filen startes som et program. Ved import i en test starter ikke webserveren automatisk. `main()` leser valgene, oppretter en `DemoServer` og lar den vente på forespørsler frem til Ctrl+C.

Serveren bruker **127.0.0.1:8765**. Adressen 127.0.0.1 peker tilbake til samme maskin; 8765 er porten til denne appen. Ollama har en annen port: **11434**. Begge kan derfor kjøre samtidig.

## 3. Kildegrunnlaget: `corpus.json`

JSON er et tekstformat for strukturerte data. Det er ikke kode som kjøres. `json.loads()` gjør JSON-tekst om til Python-ordbøker og lister.

En kilde har omtrent denne formen — forkortet eksempel:

```json
{
  "id": "S2",
  "title": "Markedsdialog",
  "url": "https://markedsplassen.anskaffelser.no/kunnskap-og-veiledning/markedsdialog",
  "reviewed_at": "2026-09-25",
  "keywords": ["markedsdialog", "behovsbeskrivelse", "brukercase"],
  "text": "Et kort redaksjonelt sammendrag av den valgte veiledningen."
}
```

I den virkelige filen finnes også blant annet `section`. De opprinnelige fem temaene er MPS, markedsdialog, informasjonssikkerhet, FinOps og SSA. I versjon 0.3 kommer avtaleområder, avropsveiledninger og vanlige spørsmål i tillegg. Sammendragene er ikke fullstendige kopier av nettsidene.

`load_corpus()` leser filen ved oppstart. Funksjonen kontrollerer at nødvendige felt finnes, at kilde-ID-ene er unike, og at originaladressene bruker HTTPS og et av de to godkjente domenene. Den kontrollerer ikke at nettsiden fremdeles eksisterer eller at sammendraget er faglig riktig.

Funksjonen beregner også en **SHA-256-hash**: et fingeravtrykk av filens bytes. Det lar oss knytte et resultat til en bestemt filversjon. Det er ikke kryptering eller bevis på riktig innhold. Endrer du en kilde, må serveren startes på nytt for å lese endringen.

## 4. Hva nettleseren gjør før spørsmålet

Nettleseren laster HTML, CSS og JavaScript fra Python-serveren. JavaScript ber om `/api/config` for å se om modellmodus er aktivert. Hvis den er det, hentes `/api/models`.

Python bruker da `installed_models()` til å spørre Ollama på **GET /api/tags**. Listen filtreres til rapporterte lokale GGUF-modeller med navn, størrelse og digest. Synlige skyaliaser og `remote_host`/`remote_model` filtreres bort. Det er en kontroll av metadata, ikke et uavhengig bevis på hvor modellmotoren faktisk utfører arbeidet.

Ved klikk på spørreknappen sender JavaScript omtrent dette til **POST /api/ask**:

```json
{
  "question": "Hvordan forbereder vi en markedsdialog?",
  "mode": "ollama",
  "model": "qwen2.5-coder:7b"
}
```

Modellnavnet er bare et eksempel. Det må finnes i den lokale listen. Ingen tidligere spørsmål eller svar følger med.

## 5. `app.py` mottar spørsmålet

`do_POST()` kontrollerer at forespørselen har riktig adresse, JSON-format og begrenset størrelse. Appen kontrollerer også Host, Origin og en tilfeldig, midlertidig forespørselsnøkkel for å hindre enkle uønskede nettleserkall.

Denne nøkkelen er ikke et LLM-token, ikke et passord til Ollama og ikke en innlogging for flere brukere. Andre programmer på samme maskin må fortsatt være betrodde.

En **semafor** med én plass hindrer at appen starter flere spørsmål samtidig. Et sett tidspunkter begrenser inntaket til tolv forespørsler per minutt. Serveren sender spørsmålet videre til `ask()` i `engine.py`.

`try` / `except` / `finally` brukes for å forsøke arbeidet, håndtere feil og frigjøre jobbplassen også når noe feiler. En kjent `DemoError` blir håndtert som en feilrespons, ikke et falskt svar eller et kall til en reserveleverandør. Flere feil i spørsmålsløpet vises med samme generelle feilmelding; det er en bevisst begrensning i denne lille demonstratoren.

## 6. `retrieve()` velger kildene — uten KI

Først kontrollerer `validate_question()` at spørsmålet er tekst med 3–1500 tegn. `words()` lager små bokstaver, finner ord og fjerner vanlige småord.

Spørsmålet «Hvordan forbereder vi en markedsdialog?» blir i dette søket til ordmengden **forbereder, markedsdialog**. En `set` er en mengde uten duplikater; gjentakelser av samme ord gir ikke flere poeng.

For hver kilde undersøker koden to ting: treff mot manuelt oppgitte søkeord, og overlapp med ord i kildetittel/sammendrag. Den godtar også at et spørsmålsord begynner med et søkeord på minst fem tegn, eksempelvis en bøyning som begynner med «markedsdialog».

Selve poengberegningen er:

```python
score = 3 * len(key_hits) + len(overlap) / math.sqrt(len(words(s["text"])) or 1)
```

Hvert søkeordtreff teller tre poeng. Vanlige teksttreff gir et tillegg, justert for hvor mange forskjellige ord sammendraget har. `or 1` forhindrer deling på null. Hvis det verken er søkeordtreff eller minst to teksttreff, tas ikke kilden med.

Kildene sorteres etter poeng. Inntil **tre** returneres. Poeng er bare en enkel rangeringsregel, **ikke sannsynlighet, kvalitetsskår eller sikker faglig relevans**. Den lille søkemetoden kan overse synonymer eller finne en kilde som ikke faktisk besvarer spørsmålet.

Finnes ingen treff, returneres `no_source_match` uten modellkall. I kildesøkmodus returneres treffene direkte, også uten modellkall.

## 7. `ask()` lager modellforespørselen

Når det finnes treff og modellmodus er aktivert, kontrolleres valgt modell igjen mot modellisten. Deretter sendes to meldinger til Ollama:

**Systemmeldingen** er instruksjonen: Svar på norsk fra de vedlagte sammendragene, bruk oppgitte kilde-ID-er og avstå hvis materialet ikke dekker spørsmålet. Instruksjonen er ikke en teknisk garanti mot feil eller påvirkning fra tekst.

**Brukermeldingen** inneholder spørsmålet og de valgte kildenes **ID og sammendrag**. Modellen åpner ikke kildelenkene. Lenker og datoer settes inn fra kildefilen når resultatet vises.

`ollama_request()` sender dette til **POST http://127.0.0.1:11434/api/chat**. Kun modelliste og chat er tillatt. Ingen automatisk modellnedlasting, skyreserve, miljøproxy eller HTTP-omdirigering brukes av klienten.

| Innstilling | Betydning i dette programmet |
|---|---|
| `stream: false` | Svaret kommer samlet, ikke ord for ord på skjermen. |
| `format: SCHEMA` | Modellen bes om et bestemt JSON-format. |
| `temperature: 0` | Ber om lite tilfeldig variasjon, ikke garantert sannhet eller identiske svar på all maskinvare. |
| `num_ctx: 4096` | Forespurt kontekstvindu; må passe valgt modell og runtime. |
| `num_predict: 384` | Forespurt grense for genereringen; et for langt svar kan bli avkortet og avvist som ugyldig JSON. |
| `keep_alive: "2m"` | Ber Ollama beholde modellen lastet en stund etter kallet. Det er ikke samtalehukommelse. |

Modellistekallet har fire sekunders timeout, chatkallet 240 sekunders timeout på nettverksoperasjonen. Dette er ikke en hard garanti for total kjøretid eller at Ollama stopper en jobb ved timeout. Responsen er begrenset til 2 MB. Ingen verktøy eller shelltilgang gis til modellen.

Ollama bruker den valgte, allerede trente modellen til å generere tokens. Programmet fintrener ikke modellen og endrer ikke modellvektene.

## 8. `validate_answer()` kontrollerer svaret

Et **illustrert**, gyldig format kan se slik ut; dette er ikke et resultat fra en virkelig modelltest:

```json
{
  "abstain": false,
  "claims": [
    {
      "text": "Forbered en behovsbeskrivelse og relevante brukercase.",
      "source_ids": ["S2"]
    }
  ]
}
```

`abstain` betyr «avstå». `claims` er en liste med påstander. Programmet krever riktig feltnavn og datatype, høyst fem påstander, avgrenset tekst og en til tre gyldige kilde-ID-er per påstand. Det avviser egne URL-er i modellteksten og ID-er som ikke var i det sendte grunnlaget. Avståelse må ha tom påstandsliste.

Dette er **formatkontroll og kilde-ID-kontroll**, ikke automatisk faktasjekk. En modell kan skrive noe feil og likevel vise til S2. Det oppdages ikke nødvendigvis av denne kontrollen. En fagperson må lese svaret opp mot kildene.

## 9. Resultatet vises og kan eksporteres

Python returnerer JSON med svar, kilder, modellmetadata, kildefingeravtrykk og målinger. `render()` i `web/app.js` bygger den synlige visningen.

Tekst legges inn med `textContent`, ikke som HTML som modellen kan lage. Lenker kommer fra kildefilen. Det reduserer risikoen for at modelltekst blir til kjørbar kode i siden.

`elapsed_seconds` er målt tid i `ask()`, ikke full tid fra klikk til ferdig visning. Inn-/uttokens vises bare når Ollama oppgir dem. Beregnet genereringshastighet bruker antall genererte tokens delt på Ollamas genereringstid; det er ikke total gjennomløpshastighet. **Kostnad er ukjent**, ikke null.

Spørsmål og svar lagres ikke automatisk av appen. «Lagre resultat» lager bevisst en JSON-fil i nettleseren. Operativsystem, nettleser og modellmotor kan ha andre logger eller lagring.

## Kundeliste: et oppslag uten modell

`corpus.json` inneholder nå også `customer_register`. Feltet `columns` sier hva hver plass i tabellradene betyr: organisasjonsnummer, navn og de sju avtalekolonnene. De 620 radene er en avskrift av den offentlige kundelisten, ikke 620 positive tilslutninger.

Den lille filen `customers.py` kontrollerer formatet og slår opp råverdier. `lookup()` søker eksakt på organisasjonsnummer, eksakt eller delvis på navn, eller viser Ja/Via-rader for et bestemt avtaleområde. Alle resultater går direkte til nettleseren. **Ingen kundelisterader sendes til LLM-en.**

`ask()` har en ekstra modus, `customers`. Den returnerer `customer_rows` og kolonnebeskrivelser, eller et tydelig manglende treff. Modus velges i samme meny som kildesøk og modell. Ved kundelisteoppslag er minste søkelengde to tegn, slik at VM kan søkes; vanlige spørsmål krever fortsatt tre.

Datoer, tomme felt og «Via» beholdes. Rader med like navn slås ikke sammen. Oppslaget viser publiserte verdier, **ikke en juridisk beslutning om avropsrett**. VM vises med status ikke bekreftet inngått. Manglende treff er ikke et avslag.

For avropsspørsmål har kildene `agreement_ids`. `retrieve()` bruker kjente avtalenavn til å velge riktig kildeområde. Dette hindrer at en spesifikk CIPS-forespørsel får CRS-regler som om de var CIPS-regler. Uspesifiserte avropsspørsmål får en kort navigasjonshjelp. Dette er fortsatt vanlig ordsøk, ikke et nytt rammeverk.

## 10. Tester og endringer

`tests/test_demo.py` kontrollerer blant annet søk, ugyldige kilde-ID-er, modellformat, inputgrenser og lokal HTTP-kommunikasjon. Den bruker simulerte modellsvar. Det gjør programtestene raske og repeterbare, men sier ikke om en virkelig modell er god til norsk veiledning.

`evaluate.py` har seks opprinnelige fagspørsmål, tre spørsmål uten dekning og ett FAQ-spørsmål om manglende prisinformasjon. Det sjekker forventet kilde på dette lille utviklingssettet. Settet er ikke en uavhengig kvalitetsmåling. Reell modellutprøving krever eksplisitt valg og manuell faglig vurdering.

For å tilpasse eksemplet: endre sammendrag, søkeord og dato i `corpus.json`, behold kildeformatet og kontroller originalen. Nye kildedomener krever i tillegg endring i `SOURCE_HOSTS` i `engine.py`. Start på nytt, kjør testene og oppdater testspørsmålene. **Ikke legg inn interne eller sensitive dokumenter.** Lokal modellkjøring alene er ingen sikkerhetsgodkjenning.

## Spørsmål det er nyttig å kunne svare på

**Er dette en egen KI-modell?** Nei, en applikasjon som bruker en eksisterende lokal modell.

**Er den trent på MPS?** Nei. Den får relevant tekst med hvert spørsmål.

**Er dette RAG?** Den følger prinsippet «hent relevant grunnlag, så generer svar», med enkelt ordsøk. Ingen embeddings, vektordatabase eller fullskala dokumentpipeline er brukt.

**Hvorfor Python og JavaScript?** Python håndterer kilder og modellkall. JavaScript håndterer knapper og visning i nettleseren. HTML/CSS lager siden.

**Hvor er nytten?** Et lite, inspeksjonsvennlig eksempel som virksomheter kan prøve lokalt, forstå og tilpasse. Tidsbesparelse og faglig gevinst må undersøkes i egne oppgaver.

**Kan det legges på et offentlig nettsted nå?** Nei. Det er en énbruker-demo på loopback. Tilgangsstyring, drift og sikkerhet for flere brukere er ikke del av leveransen.

## Tekniske primærkilder

[Ollama chat-API](https://docs.ollama.com/api/chat) · [Modelliste](https://docs.ollama.com/api/tags) · [Ollama og lokal drift](https://docs.ollama.com/faq) · [Python HTTP-server](https://docs.python.org/3/library/http.server.html)

Forklaringen beskriver denne versjonens kode. Modellmotorens dokumentasjon må kontrolleres mot versjonen som brukes.


## Oppdatering 0.4: fire hurtigvalg og automatisk tilslutningsoppslag

`choose_mode()` i `engine.py` velger direkte oppslag før et eventuelt modellkall. Tilslutningsspørsmål går til `customers.lookup()`, avtaleoversikt til `catalogue()`, og VM-spørsmål til kildevisning med datert status. Disse rutene kaller ikke en språkmodell. Andre fagspørsmål bruker den eksisterende søke-/modellflyten.

`entity_query()` i `customers.py` henter virksomheten i et enkelt uttrykk som «Jeg jobber i Asker kommune». `find_customer_rows()` matcher organisasjonsnummer eksakt, eller navn mot tabellen. Dette er enkle, synlige regler, ikke en generell språkforståelse. Ingen fuzzy gjetting brukes. Flere treff bevares hver for seg; ukjent virksomhet og spørsmål uten navn gir henholdsvis manglende treff og spørsmål om navn.

`renderCustomers()` viser én virksomhet som en oversikt over avtaleområder og tabellverdier. Ja og Via listes som registrerte tilslutninger for de seks inngåtte områdene. VM holdes separat som kommende, også når kundelisten sier Ja. Nei og tomt felt beholder sin betydning. Asker kommune er i denne kopien merket Nei i alle kolonnene.

`vm.json` er en liten tilleggsfil ved siden av `corpus.json`: den inneholder kilde S25 og en separat `plan`. Dermed endres ikke kundelistens 620 rader når fremdriftsplanen oppdateres. `load_corpus()` leser begge og beregner et fingeravtrykk av begge filene. Eldre pakker uten VM-filen kan leses uten å finne på en dato. Feil format i en eksisterende VM-fil avvises.

Oktober 2026 er en foreløpig planopplysning, ikke offentlig kildebekreftet tildeling. `publicly_confirmed` er false. Planen sendes ikke til modellen som et offentlig kildeutsagn; den vises separat med forbehold. Modellen brukes heller ikke til å skrive tilslutningsresultatene.

Hurtigknappene i `web/app.js` utfører de tre første oppslagene med ett klikk. Virksomhetsknappen åpner et tomt søkefelt. Knapper og inndata låses mens en forespørsel pågår. Et gammelt resultat fjernes før neste spørsmål, også dersom neste kall feiler.
