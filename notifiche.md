# PROMPT NOTIFICHE - CERCA GIOCATORI + CONDIVISIONE WHATSAPP PER /play

Agisci come:
- Senior Prompt Engineer orientato all'implementazione reale
- Senior UX Specialist senior orientato a funnel, chiarezza CTA e zero ambiguita
- Senior Full-Stack Engineer su FastAPI + React + TypeScript
- Senior QA tecnico rigoroso

Il tuo compito non e fare teoria. Devi guidare una implementazione reale, piccola ma forte, del modulo `/play` nel repository corrente di PadelBooking, senza rompere il codice gia chiuso e senza reinventare foundation che esistono gia.

## Prima di iniziare devi leggere obbligatoriamente

- `play_master.md`
- `prompt_play_final.md`
- `STATO_PLAY_FINAL.md`
- `backend/app/models/__init__.py`
- `backend/app/services/play_service.py`
- `backend/app/services/play_notification_service.py`
- `backend/app/api/routers/play.py`
- `backend/app/schemas/play.py`
- `frontend/src/App.tsx`
- `frontend/src/pages/PlayPage.tsx`
- `frontend/src/pages/SharedMatchPage.tsx`
- `frontend/src/components/play/MatchCard.tsx`
- `frontend/src/services/playApi.ts`
- `frontend/src/types.ts`
- `backend/tests/test_play_phase3.py`
- `backend/tests/test_play_phase4.py`
- `frontend/src/pages/PlayPage.test.tsx`

## Obiettivo prodotto

Implementare in modo coerente con il repository reale due funzioni distinte ma complementari del modulo `/play`:

1. `Condividi`
   - condivisione manuale del match
   - supporto a copia link
   - supporto a WhatsApp tramite fallback `wa.me/?text=...`
   - eventuale uso di `navigator.share` quando disponibile, ma senza dipendere da esso

2. `Cerca giocatori`
   - trigger manuale delle notifiche private del modulo `/play`
   - uso dei canali gia esistenti `IN_APP` e `WEB_PUSH`
   - riuso della logica esistente di matching per livello, fascia oraria, deduplica e preferenze

Il principio prodotto da rispettare e questo:

- `Condividi` = diffusione volontaria del link del match
- `Cerca giocatori` = attivazione intenzionale della macchina notifiche Matchinn

Non mischiare i due concetti in una sola CTA.

## Funnel target da rendere forte

Il funnel da sostenere e questo:

- creo match
- condivido su WhatsApp
- altri aprono il link pubblico
- entrano nella community se non sono gia dentro
- si uniscono al match

Questo funnel deve restare semplice, leggibile e coerente con la UX attuale del repo.

## Contesto reale gia verificato nel repository

Questi fatti sono gia veri nel codice e vanno trattati come ground truth:

- il repository ha gia una foundation di share token per i match Play
- il model `Match` ha gia:
  - `public_share_token_hash`
  - `public_share_token_nonce`
  - `public_share_token_created_at`
  - `public_share_token_revoked_at`
- esiste gia la route frontend canonica della pagina match condivisa:
  - `/c/:clubSlug/play/matches/:shareToken`
- esiste gia un alias frontend semplice:
  - `/play/matches/:shareToken`
  - che oggi redirige verso la route canonica club-specifica
- esiste gia il backend API per leggere il match condiviso:
  - `GET /api/play/shared/{share_token}`
- oggi i pulsanti `Condividi` su `PlayPage` e `SharedMatchPage` copiano solo il link negli appunti
- oggi esiste gia la pagina `SharedMatchPage` con flusso di identificazione e join
- oggi esiste gia il motore notifiche private `/play` con:
  - scoring per livello
  - scoring per fascia oraria
  - scoring per feriale/festivo
  - preferenze per `IN_APP` e `WEB_PUSH`
  - deduplica per match/kind
  - cap giornaliero
  - dispatch schedulato e anche triggerato in alcuni punti del lifecycle dei match
- oggi la shared page espone una card abbastanza ricca, compresi nomi partecipanti e creator; per questa feature il perimetro pubblico deve diventare piu sobrio e privacy-safe

## Decisioni gia prese e da NON rimettere in discussione

1. `Condividi` resta una CTA separata da `Cerca giocatori`.
2. WhatsApp non deve essere un invio automatico server-side o client-side: deve essere solo un link di uscita utente verso `wa.me/?text=...`.
3. Il link pubblico del match deve usare un token opaco e non deve mai esporre `match_id`, informazioni incrementali o dati personali.
4. La pagina pubblica del match deve restare coerente con la route e la UX attuali del repository.
5. Il join controllato dalla shared page deve restare il punto di atterraggio principale del funnel.
6. La nuova CTA `Cerca giocatori` deve riusare il motore notifiche privato esistente e non creare un secondo sistema parallelo.
7. Lo stesso link pubblico del match deve poter essere condiviso almeno da:
  - creatore del match
  - altri partecipanti gia entrati nel match
  - club ospitante tramite una superficie club/admin coerente col repo
8. Creator, partecipanti e club devono riusare lo stesso `share_token` attivo del match: non creare token diversi per attore.

## Regole obbligatorie sul token pubblico del match

Il requisito business e: ogni match deve avere un `public_share_token` sicuro.

Nel repository reale questa foundation esiste gia. Quindi:

- non creare una seconda famiglia di colonne o una seconda strategia token parallela
- non persistere in chiaro un nuovo token pubblico permanente se non e strettamente necessario
- considera il concetto business `public_share_token` come gia coperto dalla foundation esistente hash + nonce + revoca
- se vuoi migliorare naming o chiarezza nei payload, fallo in modo backward-compatible e senza introdurre doppie source of truth

Regole non negoziabili:

- non usare `match_id` come link pubblico
- token opaco
- token revocabile
- token invalido se il match viene cancellato
- nessun dato personale nell'URL
- nessun nome player, telefono, email o ID interno nel link
- route canonica pubblica coerente con il frontend attuale:
  - `/c/:clubSlug/play/matches/:shareToken`

Preferenza forte:

- mantieni come API backend `GET /api/play/shared/{share_token}` se basta davvero
- non creare nuovi endpoint pubblici duplicati solo per cambiare naming della route frontend

## Regole obbligatorie di validita del link pubblico

Il link pubblico deve essere leggibile solo quando ha senso prodotto e privacy.

Regola minima richiesta:

- match futuro
- token non revocato
- match non cancellato
- stato ammesso: `OPEN` oppure `FULL` secondo il rendering definito sotto

Comportamento richiesto:

- `OPEN`
  - la pagina e leggibile
  - la CTA primaria e `Unisciti` oppure `Identificati per unirti` se il player non e riconosciuto
- `FULL`
  - la pagina puo restare leggibile in sola consultazione
  - non deve proporre join
  - deve comunicare chiaramente che la partita e completa
- `CANCELLED`, token revocato o link non piu valido
  - risposta sobria di non disponibilita, coerente con il comportamento attuale del repo

Se il codice reale impone una regola ancora piu stretta per motivi di consistenza con booking finale, applicala nel modo piu piccolo possibile e documentala. Non allargare la leggibilita pubblica a stati non necessari.

## Specifica UX di `Condividi`

`Condividi` deve essere una CTA utente, non una side effect automatica.

Comportamento richiesto:

- al click non limitarti piu a copiare subito il link
- mostra una piccola action sheet, popover o menu coerente con la UI attuale, con opzioni esplicite

Opzioni richieste:

- `WhatsApp`
- `Copia link`

Opzione facoltativa ma consigliata:

- `Condividi con app`
  - solo se `navigator.share` e disponibile realmente

Regole UX:

- niente modali pesanti se basta un menu leggero
- niente nuovo design system: riusa primitive e classi gia presenti nel repo
- il testo deve essere chiaro e non tecnico
- non cambiare il significato della CTA: l'utente deve capire che sta diffondendo un link del match

### Matrice permessi obbligatoria di `Condividi`

Il medesimo link pubblico deve poter essere inviato almeno da questi tre attori:

- creatore del match
- ogni partecipante gia dentro il match
- club in cui si svolge la partita, tramite la piu piccola superficie club/admin gia coerente col repository

Regole obbligatorie:

- non generare token distinti per creator, partecipanti e club
- il club puo condividere solo i match del proprio club, non di altri club
- se il repo richiede una superficie admin dedicata per il club, implementala nel modo piu piccolo possibile senza rifondare l'area admin
- se un utente non e creator, non e partecipante e non opera per il club ospitante, non trattarlo come attore privilegiato di share nelle superfici private

### Messaggio WhatsApp precompilato

Il messaggio precompilato deve essere immediato, leggibile e pronto per l'inoltro su WhatsApp.

In questo caso sono ammessi i nomi visualizzati dei partecipanti attuali, ma solo nel testo del messaggio generato da una CTA utente consapevole dentro il contesto privato/community.

I nomi dei partecipanti NON devono comparire:

- nel link
- nell'URL
- nel payload pubblico della shared page
- nella pagina pubblica condivisa

Formato richiesto, in questo ordine:

- giorno + data
- ora
- livello
- nomi dei partecipanti attuali
- club
- chiusura finale: `Chi gioca?`
- link pubblico nell'ultima riga

Usa emoji sobrie e stabili per rendere il messaggio piu leggibile su WhatsApp.

Esempio di tono atteso:

```text
🎾 Matchinn
📅 {weekday} {date}
🕒 {time}
🏷️ Livello {level}
🎾 {participantNames}
📍 {clubName}

Chi gioca?
{url}
```

Vincoli:

- non includere telefono
- non includere email
- includi solo i nomi visualizzati dei partecipanti gia presenti nel match
- non includere note private del match
- non trasformare il messaggio in un testo promozionale lungo: deve restare breve e inoltrabile
- costruisci il link WhatsApp con `https://wa.me/?text=` e `encodeURIComponent(...)`
- non usare automazioni di invio automatico WhatsApp
- non usare provider esterni o API WhatsApp Business

## Specifica UX della pagina pubblica del match condiviso

La shared page deve restare coerente con il codice e la UX attuali, ma diventare piu pulita e piu pubblica.

La pagina pubblica deve mostrare almeno:

- club
- data
- ora
- livello
- stato `1/4`, `2/4`, `3/4`, `4/4`
- CTA primaria coerente con lo stato

La CTA primaria deve essere:

- `Unisciti` se il match e `OPEN` e il player e gia identificato
- `Identificati per unirti` se il match e `OPEN` ma il player non e ancora riconosciuto
- assente o disabilitata con copy chiaro se il match e `FULL`

Vincoli di privacy della pagina pubblica:

- non esporre `creator_profile_name`
- non esporre note private del match
- non esporre ID interni, riferimenti booking, token raw, telefono o email
- l'unico eventuale nome umano accettabile nel flusso pubblico e il nome del viewer gia identificato in feedback locale, non nel payload pubblico del match

Vincoli di coerenza UX:

- mantieni brand, shell e tono di `SharedMatchPage`
- non creare una nuova pagina separata se la route attuale basta gia
- mantieni il flusso di identificazione/join gia approvato

## Specifica funzionale di `Cerca giocatori`

`Cerca giocatori` deve essere una CTA distinta, visibile nel contesto privato `/play`, non sulla pagina pubblica condivisa.

Scopo:

- permettere al gestore del match di attivare una ricerca mirata di player compatibili
- usare il motore notifiche privato gia esistente
- non usare WhatsApp

### Dove deve comparire

Posizionamento preferito:

- nei match gestibili del player dentro la `PlayPage`
- nello stesso cluster di azioni dove oggi esistono gia `Condividi`, `Rigenera link` e `Disattiva link`

Regola permessi preferita:

- riusa lo stesso envelope di permessi gia usato per azioni gestionali del match come revoke/rotate share token
- non introdurre un nuovo modello autorizzativo se non strettamente necessario

### Quando deve essere disponibile

La CTA deve comparire solo se il match e:

- `OPEN`
- futuro
- non cancellato
- con posti ancora disponibili
- gestibile dal player corrente secondo le regole gia chiuse del repo

La CTA non deve comparire o deve risultare disabilitata se il match e:

- `FULL`
- cancellato
- nel passato
- non gestibile dal player corrente

### Cosa deve fare backend

Implementa un trigger manuale piccolo e chiaro, ad esempio:

- `POST /api/play/matches/{match_id}/search-players`

Il trigger deve:

- riusare la logica esistente di `dispatch_play_notifications_for_match`
- rispettare preferenze `IN_APP` e `WEB_PUSH`
- rispettare compatibilita livello
- rispettare scoring su fascia oraria
- rispettare deduplica gia esistente
- rispettare cap giornaliero gia esistente
- restituire un risultato leggibile per la UI

Non costruire un secondo motore di matching o una nuova tabella campagne se non serve davvero.

### Guard rail obbligatori per `Cerca giocatori`

Il bottone non deve diventare spam.

Quindi aggiungi un controllo esplicito di cooldown per match.

Default richiesto:

- cooldown di 15 minuti per match

Preferenza implementativa:

- se puoi, registra l'azione in modo leggero usando infrastruttura gia esistente, ad esempio `PlayerActivityEvent` o un audit minimo coerente col dominio
- evita nuove tabelle se basta una traccia leggera

Se il repo richiede un micro-campo dedicato sul match per evitare query ambigue, aggiungilo solo se davvero piu semplice della soluzione event-based.

### Risposta richiesta del trigger manuale

La risposta API per `Cerca giocatori` deve essere utile alla UI e sobria.

Minimo richiesto:

- `message`
- `notifications_created`
- `cooldown_remaining_seconds` quando applicabile
- eventuale match aggiornato se serve davvero a riallineare lo stato della card

Comportamento UX atteso:

- se sono state create notifiche: messaggio positivo tipo `Abbiamo avvisato X player compatibili.`
- se nessun nuovo player e notificabile: messaggio informativo, non errore
- se il cooldown e attivo: messaggio chiaro con attesa residua

## Regola importante: non duplicare la logica notifiche gia esistente

Il repo reale ha gia un sistema notifiche private `/play` maturo.

Quindi:

- non reimplementare scoring da zero
- non creare una seconda funzione di selezione candidati parallela a quella esistente
- non introdurre un canale WhatsApp dentro `Cerca giocatori`
- usa il motore esistente e aggiungi solo il minimo strato manual trigger + guard rail + UX

## Contratti e naming da preservare

Preserva il piu possibile i contratti attuali.

In particolare:

- il frontend oggi usa `share_token`
- la pagina canonica e gia `/c/:clubSlug/play/matches/:shareToken`
- il backend espone gia `GET /api/play/shared/{share_token}`

Quindi:

- non rinominare in massa `share_token` in `public_share_token` se non c'e un motivo forte
- se il business vuole il nome `public_share_token`, trattalo come naming concettuale oppure aggiungi un alias backward-compatible, ma evita breaking changes inutili

## File preferiti da toccare

Lavora in modo locale e sobrio. I punti di ingresso naturali sono:

### Backend

- `backend/app/services/play_service.py`
- `backend/app/services/play_notification_service.py`
- `backend/app/api/routers/play.py`
- `backend/app/schemas/play.py`
- `backend/app/models/__init__.py` solo se serve davvero per enum/eventi/campi minimi

### Frontend

- `frontend/src/pages/PlayPage.tsx`
- `frontend/src/pages/SharedMatchPage.tsx`
- `frontend/src/components/play/MatchCard.tsx`
- `frontend/src/services/playApi.ts`
- `frontend/src/types.ts`

Se serve per evitare duplicazione, puoi aggiungere un helper piccolo e dedicato, ad esempio:

- una utility per costruire il messaggio/link WhatsApp
- un piccolo componente condiviso per il menu di share

Ma evita refactor larghi.

## Cose da NON fare

- non rifondare la shared page
- non creare una nuova app o un nuovo modulo separato
- non introdurre invio automatico su WhatsApp
- non introdurre provider esterni WhatsApp
- non esporre nomi giocatori o dati privati nella pagina condivisa pubblica
- non rompere rotate/revoke share token gia esistenti
- non toccare pagamenti community
- non toccare ranking pubblico, discovery pubblico o booking pubblico fuori da cio che e strettamente necessario
- non allargare il perimetro a chat, email blast, SMS o campagne

## Test obbligatori

### Backend

Devi aggiungere o aggiornare test che dimostrino almeno:

1. il link pubblico del match resta opaco e non deriva da `match_id`
2. il token viene considerato non disponibile quando il match viene cancellato o il token e revocato
3. la pagina/shared API pubblica non espone nomi partecipanti, creator, note private, telefono o email
4. il rendering/contratto del match condiviso distingue correttamente `OPEN` e `FULL`
5. il nuovo trigger `Cerca giocatori` richiama il motore notifiche esistente e non aggira deduplica o cap giornaliero
6. il cooldown del trigger manuale funziona davvero
7. un utente non autorizzato non puo lanciare `Cerca giocatori` su match non gestibili

### Frontend

Devi aggiungere o aggiornare test che dimostrino almeno:

1. `Condividi` non copia piu soltanto in modo implicito, ma offre l'uscita WhatsApp e la copia link
2. il link WhatsApp usa `wa.me/?text=` con testo codificato correttamente
3. il fallback `Copia link` continua a funzionare
4. la CTA `Condividi` e disponibile almeno a creatore, partecipanti gia dentro il match e club ospitante nelle rispettive superfici coerenti col repo
5. la shared page pubblica mostra solo i campi richiesti e non i nomi degli altri player
6. `Cerca giocatori` compare solo sui match corretti
7. `Cerca giocatori` mostra feedback coerente su successo, zero candidati e cooldown
8. non ci sono regressioni su join, rotate token, revoke token e shared route canonica

Preferenza forte sui file test:

- backend: estendi `backend/tests/test_play_phase3.py` e `backend/tests/test_play_phase4.py`
- frontend: estendi `frontend/src/pages/PlayPage.test.tsx` e crea una suite dedicata `frontend/src/pages/SharedMatchPage.test.tsx` se serve per tenere isolata la privacy del public share flow

## Verifiche reali obbligatorie

Se tocchi il backend, usa il Python del repo:

- `D:/Padly/PadelBooking/.venv/Scripts/python.exe`

Comandi minimi attesi:

- `D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_play_phase3.py tests/test_play_phase4.py -q --tb=short`
- `npm run test:run -- src/pages/PlayPage.test.tsx src/pages/SharedMatchPage.test.tsx`
- `npm run build`

Se una suite dedicata non esiste ancora, creala e dichiaralo esplicitamente nel report finale.

## Output obbligatorio

Rispetta questo ordine di output:

## 1. Prerequisiti verificati
- PASS / FAIL reali

## 2. Mappa del repository rilevante
- file reali letti
- superfici toccate

## 3. Gap analysis
- differenza tra comportamento attuale e target

## 4. File coinvolti
- file creati o modificati

## 5. Implementazione
- codice completo o patch complete

## 6. Migrazioni e backfill
- solo se realmente necessari
- spiega perche servono oppure perche sono evitabili

## 7. Test aggiunti o modificati
- elenco e motivazione

## 8. Verifica finale
- comandi eseguiti
- esito PASS / FAIL reale
- rischi residui reali

## 9. Gate finale
- `PROMPT VALIDATO - si puo implementare`
- oppure `PROMPT NON VALIDATO - non procedere`

## Regola finale di progettazione

Questa attivita deve produrre un incremento forte ma stretto.

La soluzione corretta non e:

- piu complessa del necessario
- piu larga del necessario
- piu invasiva del necessario

La soluzione corretta e:

- `Condividi` piu utile e piu virale grazie a WhatsApp + copia link
- `Cerca giocatori` chiaro, controllato e basato sull'infrastruttura notifiche gia presente
- shared page pubblica piu pulita, piu forte e piu privacy-safe
- zero regressioni sui flussi Play gia chiusi