# PROMPT OPERATIVO PER COPILOT — FIX CHIRURGICI PRE-LIVE

Agisci come un **Senior Full-Stack Engineer** e fai una **patch minima, mirata e production-oriented** sul progetto attuale della web app di prenotazione padel.

## Obiettivo

Correggere **solo i punti davvero bloccanti o ad alto rischio pre-live**, senza refactor ampi e senza toccare parti non necessarie.

Il progetto è già vicino al rilascio.  
Non voglio redesign, non voglio ristrutturazioni, non voglio “pulizia generale”.  
Voglio solo mettere in sicurezza i punti critici.

## Priorità assolute

Correggi in quest’ordine:

1. **PayPal return flow non idempotente**
2. **Stripe webhook non sicuro se manca il secret**
3. **Frontend deve mostrare solo i provider di pagamento realmente abilitati**
4. **Per la data odierna non devono comparire slot passati come disponibili**
5. **Aggiungere test minimi mancanti sui flussi critici**
6. Solo se la patch resta minima: piccoli fix di robustezza/documentazione correlati

## Vincoli non negoziabili

- patch minima
- non cambiare architettura
- non fare refactor ampi
- non cambiare stack
- non toccare routing salvo minimo indispensabile
- non toccare autenticazione salvo minimo indispensabile
- non toccare logica di business non coinvolta nei bug
- non rinominare file
- non spostare file
- non introdurre nuove dipendenze salvo necessità reale e molto piccola
- non riscrivere componenti interi se basta una patch locale
- mantieni stile e struttura del progetto attuale

## Regola di lavoro

Prima individua i file reali coinvolti nel repository attuale.  
Poi applica la patch più piccola possibile.

Per ogni fix:
- spiega il problema in 1 riga
- spiega il rischio in 1 riga
- applica la correzione minima
- aggiungi o aggiorna il test relativo se possibile

## FIX 1 — PayPal return flow idempotente

### Problema
Il flusso di ritorno PayPal richiama il capture dell’ordine anche se la prenotazione è già stata confermata.  
Se l’utente ricarica la pagina di return o richiama l’endpoint due volte, il secondo capture può fallire o generare uno stato incoerente.

### Obiettivo
Rendere il return flow **idempotente**.

### Correzione richiesta
Nel service/handler del return PayPal:

- recupera la booking
- se la booking è già `CONFIRMED`, non richiamare il capture
- restituisci direttamente l’esito coerente della prenotazione già confermata
- gestisci in modo pulito anche il caso in cui il pagamento risulti già acquisito nel DB
- evita doppie conferme e doppie scritture log/pagamento

### Requisiti
- nessuna doppia capture
- nessuna eccezione non gestita al refresh della return URL
- nessuna regressione sul flusso normale

## FIX 2 — Stripe webhook guard obbligatoria

### Problema
Se `STRIPE_WEBHOOK_SECRET` manca, il webhook in alcuni path accetta payload non firmati.

### Obiettivo
In produzione, il webhook Stripe deve essere accettato **solo** se il secret è configurato e la firma è valida.

### Correzione richiesta
Aggiorna il webhook Stripe in modo che:

- se l’app è in produzione e il webhook secret non è configurato:
  - l’endpoint fallisce esplicitamente
  - non accetta payload
- se il secret esiste:
  - verifica obbligatoriamente la firma
- se il payload è duplicato:
  - l’evento non deve produrre doppie conferme o doppie scritture
- se l’evento è irrilevante o già processato:
  - gestiscilo in modo idempotente e pulito

### Requisiti
- niente fallback “silenziosi” non sicuri in prod
- niente accettazione di JSON raw non firmati in produzione
- mantieni il path dev/mock solo se chiaramente confinato a sviluppo/test

## FIX 3 — Frontend: mostra solo provider abilitati

### Problema
Il frontend mostra sempre Stripe e PayPal, anche se uno dei due provider non è configurato o non è abilitato dal backend.

### Obiettivo
Mostrare all’utente **solo** i metodi di pagamento realmente disponibili.

### Correzione richiesta
Nel frontend pubblico:

- leggi la config reale restituita dall’endpoint pubblico di configurazione
- usa i flag tipo:
  - `stripe_enabled`
  - `paypal_enabled`
  o gli equivalenti reali del progetto
- mostra solo i bottoni/provider effettivamente disponibili
- se è disponibile un solo provider:
  - rendi la UX coerente
  - puoi pre-selezionarlo o mostrare solo la CTA relativa
- se nessun provider è disponibile:
  - mostra un messaggio chiaro e non permettere di proseguire al checkout

### Requisiti
- niente bottone PayPal se PayPal non è attivo
- niente bottone Stripe se Stripe non è attivo
- niente submit incoerenti verso provider non configurati
- nessuna regressione sul flow booking

## FIX 4 — Slot passati non visibili oggi

### Problema
Per la data odierna vengono mostrati anche slot già passati, che poi vengono rifiutati al submit.

### Obiettivo
Non mostrare come disponibili slot che non sono più prenotabili.

### Correzione richiesta
Nel layer che costruisce o restituisce gli slot disponibili:

- se la data richiesta è oggi in timezone `Europe/Rome`
- escludi gli slot con start time <= now
- mantieni invariata la logica per le date future
- evita mismatch tra UI e validazione finale

### Requisiti
- nessuno slot passato visibile come prenotabile oggi
- nessuna regressione su date future
- gestione robusta timezone Europe/Rome

## FIX 5 — Test minimi mancanti sui flussi critici

### Obiettivo
Aggiungere **solo i test davvero necessari** per coprire i fix critici e i casi ad alto rischio.

### Regola importante
Usa **solo l’infrastruttura di test già presente nel progetto**.

- Non introdurre nuovi framework di test frontend
- Non installare Vitest, Jest, Testing Library o librerie simili
- Non scrivere pseudotest frontend non eseguibili
- Se non esiste infrastruttura di test frontend, **escludi i test frontend automatici**
- In quel caso, documenta soltanto i **controlli manuali attesi** per il frontend nella sezione finale di verifica

### Test backend richiesti

Aggiungi o completa test almeno per questi casi:

#### 1. PayPal return idempotente
- prima chiamata a return/capture: booking confermata
- seconda chiamata sulla stessa booking/order: nessuna seconda capture, nessuna eccezione non gestita, booking ancora coerente

#### 2. Stripe webhook senza secret in produzione
- se ambiente produzione e secret assente: request rifiutata
- se firma invalida: request rifiutata

#### 3. Stripe webhook duplicato
- due eventi uguali non devono produrre doppia conferma o doppio effetto

#### 4. Slot passati nella data odierna
- chiamando il flusso slot per oggi, gli slot passati non devono risultare disponibili

### Verifiche frontend richieste solo come controllo manuale, salvo infrastruttura già esistente
Verifica manualmente almeno:

- se solo Stripe è enabled, compare solo Stripe
- se solo PayPal è enabled, compare solo PayPal
- se nessuno è enabled, il checkout non è disponibile

### Requisiti test
- patch minima
- test realistici
- usa solo l’infrastruttura di test esistente
- non creare framework paralleli
- evita test inutilmente fragili

## FIX 6 — Fix opzionale esplicitamente consentito

Questo fix è **facoltativo** e va eseguito solo se la patch resta minima e locale.

### Fix opzionale consentito
Nel componente `PaymentStatusPage`, ferma il polling quando lo stato booking è terminale, almeno nei casi:

- `CONFIRMED`
- `CANCELLED`
- `EXPIRED`
- `COMPLETED`
- `NO_SHOW`

### Vincoli
- non modificare il flow generale
- non cambiare routing
- non cambiare API
- non riscrivere il componente
- applica solo una guard clause o cleanup minimo sul polling
- non aggiungere altri “piccoli miglioramenti” non esplicitamente richiesti

## Chiarimento esplicito sul perimetro slot

Non modificare in questa patch la regola sugli slot che possono estendersi oltre la mezzanotte locale a causa di durate lunghe, salvo che il progetto già preveda esplicitamente il vincolo “inizio e fine nello stesso giorno”.

In assenza di tale vincolo già definito:
- lascia invariata la logica cross-midnight
- non introdurre nuove regole prodotto

## Output atteso

Voglio un output disciplinato in questo ordine:

### 1. File reali coinvolti
Elenca i file del repository che toccherai realmente.

### 2. Piano patch minimo
Per ogni file:
- perché lo tocchi
- quale fix copre

### 3. Patch file per file
Mostra le modifiche reali file per file, con codice completo della parte necessaria.

### 4. Test aggiunti o aggiornati
Mostra i test nuovi/modificati.

### 5. Verifica finale
Chiudi con checklist chiara.

## Checklist di verifica finale

Verifica almeno:

- [ ] refresh della return URL PayPal non causa doppia capture
- [ ] booking PayPal già confermata non viene riconfermata
- [ ] Stripe webhook in produzione fallisce se il secret manca
- [ ] Stripe webhook con firma invalida viene rifiutato
- [ ] evento Stripe duplicato non produce doppio effetto
- [ ] frontend mostra solo i provider attivi
- [ ] se nessun provider è attivo, l’utente non può procedere al checkout
- [ ] per oggi non compaiono slot già passati
- [ ] nessuna regressione su logica booking standard
- [ ] nessun errore TypeScript o Python introdotto
- [ ] nessuna modifica inutile fuori perimetro

## Criterio finale di qualità

Il lavoro è corretto solo se:

- i fix critici sono davvero risolti
- la patch è piccola
- non hai toccato parti non necessarie
- il codice resta coerente col progetto esistente
- i test coprono i rischi principali pre-live

## Regola finale

Non fare miglioramenti generici.  
Non fare refactor estetici.  
Non fare “pulizia del codice” fuori scope.

Fai una **patch chirurgica pre-live** sui punti critici reali.