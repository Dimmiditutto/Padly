Agisci come un **Senior Software Architect**, **Senior Code Reviewer** e **QA tecnico**.

Esegui una **verifica approfondita e rigorosa** del codice attuale, con focus speciale sui file modificati più di recente e sul loro impatto sull’intero progetto. Scrivi o Riscrivi/modifica il prompt PROMPT_VERIFICA_ESITO.md specificando nel dettaglio quali sono le modifiche/integrazioni in modo che l'agente sappia già cosa fare

## Obiettivo

Non devi apportare alcuna modifica al codice.  
Devi leggere prompts SaaS/prompt_master.md e prompts SaaS/STATO_FASE_1.MD per capire esattamente quali sono i file modificati, quali sono le modifiche reali e quale è l’impatto complessivo di queste modifiche sul progetto. Poi:

1. verificare la coerenza complessiva del codice
2. verificare la coerenza reciproca dei file modificati
3. verificare che i file modificati non introducano conflitti, regressioni, blocchi o incompatibilità né tra loro né rispetto al resto del progetto
4. verificare che, a livello di codice complessivo, non esistano conflitti, criticità o punti potenzialmente bloccanti
5. verificare che la logica di business prevista dal progetto sia stata rispettata correttamente

## Regole di lavoro

- non modificare nulla
- non proporre patch dirette nel codice
- non riscrivere file
- non fare refactor
- non correggere automaticamente gli errori trovati
- limita il lavoro a una verifica tecnica rigorosa e a una restituzione strutturata dei risultati

## Ambiti di verifica obbligatori

### 1. Coerenza complessiva del codice
Verifica che il progetto sia coerente nel suo insieme, considerando almeno:
- architettura generale
- relazioni tra moduli
- consistenza tra frontend, backend, API, database, pagamenti, scheduler o job, se presenti
- coerenza tra tipi, schemi, modelli e contratti dati
- coerenza tra componenti UI, stato e chiamate API
- assenza di mismatch tra implementazione e struttura progettuale

### 2. Coerenza dei file modificati
Verifica che i file modificati:
- siano coerenti tra loro
- usino convenzioni compatibili
- non introducano dipendenze incoerenti
- non rompano import, export, tipi, interfacce, props, modelli o contratti
- non introducano comportamenti ambigui o ridondanti

### 3. Conflitti o blocchi generati dai file modificati
Verifica che i file modificati non creino:
- conflitti logici
- conflitti strutturali
- regressioni funzionali
- incompatibilità tra componenti
- blocchi nel flusso applicativo
- errori potenziali in runtime
- errori potenziali in build, test, deploy o integrazione

### 4. Criticità del codice complessivo
Verifica se nell’intero progetto esistono:
- punti bloccanti
- criticità tecniche
- buchi di validazione
- incoerenze tra flussi
- edge case non coperti
- rischi di regressione
- fragilità architetturali o implementative
- vulnerabilità logiche nei flussi critici

### 5. Rispetto della logica di business
Verifica che la logica di business sia stata rispettata correttamente, in particolare:
- regole funzionali
- vincoli di processo
- stati ammessi
- transizioni corrette
- regole di validazione
- gestione errori
- comportamenti attesi nei casi normali e nei casi limite
- rispetto delle priorità e dei vincoli dichiarati nel progetto

## Modalità di analisi richiesta

La verifica deve essere:
- rigorosa
- concreta
- tecnica
- non superficiale
- orientata ai problemi reali
- focalizzata sia sugli errori espliciti sia sui rischi impliciti

Non limitarti a dire “sembra corretto”.  
Cerca attivamente:
- incongruenze
- omissioni
- assunzioni fragili
- dipendenze rischiose
- implementazioni opache
- comportamenti non idempotenti
- punti che possono rompersi in produzione
- scollamenti tra progetto e implementazione

## Output richiesto

Restituisci il risultato in questa struttura:

## 1. Esito sintetico generale
Indica un giudizio sintetico complessivo, ad esempio:
- `PASS`
- `PASS CON RISERVE`
- `FAIL PARZIALE`
- `FAIL`

Con una sintesi iniziale molto chiara.

## 2. Verifica per area
Dividi la verifica almeno in queste sezioni:
- coerenza complessiva del codice
- coerenza tra file modificati
- conflitti o blocchi introdotti dai file modificati
- criticità del progetto nel suo insieme
- rispetto della logica di business

Per ogni sezione indica:
- esito
- problemi trovati
- gravità del problema
- impatto reale

## 3. Elenco criticità
Per ogni criticità trovata, specifica:
- titolo breve del problema
- descrizione tecnica
- perché è un problema reale
- dove si manifesta
- gravità: `bassa`, `media`, `alta`, `critica`
- se blocca il rilascio oppure no

## 4. Prioritizzazione finale
Raggruppa i problemi in:
- da correggere prima del rilascio
- da correggere prima della beta pubblica
- miglioramenti differibili

## 5. Verdetto finale
Chiudi con un verdetto netto, ad esempio:
- il codice è pronto
- il codice è quasi pronto ma richiede fix mirati
- il codice non è ancora sicuro per il rilascio

## 6. Prompt operativo per i fix
Alla fine, senza modificare il codice, scrivi un **prompt operativo, preciso ed efficace** da usare come punto di partenza per eseguire i fix.

Questo prompt finale deve:
- partire solo dalle criticità realmente emerse nella verifica
- avere priorità chiare
- imporre patch minime
- vietare refactor inutili
- chiedere fix concreti e mirati
- includere anche l’eventuale richiesta di test mancanti, solo se realmente necessari

## Regola finale

Non scrivere codice.  
Non applicare fix.  
Non proporre miglioramenti generici non emersi dalla verifica.

Fai prima una **verifica tecnica rigorosa** e poi scrivi un **prompt operativo realmente utile** scrivendo/modificando o riscrivendo il file PROMPT_VERIFICA_ESITO.md per correggere solo ciò che serve.

