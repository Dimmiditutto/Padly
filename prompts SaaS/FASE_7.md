# FASE 7 — SCALING OPERATIVO, TELEMETRIA MINIMA E ALLINEAMENTO STATO

Includi: prompt_master.md + STATO_FASE_1.MD + STATO_FASE_2.MD + STATO_FASE_3.MD + STATO_FASE_4.MD + STATO_FASE_5.MD + STATO_FASE_6.MD + istanze.md

## Obiettivo

Chiudere il gap piu urgente rimasto dopo FASE 6 senza introdurre piattaforme obbligatorie o architetture premature:

- preparare il rate limit a un deployment multi-instance in modo graduale e compatibile con locale/test
- introdurre telemetria operativa minima davvero utile al supporto e al go-live
- riallineare la documentazione di FASE 6 allo stato reale del codice dopo i fix post-verifica

Questa fase non deve diventare una migrazione infrastrutturale totale. Deve restare una patch architetturale pragmatica e incrementale.

## Stato reale da considerare prima di scrivere codice

Il repository reale oggi mostra questi fatti verificati:

- [backend/app/main.py](backend/app/main.py) usa ancora `request_log` in-memory e per-processo come backend del rate limit, anche se la chiave ora e corretta rispetto al tenant reale
- [backend/app/core/config.py](backend/app/core/config.py) non espone ancora configurazioni per un backend condiviso del rate limit o per telemetria operativa minima
- [backend/app/api/routers/payments.py](backend/app/api/routers/payments.py) ha un healthcheck corretto rispetto a database e scheduler, ma non espone ancora il backend del rate limit o segnali operativi aggregati minimi
- [backend/app/core/scheduler.py](backend/app/core/scheduler.py) ha logging contestuale migliore, ma non produce ancora una vista minima di stato operativo consumabile dal control plane
- [prompts SaaS/STATO_FASE_6.MD](prompts%20SaaS/STATO_FASE_6.MD) e parzialmente stale rispetto al codice reale post-verifica: descrive ancora il rate limit come basato su tenant hint e riporta conteggi test non piu aggiornati
- [istanze.md](istanze.md) definisce una regola decisionale esplicita: con 1 sola istanza il rate limit locale e ancora accettabile per partire; da 2 istanze in su serve un contatore condiviso

## Aree da coprire

### 1. Rate limit pronto per multi-instance, ma senza imporre costi prematuri

Implementa un backend di rate limit astratto e configurabile.

Questa area deve rispettare esplicitamente la regola decisionale contenuta in [istanze.md](istanze.md).

Requisiti minimi:

- mantenere supporto al backend locale in-memory per sviluppo, test e primi deploy economici
- introdurre un backend condiviso opzionale per ambienti multi-instance
- non rendere obbligatorio Redis o un servizio esterno in locale/test
- se il backend condiviso non e configurato, il sistema deve continuare a funzionare in modalita locale esplicita
- la chiave del rate limit deve continuare a usare il tenant reale risolto, non host o tenant hint grezzi
- il design deve essere abbastanza neutro da non legarsi in modo irreversibile a Railway o a un cloud specifico
- se il repository continua a operare in modalita single-instance, il backend locale deve restare la scelta di default e la piu economica
- il prompt non deve imporre l'attivazione immediata del backend condiviso: deve prepararlo e documentare chiaramente quando attivarlo, seguendo la formula di [istanze.md](istanze.md)

Nota di prodotto importante:

- questa fase deve preparare il terreno per un eventuale backend Redis-like condiviso, ma senza imporre il suo utilizzo immediato
- il repository oggi non e ancora deployato in produzione multi-instance, quindi la fase deve essere economicamente prudente
- il deliverable corretto non e "accendere Redis comunque", ma "rendere il sistema pronto a passare da 1 istanza a N istanze senza riscrivere il middleware"

### 2. Telemetria operativa minima, non un framework enorme

Introduci segnali operativi minimi riusando le superfici esistenti.

Obiettivi concreti:

- esporre in modo coerente il backend del rate limit attivo (`local` vs `shared` o naming equivalente)
- aggiungere uno snapshot operativo minimo leggibile dal control plane o da un endpoint protetto interno
- includere segnali utili come:
  - stato scheduler
  - modalita rate limit attiva
  - eventuali failure recenti rilevanti su billing/email se il repository gia offre fonti dati realistiche
  - eventuali contatori minimi utili, ma solo se hanno semantica affidabile
- non introdurre Prometheus/OpenTelemetry completi se il repository non li richiede davvero

### 3. Allineamento documentale della fase precedente

Aggiorna la documentazione che oggi non riflette piu esattamente il codice.

Minimo richiesto:

- aggiornare [prompts SaaS/STATO_FASE_6.MD](prompts%20SaaS/STATO_FASE_6.MD) allo stato reale post-fix
- riallineare i conteggi test reali e la descrizione del rate limit/healthcheck
- aggiornare i runbook o il README se il backend del rate limit diventa configurabile

## Regole

- non imporre una dipendenza infrastrutturale obbligatoria per gli ambienti locali o di test
- non sostituire l'intero middleware se basta estrarre il backend del contatore in un modulo dedicato
- non introdurre un sistema di metriche enorme o esterno se puoi ottenere il risultato con un piccolo layer interno
- non rompere il deploy attuale a istanza singola
- se una capability resta opzionale o dipendente da infrastruttura esterna, dichiaralo esplicitamente
- tratta [istanze.md](istanze.md) come vincolo di prodotto e costo: single-instance deve restare first-class, multi-instance deve essere un upgrade esplicito e configurabile

## Test e verifiche obbligatorie

- test sul backend locale del rate limit ancora verdi
- test sul backend condiviso o su un adapter fake/in-memory condiviso che dimostri semantica multi-instance coerente
- verifica che il tenant reale continui a guidare la chiave di rate limit
- test sul nuovo snapshot operativo o endpoint protetto interno
- verifica che locale/test non richiedano servizi esterni per partire
- PASS/FAIL reale sui test mirati
- se tocchi superfici globali di middleware/config, riesegui la suite backend completa

## Output obbligatorio

- file toccati
- backend di rate limit introdotti e loro modalita di attivazione
- regola decisionale finale su quando restare in locale e quando passare al backend condiviso, coerente con [istanze.md](istanze.md)
- segnali operativi o telemetria minima aggiunti
- documentazione aggiornata, incluso allineamento di STATO_FASE_6.MD
- test aggiunti o aggiornati
- PASS/FAIL reale
- STATO_FASE_7.MD con:
  - cosa e stato reso pronto per il multi-instance
  - cosa resta raccomandato per ambienti a 1 sola istanza
  - cosa resta opzionale o non attivato finche non esiste un deploy distribuito reale
  - rischi residui prima della fase successiva
  - prerequisiti per la fase seguente