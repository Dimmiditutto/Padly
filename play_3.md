# PROMPT FASE 3 - JOIN/CREATE/COMPLETE HARDENING E SHARE FLOW REALE

Usa `play_master.md` come contesto fisso. NON modificare la logica di business. Mantieni il codice coerente.

Prima di iniziare devi leggere obbligatoriamente:
- `play_master.md`
- `STATO_PLAY_2.md`

Se `STATO_PLAY_2.md` non e `PASS`, fermati e non procedere.

## Obiettivo della fase

Chiudere la parte piu critica del dominio `/play`:
- join transazionale corretto
- creazione match con anti-frammentazione
- completamento al quarto player con booking finale coerente col motore esistente
- share match e onboarding self-service realmente utilizzabile
- leave/update/cancel nei limiti consentiti

## Punto critico da trattare come centro della fase

Il join del quarto giocatore e il punto piu delicato del modulo.

Devi implementarlo in modo deterministico con:
- transazione DB
- `SELECT ... FOR UPDATE` sulla riga `matches`
- vincolo unico su `match_players(match_id, player_id)`
- ricontrollo `player_count < 4` dentro la stessa transazione
- booking finale nella stessa transazione o nello stesso boundary consistente
- riuso del lock booking/court gia esistente se il motore booking attuale lo offre gia

## Creazione match con anti-frammentazione

Il prodotto non deve creare nuove partite se ne esistono gia di compatibili.

Implementa una strategia sobria e concreta, ad esempio:
- `POST /api/play/matches` con `force_create=false` di default
- se il backend trova match compatibili, non crea subito e restituisce suggerimenti strutturati
- il frontend propone di unirsi a quei match
- solo se l'utente conferma o usa `force_create=true`, crea davvero il match

Non introdurre AI, fuzzy logic opaca o ranking arbitrari.

## Booking finale del match completato

Devi chiudere in modo esplicito la strategia di booking finale coerente con il repository reale.

Regola:
- non usare il checkout pubblico esistente come side effect automatico se non e veramente coerente con il prodotto `/play`
- preferisci il percorso piu vicino alla booking manuale/admin, con source dedicato solo se serve davvero chiarezza di audit e reporting
- documenta chiaramente il comportamento finale su pagamento, stato booking e relazione tra `Match` e `Booking`

La decisione finale deve essere implementata e scritta in `STATO_PLAY_3.md`.

## Share flow reale

Chiudi il flusso di share match in modo utilizzabile:
- token pubblico controllato
- detail page della partita condivisa
- join diretto se il player e gia riconosciuto
- onboarding self-service se il player non e riconosciuto
- completamento del join in continuita dopo l'onboarding

## Regole di prodotto da rispettare

- un player non puo essere inserito due volte nello stesso match
- un match chiuso/full non puo accettare altri join
- leave e update sono consentiti solo entro regole chiare e documentate
- se il booking finale fallisce in modo consistente, lo stato del match non deve restare corrotto

## Test richiesti

Aggiungi test backend mirati almeno per:
- join concorrente sul quarto player
- doppio join dello stesso player
- match full non piu joinabile
- create match con suggerimento anti-frammentazione
- share token valido / invalido
- completamento con creazione booking finale

Se tocchi il frontend, aggiungi anche test per:
- flow suggerimento vs force create
- share match page -> onboarding -> join

## Verifica di fine fase obbligatoria

La fase passa solo se:
- i test mirati del flusso join/create/complete sono verdi
- la decisione su booking finale e coerente col repo esistente
- non ci sono buchi evidenti su lock, stato o idempotenza

## File stato da produrre obbligatoriamente

Crea `STATO_PLAY_3.md` con almeno:
- esito PASS / FAIL
- strategia finale adottata per booking completion
- nuovi enum o source eventualmente introdotti
- contratti API create/join/leave/share consolidati
- vincoli DB o unique constraint aggiunti
- rischi residui per la Fase 4