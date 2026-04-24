# PROMPT FASE 4 - NOTIFICHE V1, WEB PUSH FOUNDATION E PROFILO PROBABILISTICO

Usa `play_master.md` come contesto fisso.

Prima di iniziare devi leggere obbligatoriamente:
- `play_master.md`
- `STATO_PLAY_3.md`

Se `STATO_PLAY_3.md` non e `PASS`, fermati e non procedere.

## Obiettivo della fase

Chiudere la prima versione utile di attivazione e memoria del modulo `/play`:
- notifiche v1 semplici e deterministiche
- base web push realmente persistita
- eventi recenti a retention breve
- profilo probabilistico aggregato e leggero
- preferenze utente e log notifiche

## Perimetro funzionale

Implementa in modo concreto le entita minime, tenant-scoped quando necessario:
- `PlayerActivityEvent`
- `PlayerPlayProfile`
- `PlayerPushSubscription`
- `PlayerNotificationPreference`
- `NotificationLog`

La memoria deve restare compatta:
- eventi recenti con retention breve, target 90 giorni
- profilo aggregato incrementale
- decay leggero e purge automatico

## Regole prodotto da rispettare

- notifiche sempre deterministiche in v1
- canali: in-app sempre, web push come canale principale di attivazione
- niente email come canale principale community
- niente spam
- max 3 notifiche al giorno per utente
- priorita:
  1. match 3/4
  2. match 2/4
  3. match 1/4 solo con criterio
- filtro almeno per compatibilita livello in v1
- notifiche mirate solo dopo almeno 5 eventi utili

## Profilo probabilistico

Implementa una base semplice ma reale per:
- score giorni settimana
- score fasce orarie
- score compatibilita livello
- engagement score
- `declared_level`
- `observed_level`
- `effective_level`

La correzione del livello deve essere graduale e non impulsiva.

Non fare ML, recommendation engine opaco o logica black-box.

## Integrazione col repo attuale

- riusa scheduler esistente dove sensato
- non rompere email/reminder correnti
- non mescolare le notifiche booking esistenti con quelle `/play` senza una separazione chiara di template, routing e audit
- se introduci service worker o subscription browser, fallo nel modo piu leggero compatibile con il frontend attuale

## UX minima richiesta

Chiudi almeno:
- subscribe/unsubscribe push
- preferenze notifiche essenziali
- feedback utente sullo stato iscrizione notifiche

Non serve una notification center enorme: fai il minimo coerente e reale.

## Test richiesti

Aggiungi test almeno per:
- registrazione e revoca push subscription
- frequency cap giornaliero
- selezione deterministica dei destinatari per match 3/4 e 2/4
- retention/purge degli eventi recenti
- aggiornamento incrementale del profilo aggregato
- non esposizione pubblica di `observed_level` e `effective_level` in UI o payload non interni

Se tocchi il frontend:
- test mirati per preferenze notifiche e subscribe flow
- build frontend finale

## Verifica di fine fase obbligatoria

La fase passa solo se:
- la base notifiche e usabile davvero
- la memoria utente e compatta e con retention
- i test mirati sono verdi
- non ci sono regressioni evidenti sui flussi `/play` gia chiusi nelle fasi precedenti

## File stato da produrre obbligatoriamente

Crea `STATO_PLAY_4.md` con almeno:
- esito PASS / FAIL
- modelli e job introdotti
- trigger notifiche chiusi in v1
- regole finali di frequency cap e compatibilita livello
- retention effettiva implementata
- backlog esplicito per una futura v2 notifiche mirate