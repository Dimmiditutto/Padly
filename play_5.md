# PROMPT FASE 5 - PAGAMENTO COMMUNITY DEFAULT OFFLINE E CAPARRA COMMUNITY OPZIONALE

Usa `play_master.md` come contesto fisso. Leggi anche `pagamento_community.md`. NON modificare la logica di business fuori da quanto gia deciso. Mantieni il codice coerente con il repository reale.

Prima di iniziare devi leggere obbligatoriamente:
- `play_master.md`
- `STATO_PLAY_4.md`
- `pagamento_community.md`

Se `STATO_PLAY_4.md` non e `PASS`, fermati e non procedere.

Agisci come:
- Senior Prompt Engineer orientato all'implementazione reale
- Senior Software Architect pragmatico
- Senior Full-Stack Engineer su FastAPI + React + TypeScript
- Senior QA tecnico rigoroso

## Obiettivo della fase

Allineare il completamento del flusso community `/play` alle regole decise piu recenti:
- default reale: nessun pagamento online, nessuna caparra, booking automatica a 4/4, booking confermata, pagamento al campo
- opzione tenant-scoped: caparra community attivabile da admin con importo e timeout dedicati
- riuso del motore booking/payment esistente senza creare uno stack parallelo solo per `/play`

## Punto critico da trattare come centro della fase

Oggi il completamento 4/4 in `backend/app/services/play_service.py` crea una booking con:
- `status=CONFIRMED`
- `payment_provider=NONE`
- `payment_status=UNPAID`
- `deposit_amount=calculate_deposit(match.duration_minutes)`
- `created_by=f'play:{match.id}'`

La Fase 5 deve chiudere questo disallineamento con la decisione prodotto, senza rompere:
- reporting e tracciabilita gia esistenti basati su `created_by=play:<match_id>`
- flussi booking/admin/public gia presenti
- foundation notifiche, push e timezone tenant-aware chiusa in Fase 4

## Regole prodotto da rispettare

Default community da rendere reale nel codice:
- nessun checkout online nel percorso standard `/play`
- `deposit_amount=0`
- booking creata automaticamente quando la partita arriva a 4/4
- booking in stato `CONFIRMED`
- `payment_provider=NONE`
- pagamento al campo

Caparra community opzionale da introdurre:
- tenant-scoped
- default `OFF`
- campi minimi di configurazione: `enabled`, `deposit_amount`, `payment_timeout_minutes`
- valida solo per il flusso community `/play`

Se la caparra community e `ON`:
- crea la booking riusando il motore di pagamento esistente
- preferisci il riuso di `PENDING_PAYMENT` e dei relativi flussi/timeout gia presenti invece di introdurre un nuovo enum `PENDING_DEPOSIT`, salvo necessita tecnica strettamente motivata
- al pagamento completato la booking deve risultare `CONFIRMED`
- al timeout scaduto la booking deve risultare `EXPIRED`
- lo slot deve tornare coerente con il comportamento gia esistente del motore booking

Decisione operativa minima da imporre nel prompt per evitare ambiguita:
- nella prima iterazione il pagatore online e il player che completa il `4/4`, cioe quello che esegue il join conclusivo e riceve la risposta con la booking appena creata
- non introdurre split payment, cambio pagatore successivo, richiesta di pagamento a un player non presente nel flusso corrente o raccolta anagrafica extra dedicata solo a `/play`
- la risposta di completamento deve contenere il minimo necessario per consentire allo stesso player di avviare subito il checkout oppure di vedere una CTA di pagamento chiara e immediata
- se per supportare questo flusso serve estendere il payload `/play`, fallo nel modo piu piccolo coerente con i tipi e i contratti gia esistenti

Vincoli di prodotto e architettura:
- non introdurre split payment, multi-pagatore, wallet o logiche refund nuove dedicate a `/play`
- non cambiare la homepage booking pubblica `/` oltre al minimo necessario per riuso infrastrutturale
- non riaprire la logica notifiche di Fase 4, salvo eventuali aggiustamenti minimi di messaggistica se indispensabili
- non perdere la semantica audit di `created_by=f'play:{match.id}'`

## Integrazione obbligatoria col repo attuale

Lavora sui punti proprietari del comportamento, senza duplicare logica:
- `backend/app/services/play_service.py` per il completamento del match e la creazione booking finale
- `backend/app/services/settings_service.py` per la configurazione tenant-scoped
- `backend/app/api/routers/admin_settings.py` e schemi admin per esporre la configurazione
- `frontend/src/pages/AdminDashboardPage.tsx` con i relativi tipi/API per la UX minima admin
- `frontend/src/pages/PlayPage.tsx` e relativi tipi/API per il feedback/next step lato player

Riusa esplicitamente, dove sensato:
- `AppSetting` come storage tenant-scoped della configurazione
- `expire_pending_booking_if_needed`
- `start_payment_for_booking`
- disponibilita provider Stripe/PayPal gia esposta dal backend admin/public
- i contratti booking/payment gia presenti nel repository

Gestisci in modo fail-closed i casi incoerenti:
- se la caparra community e `ON` ma non esiste alcun provider online realmente disponibile, non lasciare una configurazione attiva ma non onorabile
- se il flusso richiede una scelta provider, esponi una UX minima coerente con i provider disponibili e riusa il pattern gia usato nel booking pubblico
- se il provider disponibile e uno solo, puoi selezionarlo automaticamente per ridurre attrito
- se i provider online disponibili sono piu di uno, la scelta deve avvenire nello stesso flusso del player pagatore definito sopra, senza aprire una gestione pagamenti separata o demandare la scelta all'admin

Nota importante di coerenza:
- il repository oggi non ha uno stato enum `PENDING_DEPOSIT`, ma ha gia `PENDING_PAYMENT`
- il repository oggi non espone ancora setting community-specifici nel pannello admin
- il prompt va eseguito scegliendo il minimo cambiamento coerente col codice reale, non la soluzione piu teorica

## UX minima richiesta

Lato admin chiudi almeno:
- toggle `caparra community attiva`
- importo caparra community
- timeout pagamento community
- feedback chiaro sul fatto che il default resta `OFF`

Lato `/play` chiudi almeno:
- messaggio coerente quando il quarto player completa il match e la booking va subito confermata senza caparra
- messaggio coerente quando il match completa una booking con caparra attiva e pagamento richiesto
- un percorso minimo e reale per avviare il checkout dal client che riceve la risposta di completamento, senza costruire una dashboard pagamenti dedicata
- se la caparra community e `ON`, rendi esplicito nella UX che il pagamento online richiesto riguarda il player che ha completato il `4/4` nella prima iterazione

Non serve una nuova sezione prodotto enorme: fai il minimo reale, chiaro e coerente.

## Test richiesti

Backend, almeno:
- configurazione default community `OFF` letta correttamente dalle settings tenant-scoped
- completamento match 4/4 con caparra `OFF`: booking `CONFIRMED`, `deposit_amount=0`, `payment_provider=NONE`, `payment_status=UNPAID`
- completamento match 4/4 con caparra `ON`: booking in pending coerente col motore esistente e timeout rispettato
- completamento match 4/4 con caparra `ON`: la risposta `/play` identifica in modo coerente il player pagatore della prima iterazione e consente l'avvio del checkout senza passaggi manuali extra
- conferma del pagamento caparra community con riuso del percorso esistente di pagamento/mock payment se gia presente nei test
- scadenza caparra community con booking `EXPIRED`
- validazione fail-closed quando la caparra community viene attivata senza provider online disponibili
- nessuna regressione sui percorsi `/play` gia coperti nelle fasi precedenti

Frontend, se toccato:
- test mirati su `AdminDashboardPage` per lettura/salvataggio delle nuove impostazioni
- test mirati su `PlayPage` per feedback utente sul completamento offline standard e sul percorso con caparra
- se introduci scelta provider o CTA checkout, coprila con test espliciti
- se entrambe le opzioni provider sono disponibili, copri con test il comportamento minimo deciso per la selezione del provider da parte del player pagatore
- build frontend finale

Per i test backend usa il Python del repo:
- `D:/Padly/PadelBooking/.venv/Scripts/python.exe`

## Verifica di fine fase obbligatoria

La fase passa solo se:
- il default community e davvero senza caparra e senza checkout online
- la caparra community opzionale e realmente configurabile per tenant e default `OFF`
- il percorso con caparra riusa il motore payment esistente senza introdurre eccezioni architetturali gratuite
- l'admin puo leggere e salvare la configurazione
- `/play` comunica in modo chiaro l'esito del completamento match
- i test mirati sono verdi
- non ci sono regressioni evidenti sui flussi `/play`, booking e payment gia esistenti

## File stato da produrre obbligatoriamente

Crea `STATO_PLAY_5.md` con almeno:
- esito `PASS` / `FAIL`
- regola default community implementata in modo finale
- configurazione admin introdotta e valori di default
- semantica scelta per lo stato pending della caparra community, con motivazione esplicita se riusi `PENDING_PAYMENT`
- regola esplicita sul pagatore della caparra community nella prima iterazione
- strategia provider adottata nel flusso `/play`
- file principali toccati backend/frontend
- validazioni realmente eseguite con esito
- `## Note operative finali`
- `## Backlog esplicito per una futura v2 notifiche mirate`

Le ultime due sezioni devono restare coerenti con `STATO_PLAY_4.md`:
- non cancellarle
- non riscriverle in modo scollegato dalla Fase 4
- se in Fase 5 non cambiano, riportalo esplicitamente

## Fuori scope approvato

Questa fase non deve assorbire lavorazioni gia separate:
- revoca/rotazione share token, descritta in `revoca_token.md`
- KPI/reportistica dedicata o source separato per booking nate da `/play`, descritti in `kpi.md`

Questi temi restano autonomi e non devono bloccare il `PASS` della Fase 5, salvo priorita esplicita diversa richiesta dal prodotto.