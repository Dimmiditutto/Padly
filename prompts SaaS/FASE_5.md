# FASE 5 — LAYER COMMERCIALE SAAS: PIANI, SUBSCRIPTION E CONTROL PLANE MINIMO

Includi: BLOCCO_COMUNE_V5 + STATO_FASE_1.MD + STATO_FASE_2.MD + STATO_FASE_3.MD + STATO_FASE_4.MD

## Obiettivo

Trasformare il prodotto tenant-aware in un SaaS monetizzabile e governabile, senza confondere la subscription del tenant con i pagamenti booking del cliente finale.

Questa fase deve introdurre il layer commerciale minimo serio:
- piani
- subscription
- trial e stati account
- provisioning tenant
- control plane minimo della piattaforma

## Regole non derogabili

- separa nettamente booking payments e billing SaaS
- preferisci Stripe Billing se il repository usa gia Stripe e questa e la strada piu semplice e robusta
- non forzare PayPal su casi d'uso subscription se non c'e un reale beneficio tecnico
- mantieni webhooks idempotenti
- non bloccare brutalmente un tenant senza una policy chiara di grace period, stato past_due o sospensione controllata
- conserva il modello shared database anche per plan, subscription e audit commerciale, salvo eccezione tecnica reale e documentata

## Dominio target minimo

Adatta i nomi al repository reale, ma copri almeno:

### Plan
Campi minimi attesi:
- id
- code unique
- name
- price_amount
- billing_interval
- is_active
- feature_flags o limiti equivalenti solo se davvero utili

### TenantSubscription / ClubSubscription o equivalente
Campi minimi attesi:
- id
- tenant_id o club_id
- plan_id
- provider
- provider_customer_id
- provider_subscription_id
- status
- trial_ends_at nullable
- current_period_end nullable
- cancelled_at nullable
- created_at
- updated_at

### Billing event o estensione coerente delle tabelle esistenti
Usa la soluzione piu coerente col repository reale per:
- idempotenza webhook billing
- audit eventi commerciali
- troubleshooting dei flussi subscription

Anche il layer commerciale deve restare tenant-aware nello stesso database condiviso, con chiavi e query coerenti.

## Funzionalita minime

### Provisioning tenant
- creazione tenant con piano iniziale o trial
- bootstrap admin owner coerente col tenant
- stato iniziale account chiaro

### Enforcement commerciale
- regole chiare su cosa succede in trial, active, past_due, suspended e cancelled
- enforcement non distruttivo sui flussi pubblici e admin
- eventuale accesso solo lettura o banner di avviso quando appropriato

### Control plane minimo
- vista o endpoint platform per elencare tenant, piano, stato subscription e segnali operativi minimi
- possibilita di sospendere o riattivare un tenant solo se davvero necessaria e con audit

### Self-service tenant
- se coerente col repository, link a billing portal o flow self-service per aggiornare la subscription
- visualizzazione stato piano nella UI admin del tenant o in una UI platform dedicata

## Endpoint minimi

Definisci solo quelli strettamente necessari. Possibili superfici:
- endpoint platform protetti per tenant e subscription
- webhook billing provider
- endpoint per creare sessione checkout o portal del SaaS
- eventuale endpoint admin tenant per leggere il proprio stato piano

Adatta i nomi ai router reali e mantieni coerenza col modello auth introdotto prima.

## Test obbligatori

- provisioning di un nuovo tenant con piano o trial
- webhook billing idempotente
- cambio di stato subscription aggiornato correttamente
- enforcement coerente su tenant non attivo o past_due
- separazione netta tra booking payment e billing SaaS
- control plane o endpoint platform protetti correttamente
- zero regressioni evidenti sui flussi legacy toccati

## Output obbligatorio

- file backend e frontend toccati
- schema reale di piani e subscription
- strategia provider billing scelta e motivata
- regole di enforcement commerciale
- test nuovi
- PASS/FAIL reale
- STATO_FASE_5.MD con:
  - limiti del layer commerciale
  - policy stati subscription
  - superfici platform introdotte
  - rischi residui
