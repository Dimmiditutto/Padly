# PROMPT MATCH ALERT, FASCE ORARIE FINI E MEMORIA FERIALI/FESTIVI

Agisci come un Senior Staff Software Architect, Senior Backend Engineer FastAPI/SQLAlchemy, Senior Frontend Engineer React/TypeScript e QA tecnico rigoroso.

Devi implementare nel repository reale una evoluzione del sistema Match Alert pubblico e della memoria notifiche privata Play, passando da bucket orari grossolani a fasce orarie piu fini, senza alterare la business logic gia approvata e senza riaprire perimetri gia chiusi.

Non fare refactor ampi. Mantieni patch minime, locali, backward-compatible e verificabili.

## Obiettivo operativo

Portare il sistema da:

- `morning`
- `afternoon`
- `evening`

a fasce orarie piu fini, con anche il concetto utente di `Tutti gli orari`, per:

1. i filtri Match Alert nella tab pubblica di `/clubs`
2. la memoria ad personam che aiuta il sistema privato `/play` a inviare notifiche in base agli orari maggiormente usati dal player

La memoria ad personam deve anche separare i dati preferenziali tra:

- feriali
- festivi

senza cambiare la logica di business esistente su canali, ranking, watchlist, digest e matching di base.

## Contesto reale gia verificato

Leggi e rispetta il contesto reale di questi file prima di modificare codice:

- `prompt_engineering.md`
- `STATO_PLAY_FINAL.md`
- `backend/app/services/public_discovery_service.py`
- `backend/app/schemas/public.py`
- `backend/app/models/__init__.py`
- `backend/app/services/play_notification_service.py`
- `frontend/src/types.ts`
- `frontend/src/pages/ClubDirectoryPage.tsx`
- `frontend/src/pages/PublicDiscoveryPages.test.tsx`
- `backend/tests/test_play_phase4.py`
- `backend/tests/test_play_phase7_public_discovery.py`

Fatti di partenza gia veri nel codice:

- il dominio discovery pubblico usa oggi solo `morning`, `afternoon`, `evening`
- discovery pubblico resta su feed persistito `IN_APP`; non introdurre web push pubblico
- il filtro discovery pubblico usa gia livello + fascia oraria
- la distanza in km viene gia usata solo per il digest vicino, non per la watchlist dei club seguiti
- la memoria privata `/play` usa oggi `weekday_scores`, `time_slot_scores` e `level_compatibility_scores`
- la UI pubblica di `/clubs` espone oggi una tab tecnica di discovery, ma il modello mentale utente da raggiungere e `Match Alert`
- nel repo non esiste oggi un calendario festivita dedicato e non va introdotta una nuova dipendenza esterna solo per questo lavoro, salvo blocker tecnico reale e giustificato

## Business logic da NON cambiare

Queste regole devono restare vere anche dopo il lavoro:

1. discovery pubblico e dominio privato `/play` restano separati
2. discovery pubblico continua a usare solo feed `IN_APP`
3. gli alert dei club seguiti restano filtrati da:
   - livello
   - fascia oraria
   e NON dalla distanza
4. il digest `vicino a te` resta filtrato da:
   - livello
   - fascia oraria
   - distanza massima
5. i canali privati `/play` non cambiano: `IN_APP` e `WEB_PUSH` privato restano quelli gia chiusi in `STATO_PLAY_FINAL.md`
6. non toccare logiche non correlate di booking, pagamenti, ranking pubblico, OTP, cookie, share token, admin o discovery web push
7. non introdurre nuove dipendenze se non strettamente indispensabili

## Modello utente da raggiungere nella UI pubblica

La tab di `/clubs` non deve piu raccontarsi in modo tecnico. Deve dire all utente:

Titolo:

`Match Alert`

Sottotitolo:

`Scegli livello, orari e distanza: Matchinn ti avvisa quando ci sono partite compatibili con le tue preferenze.`

Il modello mentale da rendere evidente e:

- dimmi che partite ti interessano
- Matchinn ti avvisa quando ne trova una compatibile

Non usare copy tecnici tipo:

- discovery pubblica
- sessione discovery persistente
- feed persistente
- attiva discovery pubblico

## Nuova tassonomia delle fasce orarie

Usa identificatori macchina stabili e sobri in inglese, con label utente in italiano.

### Bucket concreti da supportare

- `morning` -> `Mattina` -> 07:00-12:00
- `lunch_break` -> `Pausa pranzo` -> 12:00-14:30
- `early_afternoon` -> `Primo pomeriggio` -> 14:30-17:00
- `late_afternoon` -> `Tardo pomeriggio` -> 17:00-19:30
- `evening` -> `Sera` -> 19:30-23:30

### Concetto utente aggiuntivo

- `all_day` oppure equivalente solo come concetto UI di `Tutti gli orari`

Regola obbligatoria:

- `Tutti gli orari` non deve diventare un bucket di scoring o di persistenza separato se non serve davvero
- trattalo come shortcut UI che seleziona tutti i bucket concreti

### Regole di bucketizzazione temporale

Usa l orario locale del club o del match, come gia avviene oggi.

Applica questi confini:

- `07:00 <= t < 12:00` -> `morning`
- `12:00 <= t < 14:30` -> `lunch_break`
- `14:30 <= t < 17:00` -> `early_afternoon`
- `17:00 <= t < 19:30` -> `late_afternoon`
- `19:30 <= t < 23:30` -> `evening`

Poiche il sistema deve restare deterministico anche per eventuali orari fuori finestra, introduci un fallback esplicito e testato:

- prima di `07:00` -> `morning`
- da `23:30` in poi -> `evening`

Non introdurre bucket extra.

## Regola importante sulla distanza

Mantieni esplicitamente questa semantica:

- club seguiti -> filtrati per livello + fascia oraria, NON per km
- match vicino a te -> filtrati per livello + fascia oraria + distanza

Questa regola va preservata sia nel dominio sia nei test, senza regressioni semantiche.

## Requisito sulla memoria ad personam

La memoria che aiuta il sistema privato `/play` a inviare notifiche piu utili deve usare le nuove fasce orarie fini e separare i dati tra feriali e festivi.

### Vincolo chiave

Non cambiare la logica di scoring di business. Cambia solo la granularita dei bucket e il modo in cui la memoria viene organizzata e letta.

### Implementazione richiesta

Nel profilo notifiche/gioco del player:

- mantieni `weekday_scores` esistenti, salvo adattamenti minimi realmente necessari
- sostituisci l uso piatto di `time_slot_scores` con una struttura che separi almeno:
  - `weekday`
  - `holiday`

Esempio atteso di shape logica, anche se puoi scegliere naming leggermente diverso se piu coerente:

```json
{
  "weekday": {
    "morning": 0,
    "lunch_break": 0,
    "early_afternoon": 0,
    "late_afternoon": 0,
    "evening": 0
  },
  "holiday": {
    "morning": 0,
    "lunch_break": 0,
    "early_afternoon": 0,
    "late_afternoon": 0,
    "evening": 0
  }
}
```

### Definizione operativa di feriale/festivo per questa fase

Poiche nel repo non esiste oggi una infrastruttura festivita dedicata, non aggiungere calendari esterni o librerie nuove solo per questo.

Per questa implementazione usa una classificazione minima, esplicita e documentata:

- `weekday` = lunedi-venerdi
- `holiday` = sabato-domenica

Se trovi nel repo una utility gia consolidata per una distinzione migliore, puoi riusarla. Altrimenti non inventare complessita nuova.

## Compatibilita con i dati esistenti

Il repository reale ha gia dati e JSON legacy con i tre bucket vecchi. Devi mantenere backward compatibility.

### Public discovery subscriber

Oggi `PublicDiscoverySubscriber.preferred_time_slots` e JSON con bucket storici.

Richiesta:

- accetta dati legacy con chiavi `morning`, `afternoon`, `evening`
- normalizza i dati legacy verso i nuovi bucket senza rompere gli utenti esistenti
- se `afternoon` era selezionato, mappalo a:
  - `lunch_break`
  - `early_afternoon`
  - `late_afternoon`
- se la selezione legacy era vuota o equivalente a tutti i bucket, considera selezionati tutti i bucket nuovi

### PlayerPlayProfile time_slot_scores

Oggi `time_slot_scores` e una mappa piatta legacy.

Richiesta:

- implementa una normalizzazione backward-compatible che sappia leggere sia il formato legacy piatto sia il nuovo formato annidato per `weekday`/`holiday`
- non richiedere una migrazione schema se non serve: preferisci normalizzazione applicativa sul JSON esistente
- se devi convertire un vecchio score `afternoon` ai tre bucket fini, redistribuisci il valore in modo deterministico e con somma conservata quanto piu possibile
- non triplicare il peso dell afternoon legacy copiandolo identico su tre bucket

## UX target della tab Match Alert

Riorganizza la tab pubblica in modo chiaro per l utente.

### Sezione 1

Titolo:

`Filtri notifiche`

Campi:

- livello
- orari
- distanza massima

Testo di aiuto:

`Useremo questi filtri per mostrarti solo gli alert piu utili.`

Dettagli richiesti:

- `Livello` con default `Nessuna preferenza`
- `Orari` con `Tutti gli orari` e le nuove cinque fasce
- `Distanza massima` con default 25 km

### Sezione 2

Titolo:

`Club seguiti`

Testo:

`Ricevi alert quando nei club che segui si aprono partite compatibili, soprattutto a 2/4 o 3/4.`

Stato vuoto:

`Non segui ancora nessun club. Vai nella directory e segui quelli che ti interessano.`

CTA:

`Trova il club`

### Sezione 3

Titolo:

`Match vicino a te`

Testo:

`Ricevi alert per partite compatibili nei club entro la distanza scelta.`

Controlli richiesti:

- toggle o checkbox equivalente `Attiva alert vicino a me`
- `Distanza massima`
- bottone `Usa la mia posizione`

Privacy breve:

`La posizione serve solo per trovare club entro il raggio scelto.`

Vincolo UI obbligatorio:

- non mostrare latitudine e longitudine raw nella UI finale utente se non strettamente necessario come fallback tecnico non evitabile

### Sezione 4

Titolo implicito privacy e salvataggio

Checkbox:

`Accetto il trattamento dei dati per salvare i filtri e ricevere gli alert richiesti.`

CTA finale:

`Salva alert`

Non usare come CTA finale copy tecniche tipo `Attiva discovery pubblico`.

## Ambito tecnico richiesto

### Backend discovery pubblico

Adegua in modo minimo e coerente:

- `backend/app/schemas/public.py`
- `backend/app/services/public_discovery_service.py`
- eventuali router o serializer strettamente coinvolti

Obiettivi:

- validare e serializzare i nuovi bucket fini
- mantenere compatibilita legacy dei JSON discovery
- mantenere identica la semantica watchlist vs digest distanza
- aggiornare bucket helper e matching helper

### Backend memoria privata Play

Adegua in modo minimo e coerente:

- `backend/app/models/__init__.py` solo se strettamente necessario a livello di commenti, helper o shape documentata; evita migrazioni schema se il JSON esistente basta
- `backend/app/services/play_notification_service.py`

Obiettivi:

- introdurre bucket fini nella memoria oraria
- separare memoria `weekday` e `holiday`
- mantenere invariata la logica di scoring: stessi tipi di notifiche, stessi gate, stessa idea di ranking, solo granularita piu fine e lettura corretta del bucket di giorno

### Frontend pubblico

Adegua in modo minimo e coerente:

- `frontend/src/types.ts`
- `frontend/src/pages/ClubDirectoryPage.tsx`
- eventuali utilita o componenti strettamente coinvolti

Obiettivi:

- sostituire i tre bucket con i nuovi cinque bucket + shortcut `Tutti gli orari`
- riallineare copy da `Discovery pubblico` a `Match Alert`
- nascondere latitudine/longitudine dalla UI finale se non indispensabili
- mantenere compatibilita con i payload backend aggiornati

## Vincoli non negoziabili

- patch minime
- niente refactor ampi
- niente nuove dipendenze salvo blocker reale
- niente cambi al canale discovery pubblico: resta `IN_APP`
- niente cambi alla regola distanza della watchlist: resta fuori dai club seguiti
- niente cambi a booking, pagamenti, auth, OTP, community access, push privato o ranking pubblico non direttamente richiesti
- niente migrazioni schema se la soluzione puo stare nei JSON esistenti con compatibilita applicativa
- se una migrazione diventa davvero necessaria, giustificala tecnicamente e limita l impatto

## Test obbligatori

Aggiorna o aggiungi solo i test strettamente necessari per blindare il cambiamento.

### Backend discovery pubblico

Copri almeno:

- validazione dei nuovi bucket fini nello schema
- mapping backward-compatible da legacy `afternoon`
- corretta applicazione di livello + fascia oraria negli alert watchlist
- corretta applicazione di livello + fascia oraria + distanza nel digest nearby
- boundary test degli orari:
  - `11:59`
  - `12:00`
  - `14:29`
  - `14:30`
  - `16:59`
  - `17:00`
  - `19:29`
  - `19:30`

### Backend Play memory

Copri almeno:

- record della memoria oraria fine su eventi utili
- separazione `weekday` vs `holiday`
- compatibilita in lettura del vecchio JSON piatto `time_slot_scores`
- uso del bucket corretto nel ranking delle notifiche private

### Frontend

Copri almeno:

- rendering della tab `Match Alert`
- presenza di `Tutti gli orari` e delle cinque fasce nuove
- CTA finale `Salva alert`
- assenza di latitudine/longitudine raw nella UI finale
- mantenimento del flusso `/clubs` senza regressioni funzionali

## Strategia di consegna

Lavora in fasi locali e verificabili. Se ti aiuta, usa file stato dedicati; in ogni caso non procedere a patch ampie senza avere validato la fase precedente.

Ordine consigliato:

1. audit mirato dei file reali e definizione della nuova tassonomia
2. backend discovery pubblico con compatibilita legacy
3. backend memoria privata Play con separazione `weekday` / `holiday`
4. frontend tab `Match Alert`
5. test mirati e validazione finale

## Formato di output richiesto

Quando riporti il lavoro, usa questo ordine:

## 1. Prerequisiti verificati
- PASS / FAIL reale

## 2. Mappa del repository rilevante
- file reali trovati e superfici toccate

## 3. Gap analysis
- cosa nel codice attuale usa ancora i tre bucket legacy
- cosa e stato aggiornato

## 4. File coinvolti
- file modificati

## 5. Implementazione
- breve spiegazione concreta delle scelte
- dettaglio della compatibilita legacy adottata

## 6. Migrazioni e backfill
- indica esplicitamente se non e servita una migrazione schema
- descrivi la strategia di normalizzazione/backfill dei JSON legacy

## 7. Test aggiunti o modificati
- elenco test toccati

## 8. Verifica finale
- controlli eseguiti
- PASS / FAIL / NOT APPLICABLE
- criticita residue
- gate finale:
  - `FASE VALIDATA - si puo procedere`
  - `FASE NON VALIDATA - non procedere`

## 9. Stato finale compatto
- riassunto pronto per il passaggio di consegne

## Verifica qualita obbligatoria

Prima di chiudere:

- verifica che i nuovi bucket fini siano usati sia nella discovery pubblica sia nella memoria privata `/play`
- verifica che `Tutti gli orari` non introduca un bucket di scoring superfluo
- verifica che watchlist e digest mantengano la semantica originale della distanza
- verifica che la memoria privata distingua `weekday` e `holiday` senza rompere `weekday_scores` esistenti
- verifica che i JSON legacy con `morning/afternoon/evening` non si rompano
- verifica che non siano state introdotte dipendenze non necessarie
- segnala ogni ambiguita residua solo se realmente bloccante
- produci una soluzione direttamente utilizzabile nel repository reale