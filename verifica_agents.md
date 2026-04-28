# verifica_agents.md

## Ruolo

Agisci come un Senior Software Architect, Implementation Lead, Google Ads Specialist senior, GA4 Specialist senior, GTM Specialist senior, Security Reviewer, Agent Platform Architect e Prompt Engineer senior.

Devi eseguire una verifica tecnica, funzionale e di sicurezza dell'intero codice dopo le integrazioni già applicate da Copilot sulla base dei prompt `agents.md`, `agents_1.md`, `agents_2.md`, `agents_3.md`, `agents_4.md`, `agents_5.md`, `agents_6.md`, `agents_7.md`, `agents_8.md` e `agents_n.md`.

Questa non è una nuova fase di implementazione.
Questa è una verifica finale post-integrazione.

L'obiettivo è stabilire se il codice attuale rende realmente operativi, efficaci e sicuri:

- l'agente Google Ads
- l'agente GA4
- l'agente GTM
- l'orchestratore / implementation lead
- il flusso cross-platform Ads ↔ GA4 ↔ GTM
- il workflow proposal → approval → execution
- gli output agentici verso frontend, API, report e storico decisionale

Devi verificare il codice reale, non ciò che i prompt promettono.

## Obiettivo principale

Verifica in modo completo ed esaustivo se, dopo le integrazioni già effettuate, il sistema è in grado di creare, modificare, integrare, diagnosticare e governare in modo completo, efficiente e sicuro una qualsiasi campagna Google Ads con relativa misurazione GA4/GTM.

In particolare devi verificare:

1. se i singoli agenti sono realmente efficaci e sicuri per espletare il compito di creare, modificare, integrare, diagnosticare e ottimizzare campagne Google Ads;
2. se l'orchestratore consente ai singoli agenti di interfaccarsi correttamente tra loro per gestire un flusso end-to-end Ads ↔ GA4 ↔ GTM;
3. se le capability implementate sono davvero raggiungibili dal runtime agentico e non solo dichiarate;
4. se le azioni write sono protette da approval, readiness check, validazione, audit trail e rollback/dry-run dove necessario;
5. se prompt agentici, tool registry, capability matrix, execution dispatcher, schema output, API e frontend sono coerenti;
6. se restano gap bloccanti per usare il sistema in modo professionale su campagne reali;
7. se i test esistenti dimostrano davvero la copertura funzionale oppure coprono solo casi parziali/mocked.

## Vincolo fondamentale

Non modificare codice applicativo.

Non correggere bug.

Non fare refactor.

Non cambiare business logic.

Non introdurre dipendenze.

Non modificare prompt agentici, schema, servizi, API, frontend o test.

Puoi creare o aggiornare solo file di audit/report Markdown, se necessario.

Se trovi problemi, devi documentarli con evidenze e proporre patch minime future, ma non applicarle.

## File di output obbligatori

Crea o aggiorna questi file:

- `REPORT_verifica_agents.md`
- `STATO_verifica_agents.md`

Non creare altri file salvo necessità motivata.

## Fonti obbligatorie da leggere prima

Leggi prima questi file, se presenti:

- `agents.md`
- `agents_1.md`
- `agents_2.md`
- `agents_3.md`
- `agents_4.md`
- `agents_5.md`
- `agents_6.md`
- `agents_7.md`
- `agents_8.md`
- `agents_n.md`
- `STATO_agents_1.md`
- `STATO_agents_2.md`
- `STATO_agents_3.md`
- `STATO_agents_4.md`
- `STATO_agents_5.md`
- `STATO_agents_6.md`
- `STATO_agents_7.md`
- `STATO_agents_8.md`
- `STATO_agents_9.md`
- eventuale report finale già prodotto nelle fasi precedenti

Se uno di questi file non esiste, dichiaralo esplicitamente nella sezione `Blind spot e file non trovati`.

## Aree codice da ispezionare

Cerca e analizza almeno queste aree, adattandoti alla struttura reale del repository:

- `backend/app/agents/`
- `backend/app/agents/prompts/`
- `backend/app/agents/tools/`
- `backend/app/agents/tools/registry.py`
- `backend/app/agents/contracts.py`
- `backend/app/agents/orchestrator.py`
- `backend/app/schemas/`
- `backend/app/schemas/agent_output.py`
- `backend/app/api/`
- `backend/app/api/approvals.py`
- `backend/app/services/`
- `backend/app/services/capability_matrix.py`
- `backend/app/services/cross_platform.py`
- `backend/app/services/campaign_binding.py`
- `backend/app/services/executions/`
- `backend/app/core/`
- `frontend/src/`
- `frontend/tests/`
- `docs/`
- `tests/`
- `backend/tests/`
- `.env.example`
- `README.md`
- file relativi a OAuth, Google APIs, Google Ads API, GA4 Data API, GA4 Admin API e GTM API

Se i nomi sono diversi, individua gli equivalenti reali.

## Regola di valutazione obbligatoria

Non usare mai la logica semplificata `tool presente = capability disponibile`.

Per ogni capability devi verificare separatamente questi layer:

1. `read tool exposed`
2. `proposal reachable`
3. `execute capable`
4. `approval protected`
5. `readiness checked`
6. `runtime materializable`
7. `orchestrator attachable`
8. `frontend/API consumable`
9. `tested`

Classifica ogni capability con uno di questi stati:

- `assente`
- `solo dichiarata`
- `read-only disponibile`
- `proposal disponibile ma execute assente`
- `execute-capable ma non proposal-reachable`
- `execute-capable e proposal-reachable`
- `approval-backed ma readiness incompleta`
- `materializzabile ma non orchestrata`
- `orchestrata ma non sicura`
- `completa e verificata`

Quando rilevi un gap, devi indicare quale layer manca davvero:

- manca il tool read-only
- manca il proposal layer
- manca l'execute layer
- manca il readiness check
- manca l'approval guardrail
- manca l'audit log
- manca il rollback/dry-run
- manca l'attach nel flusso orchestrator / campaign binding / measurement chain
- manca il consumo frontend/API
- manca copertura test reale

## Regola anti-falso positivo

Non dichiarare una capability come completa se:

- esiste solo nel prompt;
- esiste solo in `capability_matrix`;
- esiste solo come enum/action type;
- esiste solo come test mockato;
- esiste solo come funzione non chiamata;
- esiste solo come endpoint non collegato al runtime agentico;
- esiste solo come execute path senza proposal reachability;
- esiste solo come proposal senza readiness/approval;
- esiste solo come read tool senza mapping operativo;
- esiste nel backend ma non è usabile dal frontend o dall'orchestratore quando necessario.

## Metodo operativo

Procedi in 10 blocchi.

## Blocco 1 — Verifica esecuzione delle fasi precedenti

Verifica se Copilot ha prodotto o aggiornato i file stato/report previsti dalle fasi precedenti.

Controlla:

- presenza di `STATO_agents_1.md` fino a `STATO_agents_9.md`;
- gate `PASS` o `FAIL`;
- coerenza tra file stato e codice attuale;
- eventuali finding dichiarati come chiusi ma ancora aperti nel codice;
- eventuali gap dichiarati come implementati ma non realmente materializzati;
- eventuali modifiche non documentate.

Output richiesto:

| Fase | File stato | Gate | Claim principale | Evidenza nel codice | Stato verifica | Note |
|---|---|---|---|---|---|---|

## Blocco 2 — Verifica agente Google Ads

Verifica se l'agente Ads è realmente in grado di gestire una campagna Google Ads completa.

Devi controllare almeno:

### Lettura e diagnosi

- account collegati;
- MCC/client account;
- customer ID;
- currency/timezone;
- permessi e accessi;
- campagne;
- ad group;
- keyword;
- search terms;
- negative keyword;
- annunci RSA;
- asset;
- sitelink/callout/snippet;
- final URL;
- policy status;
- conversion actions;
- primary/secondary;
- conversion source;
- category;
- count setting;
- conversion window;
- bidding strategy;
- budget;
- performance metrics;
- impression share;
- lost IS budget/rank;
- learning status, se disponibile.

### Proposal e write

Verifica se può proporre e, dopo approval, eseguire:

- creazione campagna Search;
- modifica stato campagna;
- modifica budget;
- modifica bidding strategy;
- creazione/modifica ad group;
- creazione/modifica keyword;
- aggiunta negative keyword;
- creazione/modifica RSA;
- creazione/modifica asset;
- collegamento conversion goals;
- modifica conversion settings;
- esperimenti/bozze, se previsti;
- applicazione raccomandazioni solo dopo approval.

### Output richiesto Ads

| Capability Ads | Read | Proposal | Execute | Approval | Readiness | Orchestrator attach | Test | Stato | Evidenza | Gap |
|---|---|---|---|---|---|---|---|---|---|---|

## Blocco 3 — Verifica agente GA4

Verifica se l'agente GA4 è realmente in grado di leggere, diagnosticare e configurare la parte analytics necessaria a supportare campagne Google Ads.

Devi controllare almeno:

### Lettura e diagnosi

- account/properties;
- data streams;
- measurement ID;
- collegamenti Google Ads;
- timezone/currency;
- enhanced measurement;
- data retention;
- eventi;
- key events;
- parametri evento;
- custom dimensions;
- custom metrics;
- audience;
- traffico source/medium;
- campaign/session campaign;
- landing page;
- funnel intermedi;
- session key event rate;
- key event rate;
- revenue per session, se e-commerce;
- segmentazione per campagna;
- divergenze Ads/GA4;
- eventi realtime/debug, se supportati.

### Proposal e write

Verifica se può proporre e, dopo approval, eseguire o guidare:

- creazione/modifica key events;
- creazione audience;
- lettura audience;
- creazione custom dimensions;
- creazione custom metrics;
- verifica/creazione collegamento Ads;
- lettura/configurazione data stream;
- configurazione coerente dei parametri necessari al tracking.

### Output richiesto GA4

| Capability GA4 | Read | Proposal | Execute | Approval | Readiness | Orchestrator attach | Test | Stato | Evidenza | Gap |
|---|---|---|---|---|---|---|---|---|---|---|

## Blocco 4 — Verifica agente GTM

Verifica se l'agente GTM è realmente in grado di leggere, diagnosticare, proporre e governare modifiche sicure su Google Tag Manager.

Devi controllare almeno:

### Lettura e diagnosi

- account GTM;
- container;
- workspace;
- versioni;
- tag;
- trigger;
- variabili;
- built-in variables;
- folder;
- template;
- environments;
- user permissions, se disponibili;
- GA4 tag;
- Google tag;
- Conversion Linker;
- Google Ads conversion tag;
- remarketing tag;
- consent tag;
- duplicazioni tag;
- trigger troppo larghi;
- trigger fragili basati su DOM;
- trigger basati su dataLayer;
- custom event;
- thank-you page;
- dataLayer variables;
- lead_id / transaction_id;
- value / currency;
- rischio doppio firing.

### Proposal e write

Verifica se può proporre e, dopo approval, eseguire:

- creazione workspace;
- creazione tag;
- modifica tag;
- disabilitazione tag;
- creazione trigger;
- modifica trigger;
- creazione variabili;
- modifica variabili;
- creazione versioni;
- preview/validation;
- publish version;
- rollback/ripristino versione;
- gestione conflitti workspace.

### Requisito di sicurezza GTM

Per GTM non basta poter creare un tag.

Verifica obbligatoriamente se:

- ogni write avviene in workspace separata;
- il publish è distinto dalla creazione/modifica;
- esiste preview evidence prima del publish;
- il target è deterministico;
- esiste rollback o ripristino versione;
- il sistema impedisce publish diretto non approvato.

### Output richiesto GTM

| Capability GTM | Read | Proposal | Execute | Approval | Readiness | Workspace/Preview/Rollback | Test | Stato | Evidenza | Gap |
|---|---|---|---|---|---|---|---|---|---|---|

## Blocco 5 — Verifica orchestratore e interfaccia tra agenti

Verifica se l'orchestratore coordina davvero gli agenti e non si limita a invocarli separatamente.

Devi controllare:

- routing intent → agente corretto;
- routing multi-agente;
- escalation verso implementation lead;
- composizione risultati specialistici;
- validazione output;
- gestione errori specialisti;
- merge delle evidenze;
- ownership delle raccomandazioni;
- separazione tra diagnosi, proposta e azione;
- collegamento tra Ads, GA4 e GTM;
- passaggio di contesto tra agenti;
- campaign binding;
- measurement chain;
- generazione di action proposal coordinate;
- blocco di azioni rischiose senza approval;
- supporto a follow-up specialistico.

Devi rispondere a queste domande operative con `si`, `no` o `parzialmente`:

| Domanda operativa | Risposta | Evidenza | Limite | Impatto |
|---|---|---|---|---|
| Una campagna Ads può essere collegata alla conversione corretta? |  |  |  |  |
| Il sistema sa distinguere GA4 import da Google Ads tag diretto? |  |  |  |  |
| Il sistema sa collegare evento GA4 → tag GTM? |  |  |  |  |
| Il sistema sa verificare se il trigger GTM è affidabile? |  |  |  |  |
| Il sistema sa verificare deduplicazione lead_id/transaction_id? |  |  |  |  |
| Il sistema sa verificare primary/secondary conversion? |  |  |  |  |
| Il sistema sa verificare conversion window e count setting? |  |  |  |  |
| Il sistema sa verificare se il traffico Ads arriva in GA4? |  |  |  |  |
| Il sistema sa verificare preservazione GCLID/GBRAID/WBRAID? |  |  |  |  |
| Il sistema sa confrontare final URL Ads e landing page GA4? |  |  |  |  |
| Il sistema sa verificare audience GA4 collegate ad Ads? |  |  |  |  |
| Il sistema sa generare un piano coordinato Ads+GA4+GTM? |  |  |  |  |
| Il sistema sa impedire azioni cross-platform incoerenti? |  |  |  |  |

## Blocco 6 — Verifica scenari end-to-end obbligatori

Simula staticamente, senza eseguire mutate reali, questi scenari.

Per ogni scenario devi indicare:

- percorso runtime previsto;
- agenti coinvolti;
- tool usati;
- proposal generate;
- approval richiesta;
- execute path previsto;
- readiness blockers;
- output frontend/API;
- test esistente o mancante;
- punto in cui il flusso fallisce, se fallisce.

### Scenario A — Creazione campagna Search lead generation

Input utente ipotetico:

“Crea una campagna Search per generare lead su un prodotto, con budget giornaliero, keyword, RSA, asset, conversione primaria e tracking GA4/GTM coerente.”

Verifica se il sistema può coprire:

- raccolta requisiti minimi;
- validazione account Ads;
- verifica conversioni esistenti;
- proposta struttura campagna;
- proposta budget/bidding;
- proposta ad group/keyword/RSA/asset;
- verifica tracking GA4/GTM;
- proposal approval-backed;
- execute Ads;
- eventuale execute GTM/GA4;
- report finale.

### Scenario B — Modifica campagna esistente

Input utente ipotetico:

“Aumenta budget, aggiungi negative keyword, migliora annunci RSA e collega la conversione corretta.”

Verifica se il sistema può coprire:

- lettura stato corrente;
- diagnosi performance;
- proposta modifiche;
- before/after;
- risk assessment;
- approval;
- execute;
- audit log;
- rollback/dry-run dove necessario.

### Scenario C — Integrazione tracking nuova conversione lead

Input utente ipotetico:

“Configura il tracking del lead: evento GA4 generate_lead, trigger GTM affidabile, conversione Ads primaria e deduplicazione.”

Verifica se il sistema può coprire:

- verifica dataLayer;
- verifica tag GTM;
- verifica evento GA4;
- configurazione key event;
- conversion action Ads;
- mapping Ads ↔ GA4 ↔ GTM;
- deduplicazione lead_id/transaction_id;
- consent mode / Conversion Linker;
- approval e publish GTM controllato;
- validazione finale.

### Scenario D — Audit campagna già attiva

Input utente ipotetico:

“Analizza perché una campagna spende ma non genera lead tracciati correttamente.”

Verifica se il sistema può coprire:

- Ads performance;
- search terms;
- conversion actions;
- GA4 source/medium/campaign;
- landing page;
- funnel eventi;
- GTM tag/trigger;
- discrepanze Ads/GA4;
- diagnosi con evidenze;
- raccomandazioni prioritarie.

### Output richiesto scenari

| Scenario | Completo sì/no/parziale | Punto più debole | Gap bloccante | Gap non bloccante | Evidenza | Test |
|---|---|---|---|---|---|---|

## Blocco 7 — Verifica sicurezza, approval e rischio operativo

Verifica se tutte le azioni potenzialmente distruttive o economicamente rilevanti sono protette.

Classifica come rischio alto o critico almeno:

- modifica budget;
- modifica bidding;
- modifica stato campagna;
- creazione campagna reale;
- publish GTM;
- modifica conversione primaria;
- modifica key event GA4;
- modifica audience usata da Ads;
- eliminazione o disabilitazione tag/trigger/variabili;
- modifica Conversion Linker;
- modifica consent/tracking.

Per ogni famiglia di azioni write compila:

| Azione | Area | Proposal | Approval | Readiness | Preview | Before/After | Rollback/Dry-run | Audit log | Rischio | Evidenza | Correzione consigliata |
|---|---|---|---|---|---|---|---|---|---|---|---|

## Blocco 8 — Verifica prompt, contratti, schema e frontend

Verifica coerenza tra:

- prompt agentici;
- specialist runtime;
- tool registry;
- capability matrix;
- approval workflow;
- execution dispatcher;
- schema `AgentFinding`;
- schema `EvidenceItem`;
- schema `AgentResponse`;
- schema `AgentActionProposal`;
- API backend;
- frontend.

Controlla se gli output permettono davvero:

- evidenze consultabili;
- severity/confidence;
- affected entity;
- tool provenance;
- metric snapshot;
- before/after;
- diff;
- impact assessment;
- risk level;
- rollback plan o equivalente;
- user-facing explanation;
- approvazione da frontend;
- storico decisionale;
- esecuzione controllata.

Output richiesto:

| Area | Coerente sì/no/parziale | File/schema | Problema | Impatto | Fix minimo consigliato |
|---|---|---|---|---|---|

## Blocco 9 — Verifica testabilità e copertura test

Verifica se esistono test reali per:

- orchestrator routing;
- output validation;
- tool registry;
- Ads read;
- Ads proposal;
- Ads execute approval-backed;
- GA4 read;
- GA4 Admin/mutate;
- GTM read;
- GTM workspace/write/publish guardrail;
- cross-platform health check;
- implementation audit;
- approval workflow;
- readiness blockers;
- execution dispatcher;
- frontend rendering delle proposal;
- error handling;
- permessi/OAuth mancanti;
- idempotenza/retry.

Classifica i test:

- `assente`
- `solo unit mock`
- `parziale`
- `integrazione utile`
- `copertura robusta`

Output richiesto:

| Area test | File test | Tipo | Cosa verifica davvero | Limite | Stato |
|---|---|---|---|---|---|

## Blocco 10 — Decisione finale

Produci una decisione netta.

Non usare formule vaghe.

Devi concludere se il sistema è:

- `NON PRONTO`
- `PRONTO SOLO PER AUDIT READ-ONLY`
- `PRONTO PER PROPOSAL SENZA EXECUTE`
- `PRONTO PER EXECUTE LIMITATO CON APPROVAL`
- `PRONTO PER USO OPERATIVO AVANZATO`

La decisione deve essere motivata con evidenze.

## Criteri di scoring

Assegna un punteggio 0-5 a ciascun agente e all'orchestratore sulle seguenti aree:

1. Copertura read
2. Copertura proposal
3. Copertura execute
4. Qualità diagnostica
5. Sicurezza approval
6. Readiness e guardrail
7. Completezza input/output
8. Coerenza prompt-tool-runtime
9. Capacità cross-platform
10. Testabilità

Scala:

- 0 = assente
- 1 = molto incompleto
- 2 = parziale
- 3 = utilizzabile per audit base
- 4 = operativo con limiti
- 5 = completo e pronto per uso avanzato

Output richiesto:

| Componente | Read | Proposal | Execute | Diagnostica | Approval | Readiness | I/O | Coerenza | Cross-platform | Testabilità | Media | Stato |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|

## Struttura obbligatoria di `REPORT_verifica_agents.md`

Il report finale deve avere esattamente questa struttura:

## 1. Executive summary

Sintesi secca:

- decisione finale;
- stato agente Ads;
- stato agente GA4;
- stato agente GTM;
- stato orchestratore;
- stato cross-platform Ads ↔ GA4 ↔ GTM;
- rischio principale;
- prima priorità implementativa;
- cosa è già sufficiente;
- cosa non è ancora sufficiente.

## 2. Verifica delle fasi precedenti

Tabella con stato di `agents.md`, fasi 1-9, file stato, report, claim e verifica nel codice.

## 3. Copertura agenti e orchestratore

Tabella scoring 0-5 per:

- AdsSpecialist;
- AnalyticsSpecialist / GA4;
- GTMSpecialist;
- Orchestrator / Implementation Lead;
- Cross-platform health / implementation audit.

## 4. Verifica agente Google Ads

Includi:

- capability matrix Ads;
- cosa funziona;
- cosa è parziale;
- cosa manca;
- gap bloccanti;
- gap non bloccanti;
- evidenze.

## 5. Verifica agente GA4

Stessa struttura della sezione Ads.

## 6. Verifica agente GTM

Stessa struttura della sezione Ads, con focus specifico su workspace, preview, publish e rollback.

## 7. Verifica orchestrazione cross-platform

Includi:

- matrice domande operative;
- mapping Ads ↔ GA4 ↔ GTM;
- stato `cross_platform_health_check`;
- stato `implementation_audit`;
- attachability reale;
- limiti.

## 8. Verifica scenari end-to-end

Includi gli scenari A, B, C, D con esito completo/parziale/non supportato.

## 9. Sicurezza, approval e rischio operativo

Includi:

- guardrail matrix;
- rischi critici;
- rischi alti;
- rischi medi;
- rischi bassi;
- azioni vietate senza approval.

## 10. Coerenza prompt-tool-schema-frontend

Includi:

- incoerenze prompt-tool;
- gap schema/contract;
- limiti frontend/API;
- impatto su storico decisionale e approvazioni.

## 11. Testabilità e copertura test

Includi:

- test presenti;
- test mancanti;
- test troppo mockati;
- test minimi da aggiungere prima di considerare il sistema affidabile.

## 12. Gap bloccanti

Per ogni gap:

- ID gap;
- area;
- agente/componente;
- problema;
- evidenza;
- impatto;
- severità;
- fix minimo consigliato;
- priorità.

## 13. Gap importanti ma non bloccanti

Stessa struttura dei gap bloccanti.

## 14. Piano implementativo minimo consigliato

Non proporre refactor ampi.

Ordina le azioni in questo modo:

1. fix critici di sicurezza/approval;
2. fix proposal reachability;
3. fix execute path mancanti;
4. fix cross-platform mapping;
5. fix frontend/API per approval e storico;
6. test minimi obbligatori;
7. miglioramenti diagnostici non bloccanti.

Per ogni azione indica:

- priorità;
- file coinvolti;
- patch minima attesa;
- test da aggiungere;
- rischio se non fatto.

## 15. Raccomandazione finale

Concludi con una decisione operativa netta:

- cosa è già utilizzabile oggi;
- cosa non va usato in produzione;
- cosa va implementato prima;
- cosa può essere rimandato;
- cosa non implementare per evitare overengineering;
- prossimo prompt consigliato per Copilot, se serve una fase di fix.

## Struttura obbligatoria di `STATO_verifica_agents.md`

Il file stato deve contenere:

- scope verifica;
- data/contesto;
- file letti;
- file non trovati;
- gate finale `PASS` o `FAIL`;
- decisione finale;
- gap bloccanti aperti;
- rischi critici aperti;
- test mancanti essenziali;
- prossima azione consigliata;
- link o riferimento a `REPORT_verifica_agents.md`.

## Formato evidenze obbligatorio

Ogni finding deve includere:

- File:
- Funzione/classe:
- Riga o blocco rilevante, se disponibile:
- Tool/endpoint/action_type:
- Agente/componente impattato:
- Layer mancante o verificato:
- Impatto operativo:
- Severità:
- Raccomandazione:

Non scrivere finding senza evidenza.

Se non trovi un file o una capability, scrivi:

`Non trovato nel repository dopo ricerca in: [percorsi ispezionati]`.

## Severità

Usa questa scala:

- `Critica`: blocca lo scopo principale o consente mutate rischiose senza approval.
- `Alta`: limita fortemente l'operatività o può generare raccomandazioni errate.
- `Media`: riduce completezza o precisione, ma non blocca il workflow principale.
- `Bassa`: miglioramento utile, naming, documentazione o ergonomia.

## Comandi di ricerca consigliati

Usa strumenti equivalenti a questi, adattandoli al repository:

- `rg -n "AdsSpecialist|AnalyticsSpecialist|GTMSpecialist|Orchestrator" backend frontend tests docs`
- `rg -n "cross_platform_health_check|implementation_audit|campaign_binding|measurement" backend frontend tests docs`
- `rg -n "capability_matrix|AgentActionProposal|AgentFinding|EvidenceItem|AgentResponse" backend frontend tests docs`
- `rg -n "approval|readiness|execute|dispatcher|rollback|dry_run|preview" backend frontend tests docs`
- `rg -n "googleads|Google Ads|GA4|analyticsdata|analyticsadmin|tagmanager|GTM" backend frontend tests docs`
- `rg -n "create_campaign|mutate|budget|bidding|keyword|negative|responsive_search|conversion" backend frontend tests docs`
- `rg -n "workspace|publish|version|tag|trigger|variable|conversion_linker" backend frontend tests docs`
- `rg -n "key_event|custom_dimension|audience|data_stream|ads_link|event_parameter" backend frontend tests docs`

## Acceptance checks finali

La verifica può essere chiusa con `PASS` solo se:

- il report finale è stato creato;
- ogni agente è stato valutato sui layer read/proposal/execute/approval/readiness/attach/test;
- l'orchestratore è stato verificato con scenari end-to-end;
- gli scenari A-D hanno esito motivato;
- ogni finding ha evidenza concreta;
- tutti i gap bloccanti sono distinti dai gap non bloccanti;
- i rischi critici e alti sono esplicitati;
- la decisione finale è netta;
- `STATO_verifica_agents.md` riporta `PASS` o `FAIL` con motivazione.

Se anche uno solo di questi punti manca, il gate finale deve essere `FAIL`.

## Regola finale

Non devi dimostrare che il lavoro precedente è stato “fatto”.

Devi dimostrare se il codice attuale è davvero pronto.

Valuta severamente.

Meglio un `FAIL` utile e documentato che un `PASS` fragile.

Il risultato deve permettere di decidere subito se il sistema può essere usato solo per audit, anche per proposal, oppure anche per execute approval-backed su campagne reali.
