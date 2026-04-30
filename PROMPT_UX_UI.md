# PROMPT UX/UI

Agisci come un Prompt Engineer senior + UX Designer senior + UI Specialist senior + Frontend Engineer senior.

Leggi obbligatoriamente prima questi file di contesto:

- [prompt_engineering.md](prompt_engineering.md)
- [STATO_PLAY_FINAL.md](STATO_PLAY_FINAL.md)
- [STATO_HOME_MATCHINN.md](STATO_HOME_MATCHINN.md)
- [STATO_GEOHOME.md](STATO_GEOHOME.md)

Poi leggi almeno queste superfici reali del codice prima di proporre o modificare qualsiasi file:

- [frontend/src/App.tsx](frontend/src/App.tsx)
- [frontend/src/pages/MatchinnHomePage.tsx](frontend/src/pages/MatchinnHomePage.tsx)
- [frontend/src/pages/ClubDirectoryPage.tsx](frontend/src/pages/ClubDirectoryPage.tsx)
- [frontend/src/pages/PublicClubPage.tsx](frontend/src/pages/PublicClubPage.tsx)
- [frontend/src/pages/PublicBookingPage.tsx](frontend/src/pages/PublicBookingPage.tsx)
- [frontend/src/pages/PublicCancellationPage.tsx](frontend/src/pages/PublicCancellationPage.tsx)
- [frontend/src/pages/PaymentStatusPage.tsx](frontend/src/pages/PaymentStatusPage.tsx)
- [frontend/src/pages/PlayPage.tsx](frontend/src/pages/PlayPage.tsx)
- [frontend/src/pages/PlayAccessPage.tsx](frontend/src/pages/PlayAccessPage.tsx)
- [frontend/src/pages/InviteAcceptPage.tsx](frontend/src/pages/InviteAcceptPage.tsx)
- [frontend/src/pages/SharedMatchPage.tsx](frontend/src/pages/SharedMatchPage.tsx)
- [frontend/src/pages/AdminLoginPage.tsx](frontend/src/pages/AdminLoginPage.tsx)
- [frontend/src/pages/AdminPasswordResetPage.tsx](frontend/src/pages/AdminPasswordResetPage.tsx)
- [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx)
- [frontend/src/pages/AdminCurrentBookingsPage.tsx](frontend/src/pages/AdminCurrentBookingsPage.tsx)
- [frontend/src/pages/AdminBookingsPage.tsx](frontend/src/pages/AdminBookingsPage.tsx)
- [frontend/src/pages/AdminLogsPage.tsx](frontend/src/pages/AdminLogsPage.tsx)
- [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx)
- [frontend/src/index.css](frontend/src/index.css)
- [frontend/src/utils/play.ts](frontend/src/utils/play.ts)

## Obiettivo

Riscrivi e implementa la UX/UI dell'app per renderla semplice, chiara, lineare e orientata all'obiettivo utente, applicando in modo coerente tutti i punti di:

- Punto 1
- Punto 3
- Verifica completa

L'app deve risultare:

- piu leggibile above the fold
- con meno CTA duplicate o concorrenti
- con un funnel utente piu lineare
- coerente tra pubblico, booking, discovery, community privata e area admin
- visivamente unificata tramite logo e pattern di navigazione condivisi

## Vincoli non negoziabili

Non modificare la business logic.

In particolare:

- non cambiare logica di booking pubblico, caparra, checkout, payment status, cancellazione, OTP, invite flow, group access, join/leave match, notification dispatch, ranking pubblico, Match Alert, discovery pubblica o fallback Play gia approvati
- non cambiare contratti API, payload, semantica dei canali o separazione pubblico/privato
- non introdurre nuova auth globale Matchinn
- non introdurre nuove dipendenze se non strettamente necessarie
- non esporre dati privati nelle superfici pubbliche
- non eliminare la semantica attuale degli alias Play

Mantieni anche queste verita architetturali gia validate:

- `/` e la home prodotto Matchinn
- `/booking` resta il booking pubblico tenant-aware
- `/clubs` resta il punto centrale di scelta del club
- `/c/:clubSlug` resta la pagina pubblica del club
- `/c/:clubSlug/play` resta la community privata del club
- `/play` e un alias che oggi cade su `DEFAULT_PLAY_ALIAS_SLUG = default-club`; non cambiare questa logica di fallback, ma evita di esporre il placeholder tecnico come esperienza utente finale
- la geolocalizzazione deve restare esplicita e mai forzata all'ingresso

## Requisiti globali obbligatori

1. Usa il logo `dark.png` come asset visivo su tutte le pagine utente e admin.
	Contesto reale: l'asset frontend servito e [frontend/public/dark.png](frontend/public/dark.png).

2. Ogni pagina non-root deve avere un tasto di ritorno chiaro alla pagina precedente e/o alla home.
	Regola pratica:
	- usa una CTA di ritorno visibile e coerente
	- se il back browser e fragile, usa una destinazione esplicita come home, clubs, booking o dashboard admin
	- la root `/` non richiede un bottone home aggiuntivo perche e gia la home

3. Le tab/card degli orari preferiti in Match Alert devono usare il colore hex `#cffafe`.

4. Uniforma il pattern dei top header:
	- logo `dark.png`
	- titolo pagina
	- eventuale contesto secondario
	- una CTA chiara di ritorno

5. Riduci i doppioni reali:
	- CTA con etichette diverse ma stesso outcome
	- pannelli che ripetono lo stesso intent della hero
	- ingressi guest duplicati nello stesso funnel

6. Mantieni patch minime e mirate.
	Se una piccola astrazione condivisa riduce davvero duplicazioni UI senza toccare la logica, e ammessa. Evita refactor larghi non richiesti.

## Funnel ideale da implementare

La UX complessiva deve seguire questo percorso mentale:

1. Home: l'utente capisce subito cosa fare.
2. Directory club: l'utente cerca o scopre il club giusto.
3. Pagina club: l'utente sceglie un solo intent principale.
4. Booking oppure community: l'utente entra nel ramo corretto senza ambiguita.
5. Azione: prenota, entra, si identifica, segue un club o si unisce a un match.
6. Esito: stato finale chiaro con una CTA di ritorno comprensibile.

Tutto cio che rompe questo funnel va semplificato, fuso o eliminato.

## Decisioni UX/UI da implementare per route

### 1. Home `/`

File principali:

- [frontend/src/pages/MatchinnHomePage.tsx](frontend/src/pages/MatchinnHomePage.tsx)
- [frontend/src/index.css](frontend/src/index.css)

Obiettivo:

- la home deve essere il punto di ingresso piu semplice e diretto di tutta l'app

Implementa queste decisioni:

- mantieni come CTA hero principali solo:
  - `Trova campi vicino a te`
  - `Scegli il club per prenotare`
- elimina il blocco `Stato rapido`
- elimina il blocco/tab `Posizione` che oggi replica lo stesso intent della hero
- mantieni `Area club` come secondaria e meno dominante
- mantieni `Le tue community` e `Match da completare`, ma con gerarchia piu pulita e meno rumore above the fold
- evita metriche tecniche o contatori a zero in primo piano
- usa `dark.png` in header

Duplicazione reale da risolvere:

- le CTA hero verso `/clubs` e il blocco `Posizione` con `Usa la mia posizione` / `Cerca un campo` fanno percepire lo stesso outcome utente

### 2. Directory `/clubs` e `/clubs/nearby`

File principali:

- [frontend/src/pages/ClubDirectoryPage.tsx](frontend/src/pages/ClubDirectoryPage.tsx)
- [frontend/src/index.css](frontend/src/index.css)

Obiettivo:

- `/clubs` deve essere il punto unico e leggibile di scelta del club

Implementa queste decisioni:

- mantieni ricerca e directory club come azione primaria
- mantieni Match Alert come azione secondaria ma chiara
- differenzia in modo netto la geolocalizzazione per `cercare club vicini` dalla geolocalizzazione per `salvare la posizione Match Alert`
- evita testi o CTA che facciano sembrare identiche due azioni diverse
- mantieni le tab degli orari preferiti con `#cffafe`
- mantieni il ritorno alla home
- usa `dark.png` in header

Ambiguita da correggere:

- `Trova club vicino a me` e `Usa la mia posizione` oggi usano linguaggi troppo simili pur avendo outcome diversi

### 3. Pagina club pubblica `/c/:clubSlug`

File principali:

- [frontend/src/pages/PublicClubPage.tsx](frontend/src/pages/PublicClubPage.tsx)

Obiettivo:

- la pagina club deve chiarire subito le tre strade possibili: booking, community, alert

Implementa queste decisioni:

- inserisci `dark.png` nel top header, senza perdere il contesto del club
- aggiungi un ritorno chiaro a home e/o clubs
- conserva le CTA principali ma gerarchizzale meglio
- evita che `Segui questo club` e `Attiva discovery` sembrino due sistemi separati e scollegati
- rendi piu evidente il filtro livello e il suo valore pratico
- rendi i gruppi `Da chiudere subito`, `Buone occasioni`, `Da monitorare` piu leggibili e orientati all'azione
- non cambiare il modello pubblico read-only e non esporre dati privati

### 4. Booking pubblico `/booking`

File principali:

- [frontend/src/pages/PublicBookingPage.tsx](frontend/src/pages/PublicBookingPage.tsx)

Obiettivo:

- il booking deve restare lineare e tenant-aware, senza confondere l'utente quando manca il contesto club

Implementa queste decisioni:

- aggiungi `dark.png` nel top header
- aggiungi un ritorno chiaro a home e/o pagina precedente
- mantieni la struttura a step attuale e non cambiare la logica slot/pagamento
- nello stato `club mancante`, riduci l'overchoice:
  - una CTA primaria verso la directory club
  - una CTA secondaria verso home o ritorno
  - evita tre uscite concorrenti di pari peso
- mantieni gli empty state sugli slot gia esistenti
- se la sezione geolocalizzata `Club vicini a te` resta, trattala come supporto secondario e non come flusso concorrente al booking

### 5. Cancellazione `/booking/cancel`

File principali:

- [frontend/src/pages/PublicCancellationPage.tsx](frontend/src/pages/PublicCancellationPage.tsx)

Obiettivo:

- mantenere il flusso semplice, con messaggio rimborso e azione finale ben collegati

Implementa queste decisioni:

- aggiungi `dark.png`
- aggiungi ritorno a home e/o booking
- rafforza la lettura della finestra di rimborso senza cambiare la logica
- tieni CTA e conseguenza economica piu vicine nello stesso blocco percettivo

### 6. Esiti pagamento `/booking/success`, `/booking/cancelled`, `/booking/error`

File principali:

- [frontend/src/pages/PaymentStatusPage.tsx](frontend/src/pages/PaymentStatusPage.tsx)

Obiettivo:

- rendere gli esiti piu rassicuranti e chiari, senza cambiare polling o semantica di stato

Implementa queste decisioni:

- aggiungi `dark.png`
- aggiungi ritorno chiaro a home e/o booking
- uniforma la grammatica visiva delle tre varianti
- migliora la percezione del polling nello stato success senza cambiare la logica di verifica
- conserva snapshot booking e azione self-service di annullamento quando gia prevista

### 7. Play alias `/play` e fallback `/c/default-club/play`

File principali:

- [frontend/src/App.tsx](frontend/src/App.tsx)
- [frontend/src/utils/play.ts](frontend/src/utils/play.ts)
- [frontend/src/pages/PlayPage.tsx](frontend/src/pages/PlayPage.tsx)

Obiettivo:

- mantenere la logica di fallback esistente, ma evitare che l'utente percepisca `default-club` come nome prodotto reale

Implementa queste decisioni:

- non cambiare la route logic degli alias
- correggi l'esposizione UX del placeholder tecnico `DEFAULT CLUB`
- usa `dark.png`
- aggiungi ritorno chiaro a home e/o booking
- tratta `/play` e `/c/default-club/play` come superficie Play di fallback da rendere presentabile e non tecnica

### 8. Community privata `/c/:clubSlug/play`

File principali:

- [frontend/src/pages/PlayPage.tsx](frontend/src/pages/PlayPage.tsx)

Obiettivo:

- la board Play deve restare potente, ma piu leggibile e meno ridondante per guest e player gia entrati

Implementa queste decisioni:

- aggiungi `dark.png` nel top header, mantenendo il contesto club
- aggiungi ritorno chiaro a home e/o booking
- per guest evita il doppione reale tra:
  - CTA hero `Entra o rientra`
  - CTA interna `Apri accesso community`
- mantieni `Partite da completare` come primo contenuto utile
- mantieni `Le mie partite`, `Crea nuova partita` e `Preferenze notifiche`, ma con gerarchia piu netta
- non cambiare logica di create/join/payment/notifiche

### 9. Accesso community `/c/:clubSlug/play/access` e invito `/c/:clubSlug/play/invite/:token`

File principali:

- [frontend/src/pages/PlayAccessPage.tsx](frontend/src/pages/PlayAccessPage.tsx)
- [frontend/src/pages/InviteAcceptPage.tsx](frontend/src/pages/InviteAcceptPage.tsx)

Obiettivo:

- ridurre il punto piu fragile del funnel Play senza cambiare API o purpose backend

Implementa queste decisioni:

- aggiungi `dark.png`
- aggiungi ritorno chiaro a home e/o booking
- evita che `Scegli il flusso` diventi il primo problema cognitivo dell'utente
- per accesso generico usa etichette umane e autoesplicative, non tecniche
- per invite/group evita scelte inutili e preconfigura il flusso corretto gia noto dal contesto route
- mantieni OTP, verifica, redirect e purpose attuali

### 10. Match condiviso `/c/:clubSlug/play/matches/:shareToken`

File principali:

- [frontend/src/pages/SharedMatchPage.tsx](frontend/src/pages/SharedMatchPage.tsx)

Obiettivo:

- rendere chiarissimo se l'utente e gia riconosciuto e quale sia il prossimo passo

Implementa queste decisioni:

- aggiungi `dark.png`
- aggiungi ritorno chiaro a home e/o Play board
- unifica stato profilo e CTA principale in un unico messaggio ben leggibile
- non cambiare la logica del join o del link condiviso

### 11. Login admin `/admin/login`

File principali:

- [frontend/src/pages/AdminLoginPage.tsx](frontend/src/pages/AdminLoginPage.tsx)

Obiettivo:

- mantenere il login admin essenziale ma piu chiaro sul reset password

Implementa queste decisioni:

- aggiungi `dark.png`
- mantieni una CTA chiara di ritorno a booking o home
- rendi il recupero password piu evidente come secondaria importante
- non cambiare auth o reset logic

### 12. Reset password admin `/admin/reset-password`

File principali:

- [frontend/src/pages/AdminPasswordResetPage.tsx](frontend/src/pages/AdminPasswordResetPage.tsx)

Implementa queste decisioni:

- aggiungi `dark.png`
- aggiungi ritorno chiaro a login admin e/o home
- mantieni il flusso attuale

### 13. Dashboard admin `/admin`

File principali:

- [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx)

Implementa queste decisioni:

- aggiungi `dark.png`
- aggiungi ritorno chiaro a home e/o login/dashboard root quando utile
- raggruppa meglio i moduli per task e priorita
- riduci la densita above the fold
- non cambiare logica operativa admin

### 14. Prenotazioni attuali `/admin/prenotazioni-attuali`

File principali:

- [frontend/src/pages/AdminCurrentBookingsPage.tsx](frontend/src/pages/AdminCurrentBookingsPage.tsx)

Implementa queste decisioni:

- aggiungi `dark.png`
- aggiungi ritorno chiaro alla dashboard e/o home
- rendi piu leggibile il selettore temporale attuale
- non cambiare logica dati o filtri

### 15. Prenotazioni `/admin/prenotazioni`

File principali:

- [frontend/src/pages/AdminBookingsPage.tsx](frontend/src/pages/AdminBookingsPage.tsx)

Implementa queste decisioni:

- aggiungi `dark.png`
- aggiungi ritorno chiaro alla dashboard e/o home
- mantieni il filtro origine, ma rendilo piu umano e meno tecnico nel linguaggio
- conserva la semantica `PLAY_ONLY` / `NON_PLAY`, ma migliora etichette e microcopy

### 16. Log admin `/admin/log`

File principali:

- [frontend/src/pages/AdminLogsPage.tsx](frontend/src/pages/AdminLogsPage.tsx)

Implementa queste decisioni:

- aggiungi `dark.png`
- aggiungi ritorno chiaro alla dashboard e/o home
- mantieni l'impianto attuale, evitando cambi inutili

### 17. Dettaglio prenotazione `/admin/bookings/:bookingId`

File principali:

- [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx)

Implementa queste decisioni:

- aggiungi `dark.png`
- aggiungi ritorno chiaro alle prenotazioni e/o home
- migliora la leggibilita mobile del blocco `Modifica slot`
- non cambiare la logica di update prenotazione

## Doppioni e conflitti da verificare e risolvere esplicitamente

Verifica e risolvi questi casi in modo esplicito nel codice e nella UI finale:

1. Home:
	- CTA hero vs blocco `Posizione`
	- `Stato rapido` come pannello tecnico non orientato al compito

2. Directory `/clubs`:
	- linguaggio troppo simile tra geolocalizzazione per ricerca club e geolocalizzazione per Match Alert

3. Play page guest:
	- `Entra o rientra` vs `Apri accesso community`

4. Booking senza tenant:
	- troppe CTA di uscita concorrenti nello stato di recovery

5. Admin:
	- etichette troppo tecniche che usano `/play` come linguaggio utente finale

## Coerenza visuale richiesta

- usa una direzione visuale coerente con il design gia presente
- non introdurre una nuova estetica scollegata
- rafforza solo gerarchia, spacing, titolo, CTA e leggibilita
- usa `dark.png` in tutte le hero/header pagina
- mantieni i tab Match Alert degli orari preferiti con `#cffafe`
- evita pannelli decorativi se non aiutano davvero il compito utente

## File probabilmente coinvolti

Parti da questi file, ma tocca solo quelli necessari:

- [frontend/src/pages/MatchinnHomePage.tsx](frontend/src/pages/MatchinnHomePage.tsx)
- [frontend/src/pages/ClubDirectoryPage.tsx](frontend/src/pages/ClubDirectoryPage.tsx)
- [frontend/src/pages/PublicClubPage.tsx](frontend/src/pages/PublicClubPage.tsx)
- [frontend/src/pages/PublicBookingPage.tsx](frontend/src/pages/PublicBookingPage.tsx)
- [frontend/src/pages/PublicCancellationPage.tsx](frontend/src/pages/PublicCancellationPage.tsx)
- [frontend/src/pages/PaymentStatusPage.tsx](frontend/src/pages/PaymentStatusPage.tsx)
- [frontend/src/pages/PlayPage.tsx](frontend/src/pages/PlayPage.tsx)
- [frontend/src/pages/PlayAccessPage.tsx](frontend/src/pages/PlayAccessPage.tsx)
- [frontend/src/pages/InviteAcceptPage.tsx](frontend/src/pages/InviteAcceptPage.tsx)
- [frontend/src/pages/SharedMatchPage.tsx](frontend/src/pages/SharedMatchPage.tsx)
- [frontend/src/pages/AdminLoginPage.tsx](frontend/src/pages/AdminLoginPage.tsx)
- [frontend/src/pages/AdminPasswordResetPage.tsx](frontend/src/pages/AdminPasswordResetPage.tsx)
- [frontend/src/pages/AdminDashboardPage.tsx](frontend/src/pages/AdminDashboardPage.tsx)
- [frontend/src/pages/AdminCurrentBookingsPage.tsx](frontend/src/pages/AdminCurrentBookingsPage.tsx)
- [frontend/src/pages/AdminBookingsPage.tsx](frontend/src/pages/AdminBookingsPage.tsx)
- [frontend/src/pages/AdminLogsPage.tsx](frontend/src/pages/AdminLogsPage.tsx)
- [frontend/src/pages/AdminBookingDetailPage.tsx](frontend/src/pages/AdminBookingDetailPage.tsx)
- [frontend/src/index.css](frontend/src/index.css)
- eventuali componenti condivisi header/navigation solo se riducono davvero duplicazione UI senza alterare logica

Aggiorna i test frontend solo dove cambiano copy, CTA, struttura o aspettative visive rilevanti.

## Output richiesto

Lavora in questo ordine:

## 1. Prerequisiti verificati
- conferma lettura dei file di contesto
- conferma route reali da [frontend/src/App.tsx](frontend/src/App.tsx)

## 2. Mappa delle superfici toccate
- route -> file principale -> obiettivo UX

## 3. Gap analysis
- duplicazioni reali
- punti di confusione
- incoerenze di naming

## 4. File coinvolti
- elenco dei file modificati

## 5. Implementazione
- patch minime e mirate
- nessun cambio di business logic

## 6. Test aggiornati
- solo test necessari

## 7. Verifica finale
- test eseguiti
- build se utile
- esito PASS / FAIL
- rischi residui

## 8. Checklist route-by-route
- `/`
- `/booking`
- `/clubs`
- `/clubs/nearby`
- `/c/:clubSlug`
- `/booking/cancel`
- `/booking/success`
- `/booking/cancelled`
- `/booking/error`
- `/play`
- `/c/default-club/play`
- `/c/:clubSlug/play`
- `/c/:clubSlug/play/access`
- `/c/:clubSlug/play/invite/:token`
- `/c/:clubSlug/play/matches/:shareToken`
- `/admin/login`
- `/admin/reset-password`
- `/admin`
- `/admin/prenotazioni-attuali`
- `/admin/prenotazioni`
- `/admin/log`
- `/admin/bookings/:bookingId`

Per ogni route indica brevemente:

- cosa e stato semplificato
- quale duplicazione e stata rimossa o evitata
- come e stato gestito logo + ritorno navigazione

## Quality gate finale

Prima di chiudere:

- verifica di non avere cambiato la business logic
- verifica che `dark.png` sia presente in tutte le pagine rilevanti
- verifica che ogni pagina non-root abbia un ritorno chiaro
- verifica che i tab degli orari preferiti Match Alert usino `#cffafe`
- verifica che i doppioni reali siano stati fusi o eliminati
- verifica che `/play` e `/c/default-club/play` non espongano piu il placeholder tecnico come esperienza utente finale, senza cambiare la logica alias
- verifica che il risultato sia semplice, chiaro e orientato al compito dell'utente

Se trovi un conflitto tra miglioramento UX e business logic attuale, proteggi la business logic e risolvi il problema solo a livello di UI, copy, gerarchia, affordance e navigazione.
