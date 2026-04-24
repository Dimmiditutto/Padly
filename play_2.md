# PROMPT FASE 2 - FRONTEND `/play`, ONBOARDING E PAGINE PUBBLICHE COMMUNITY

Usa `play_master.md` come contesto fisso.

Prima di iniziare devi leggere obbligatoriamente:
- `play_master.md`
- `STATO_PLAY_1.md`

Se `STATO_PLAY_1.md` non e `PASS`, fermati e non procedere.

## Obiettivo della fase

Implementare la UX reale del modulo `/play` lato frontend e chiudere il wiring pubblico necessario per:
- `PlayPage`
- `InviteAcceptPage`
- `SharedMatchPage`
- identificazione player nel flusso di join/create
- sezione `MyMatches` quando il player e riconosciuto

Il tutto senza rompere:
- il booking pubblico esistente su `/`
- l'area admin attuale
- la propagazione tenant gia presente

## Route frontend richieste

Implementa o chiudi queste route frontend:
- `/c/:clubSlug/play`
- `/c/:clubSlug/play/invite/:token`
- `/c/:clubSlug/play/matches/:shareToken`

Alias opzionali solo se economici e sicuri:
- `/play` -> redirect al club di default
- `/play/invite/:token` -> redirect coerente solo se il tenant default e davvero disponibile

Non rimuovere `/`.

## Componenti attesi

Chiudi almeno questi componenti o equivalenti reali:
- `PlayPage`
- `MatchBoard`
- `MatchCard`
- `CreateMatchForm`
- `MyMatches`
- `JoinConfirmModal`
- `InviteAcceptPage`
- `SharedMatchPage`

Puoi aggiungere un `PlayerProfileSheet` minimale se serve davvero al flusso.

## Regole UX obbligatorie

La pagina `/play` deve riflettere la logica prodotto gia decisa:

- sezione principale con i match aperti, ordinati 3/4 -> 2/4 -> 1/4
- ogni card mostra almeno:
  - giorno
  - data
  - orario
  - campo
  - livello
  - numero giocatori
  - posti mancanti
  - note opzionali
  - bottone `Unisciti`
  - bottone `Condividi`
- sezione secondaria per creare una nuova partita
- sezione personale `Le mie partite` visibile solo se il player e riconosciuto

Non trasformare `/play` in una pagina slot-list generica: il focus e il consolidamento delle partite aperte.

## Onboarding e identita

Chiudi lato frontend e wiring API per:
- player gia riconosciuto via `GET /api/play/me`
- identificazione rapida quando prova a unirsi o creare un match
- onboarding invite accept con:
  - nome
  - livello dichiarato o `Nessuna preferenza`
  - checkbox privacy obbligatoria
- shared match page che mostra la partita e consente onboarding self-service se l'utente non e riconosciuto

Il nome prodotto lato UI e `nome profilo`, non `first_name`/`last_name`.

## Integrazione tenant-aware

Poiche il repo oggi usa tenant via query/header, la fase deve:
- leggere `clubSlug` dalla route param
- propagare il tenant slug alle API play in modo coerente con le utility gia esistenti
- non richiedere una rifondazione del backend routing pubblico

Se serve, estendi le utility tenant frontend invece di introdurne di parallele.

## Compatibilita con l'app attuale

- non alterare il flusso di booking tradizionale su `/`
- non cambiare la UX admin esistente salvo tocchi minimi indispensabili
- usa design system e componenti gia presenti dove possibile
- mantieni tono e qualita visuale coerenti con il frontend corrente

## Test richiesti

Aggiungi test frontend mirati almeno per:
- render di `/c/:clubSlug/play`
- ordine visivo delle card match
- identificazione richiesta quando l'utente prova a unirsi senza essere riconosciuto
- invite accept con privacy obbligatoria
- shared match page con player gia riconosciuto vs anonimo
- preservazione tenant nel routing `/c/:clubSlug/play`

Esegui almeno:
- test mirati delle nuove pagine/componenti
- `npm run build` se tocchi routing, types o contratti API

## Verifica di fine fase obbligatoria

La fase passa solo se:
- il frontend compila
- le nuove route funzionano senza rompere quelle correnti
- i test mirati frontend sono verdi
- l'identificazione player e il tenant propagation sono coerenti con `STATO_PLAY_1.md`

## File stato da produrre obbligatoriamente

Crea `STATO_PLAY_2.md` con almeno:
- esito PASS / FAIL
- nuove route frontend chiuse
- pagine/componenti creati
- contratti API effettivamente usati dal frontend
- modal/sheet di identificazione usato
- eventuali deviazioni da `STATO_PLAY_1.md`
- rischi residui per la Fase 3