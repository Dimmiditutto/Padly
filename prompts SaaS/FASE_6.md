# FASE 6 — HARDENING SAAS, OPERATIONS E GO-LIVE READINESS

Includi: prompt_master.md + STATO_FASE_1.MD + STATO_FASE_2.MD + STATO_FASE_3.MD + STATO_FASE_4.MD + STATO_FASE_5.MD

## Obiettivo

Portare il progetto a un livello SaaS serio e operabile in produzione: osservabilita, sicurezza, supporto operativo, compliance minima e runbook chiari.

Questa fase non deve diventare un contenitore confuso. Concentrati solo sugli aspetti che rendono il prodotto davvero rilasciabile e governabile.

## Aree da coprire

### Osservabilita e audit
- logging strutturato con tenant_id, oppure club_id se questa e la tenant key scelta, request_id e segnali utili al debug
- audit piu leggibile per azioni admin e commerciali rilevanti
- healthcheck e segnali operativi coerenti col deployment reale

### Sicurezza applicativa
- revisione di cookie, CORS, security headers e dominio cookie in contesto multi-tenant
- rate limit con chiavi adatte a un SaaS multi-tenant
- controlli su accessi cross-tenant e ruoli piattaforma
- gestione sicura di env e segreti in produzione

### Operazioni e supporto
- runbook minimi per migrazioni, rollback, incident response e bootstrap di un nuovo tenant
- strumenti minimi di supporto per sospensione, riattivazione, reset password e troubleshooting email o billing
- backup e restore documentati in modo realistico

Nota operativa:
- i runbook devono assumere database unico condiviso
- backup, restore e troubleshooting devono spiegare chiaramente cosa e fattibile per singolo tenant in un contesto shared database e cosa richiede procedure applicative dedicate

### Compliance minima e data governance
- retention minima sensata per log e dati operativi, se coerente col progetto
- export o cancellazione guidata dei dati essenziali quando e gia ragionevole implementarla
- chiarezza su dati cliente finale vs dati del tenant

### Quality gates finali
- smoke test multi-tenant
- smoke test del default tenant legacy
- verifica delle migrazioni in sequenza
- verifica build frontend e backend su superfici toccate

## Regole

- non introdurre un framework di observability enorme se il repo richiede solo logging strutturato e qualche metrica chiave
- non proclamare il SaaS pronto se mancano runbook, backup o test minimi di isolamento
- non spezzare il deploy Railway corrente senza una motivazione forte e documentata
- se una misura resta manuale, dichiaralo esplicitamente e non venderla come automatizzata

## Test e verifiche obbligatorie

- logging o audit include il contesto tenant dove previsto
- protezioni cross-tenant verificate sui casi piu sensibili
- rate limit o protezioni operative non rompono i flussi core legittimi
- smoke test su booking pubblico, admin auth, settings tenant e billing state
- il default tenant legacy continua a funzionare
- PASS/FAIL reale su build, test e verifiche di fine fase

## Output obbligatorio

- file toccati
- miglioramenti operativi introdotti
- policy o runbook aggiunti
- test e smoke test aggiunti o aggiornati
- PASS/FAIL reale
- STATO_FASE_6.MD con:
  - cosa rende il SaaS realmente pronto o quasi pronto
  - cosa resta manuale o parziale
  - rischi residui prima del go-live
  - backlog post go-live consigliato
