# FASE 8 — DATA GOVERNANCE OPERATIVA, EXPORT E DELETE GUIDATI

Includi: prompt_master.md + STATO_FASE_1.MD + STATO_FASE_2.MD + STATO_FASE_3.MD + STATO_FASE_4.MD + STATO_FASE_5.MD + STATO_FASE_6.MD + STATO_FASE_7.MD se esiste + istanze.md

## Obiettivo

Trasformare la data governance da sola documentazione a workflow applicativi minimi e guidati, senza fingere di avere una compliance completa o automatismi che il repository non supporta.

Questa fase deve restare concreta:

- export essenziale dei dati tenant o cliente finale quando e ragionevole farlo
- workflow guidato di delete o anonymization minima dove ha senso introdurla senza rompere i vincoli operativi e fiscali
- retention minima applicata almeno ai log e ai dati tecnici che il progetto puo realisticamente pulire

## Stato reale da considerare prima di scrivere codice

Fatti verificati nel repository reale:

- [docs/operations/DATA_GOVERNANCE.md](docs/operations/DATA_GOVERNANCE.md) documenta export/delete come manuali o semi-guidati
- non esistono endpoint applicativi chiari per export tenant/customer, cancellazione guidata o anonimizzazione strutturata
- non risultano job applicativi di purge/retention per log tecnici o email log
- il database resta shared-database e il restore tenant-only non e un restore fisico nativo

## Aree da coprire

### 1. Export dati essenziali guidato

Implementa una superficie minima interna, chiara e sicura, per esportare dati essenziali.

Vincoli:

- evitare un export totale e non filtrato del database
- supportare almeno un export tenant-scoped o customer-scoped realmente utile
- includere relazioni indirette dove necessario, per esempio pagamenti booking via booking_id
- chiarire bene cosa e dato del tenant e cosa e dato del cliente finale

### 2. Delete o anonymization minima guidata

Introduci un workflow minimo e prudente.

Vincoli:

- non fare hard delete distruttive senza protezioni
- preferire anonymization o soft-delete dove il dominio lo richiede
- rispettare il fatto che alcune entita possono avere obblighi fiscali, contabili o di contestazione pagamenti
- se alcuni casi restano manuali, dichiararlo esplicitamente

### 3. Retention applicata ai dati tecnici realisticamente pulibili

Implementa purge minima dove ha senso farlo davvero.

Target candidati:

- `email_notifications_log`
- eventi tecnici di webhook, se coerente con retention dichiarata
- eventuali log applicativi persistiti nel database se presenti

Non toccare dati di booking o commerciali se il modello di retention non e ancora sufficientemente chiaro e sicuro.

## Regole

- non vendere come GDPR-complete workflow che sono solo minimi o interni
- non introdurre una compliance suite gigante o un motore policy generico
- non rompere l'integrita referenziale nel database shared-database
- non cancellare dati di dominio critici solo per soddisfare il prompt

## Test e verifiche obbligatorie

- test di export tenant/customer sui casi supportati
- test di delete/anonymization sui casi supportati
- test di retention o purge sui dati tecnici scelti
- verifica che il tenant legacy default continui a funzionare
- PASS/FAIL reale su test mirati

## Output obbligatorio

- file toccati
- workflow export/delete/anonymization introdotti
- policy di retention effettivamente applicate nel codice
- limiti espliciti di cio che resta manuale
- test aggiunti o aggiornati
- PASS/FAIL reale
- STATO_FASE_8.MD con:
  - workflow ora automatizzati o guidati
  - workflow ancora manuali
  - rischi residui lato governance dati
  - prerequisiti per la fase seguente