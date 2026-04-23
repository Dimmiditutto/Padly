# Play — Riassunto consolidato delle decisioni

## 1. Direzione generale del prodotto

Abbiamo deciso di **non mettere al centro una chat AI**.

La scelta corretta per questo progetto è:

- **pagina `/play` come cuore del prodotto**
- **tutto deterministico**
- **nessun LLM necessario nella prima versione**
- eventuale AI solo in futuro, come livello opzionale e non come motore principale

### Motivi
- meno complessità
- zero hallucination
- costi quasi nulli
- flusso più chiaro per utenti e club
- maggiore affidabilità su partite, join e completamento

---

## 2. Pagina `/play`

La pagina `/play` deve essere la pagina pubblica dove si gestisce tutto il flusso partite.

### Obiettivo reale della pagina
Non deve essere solo una pagina “crea partita”.

Deve fare due cose insieme:
- **completare prima le partite già aperte**
- **creare una nuova partita solo quando serve davvero**

Quindi `/play` è un **motore di consolidamento delle partite**, non una semplice lista slot.

### Struttura corretta della pagina

#### Blocco principale: partite da completare
È la sezione più importante.

Ordine di priorità:
1. partite **3/4**
2. partite **2/4**
3. partite **1/4**
4. solo dopo slot liberi / creazione nuova partita

Ogni card deve mostrare:
- giorno
- data
- orario
- livello
- numero giocatori
- posti mancanti
- note opzionali
- bottone `Unisciti`
- bottone `Condividi`

#### Blocco secondario: crea una nuova partita
Serve per:
- scegliere giorno
- scegliere slot libero
- scegliere livello
- aggiungere nota facoltativa
- creare il match

Ma prima della creazione il sistema deve verificare se esiste già una partita compatibile e, se sì, suggerire di unirsi a quella invece di frammentare la domanda.

#### Blocco personale: le mie partite
Se l’utente è riconosciuto:
- vede le partite a cui partecipa
- vede le partite create da lui
- può uscire o modificare dove consentito

### Componenti corretti della pagina
- `PlayPage`
- `MatchBoard`
- `MatchCard`
- `CreateMatchForm`
- `MyMatches`
- `JoinConfirmModal`
- `InviteAcceptPage`
- `SharedMatchPage`

---

## 3. Logica di dominio partite

### Entità principali
Abbiamo deciso che il dominio corretto è:

- `Match` = partita aperta
- `Player` = utente leggero
- `MatchPlayer` = partecipazione utente-partita
- `Club` = contenitore/configurazione club
- più tabelle accessorie per token, inviti, notifiche, profilo utente

### Regole fisse
- una partita dura **90 minuti**
- una partita è completa a **4 giocatori**
- lo stato parte da `OPEN`
- quando entra il quarto giocatore:
  - il backend prende lock
  - ricontrolla che lo slot sia ancora libero
  - crea la booking finale
  - collega la booking al match
  - imposta il match come `FULL`
  - invia le notifiche necessarie

Questa parte è **tutta backend deterministica**, nessuna AI.

---

## 4. Lock al quarto giocatore

Questo è il punto più critico dell’intero sistema.

### Scelta corretta
Usare:
- **transazione DB**
- **`SELECT ... FOR UPDATE` sulla riga `matches`**
- **vincolo unico su `match_players(match_id, player_id)`**
- **ricontrollo `player_count < 4` dentro la stessa transazione**
- **creazione booking finale nella stessa transazione**
- opzionale: **advisory lock PostgreSQL** se il booking system esistente lo usa già per proteggere slot/campo

### Flusso corretto
1. begin transaction
2. lock del match con `FOR UPDATE`
3. verifica `status = OPEN`
4. verifica che il player non sia già dentro
5. conta i player attuali
6. se già 4 -> errore
7. inserisce il nuovo `MatchPlayer`
8. riconta
9. se ora sono 4:
   - lock / verifica disponibilità slot
   - crea booking
   - `match.status = FULL`
   - collega `booking_id`
10. commit

### Decisione finale
- `FOR UPDATE` per coerenza sul match
- advisory lock esistente per proteggere la booking finale, se già presente nel sistema

---

## 5. Identità utente

Abbiamo deciso di **non usare login classico con password**.

La soluzione corretta è una **identità leggera persistente**.

### Primo accesso
La prima volta che l’utente entra davvero nel flusso:
- viene identificato con **nome + telefono**
- opzionalmente in futuro anche email, ma il canale principale che abbiamo deciso è il telefono perché il flusso nasce da WhatsApp

Il backend:
- crea o recupera il `Player`
- genera un **player access token**
- salva **solo l’hash** del token

### Accessi successivi
Quando l’utente torna su `/play`:
- il frontend chiama `GET /api/play/me`
- il backend legge il token
- se è valido, riconosce il player
- l’utente entra già riconosciuto e può usare join rapido

### Se il token manca o non è valido
Abbiamo deciso che:
- se il token è assente, invalido, scaduto o revocato
- il sistema deve richiedere di nuovo identificazione
- e generare un **nuovo token**

Questa parte è importante per casi come:
- cambio telefono
- reinstallazione
- pulizia cache
- browser diverso

---

## 6. Token: struttura corretta

Abbiamo deciso di usare **due tipi distinti di token**, non uno solo.

### A. Community invite token
Serve solo per l’onboarding iniziale.

Caratteristiche:
- token opaco
- monouso
- con scadenza
- legato lato server a:
  - `club_id`
  - `name`
  - `phone`
  - `expires_at`
  - `used_at`
  - `revoked_at`

Non deve contenere dati personali in chiaro nel link.

### B. Player access token
Serve per riconoscere l’utente nelle visite successive.

Caratteristiche:
- persistente
- usato da `/api/play/me`
- il backend salva solo l’hash

### Dove salvare il player access token
Decisione esplicita:
- **cookie `httpOnly`, `secure`, `SameSite=Lax`** come default
- **non** `localStorage` come soluzione principale

### Motivazione
Il cookie httpOnly è:
- più robusto
- più sicuro
- più pulito architetturalmente

Il cross-device non si risolve col token:
- si risolve con nuovo onboarding
- oppure con recovery futuro

Quindi:
- **invite token** nel link
- **player access token** in cookie httpOnly

---

## 7. Invito community via WhatsApp dal club

Questo è uno dei punti principali decisi.

### Flusso corretto
1. il club raccoglie:
   - nome
   - telefono

2. l’admin crea un invito community

3. il backend genera un **invite token**

4. il club invia via WhatsApp un link tipo:
   - `/play/invite/{token}`

5. l’utente apre il link

6. vede una pagina semplice con:
   - nome club
   - proprio nome
   - bottone `Accetta ed entra nella community`

7. quando clicca:
   - il backend valida l’invito
   - crea o recupera il `Player`
   - genera il `player access token`
   - marca l’invito come usato
   - l’utente entra nell’app già riconosciuto

### Decisione netta
Questo flusso deve essere **100% deterministico**.

Niente LLM.  
Niente parsing.  
Niente automazioni intelligenti.

---

## 8. Condivisione tra utenti via WhatsApp

Abbiamo deciso che anche gli utenti devono poter condividere una partita.

### Come
Ogni partita aperta deve avere:
- bottone `Condividi`
- link pubblico controllato

Esempio:
- `/play/matches/{public_share_token}`

### Flusso
Un utente della community condivide il link:
- nel proprio gruppo WhatsApp
- a uno o più amici

### Decisione chiave
La condivisione deve **abilitare viralità**, quindi **non** richiede sempre un invito preventivo del club.

### Se chi apre il link è già riconosciuto
- entra
- vede la partita
- può unirsi

### Se chi apre il link NON è riconosciuto
segue un **self-service onboarding controllato**:
1. il backend valida `public_share_token`
2. mostra la partita
3. chiede:
   - nome
   - telefono
   - bottone `Entra nella community e unisciti`
4. il backend:
   - crea o recupera il `Player`
   - genera `player access token`
   - inserisce l’utente nella community del club
   - completa il join al match

### Decisione finale
Esistono quindi **due flussi di onboarding**:
- **invito del club via WhatsApp**
- **self-service onboarding da share match**

Questa è la scelta corretta per non bloccare la condivisione organica.

---

## 9. Chat interna

Qui abbiamo deciso una cosa precisa:

### Non fare subito una chat generale stile WhatsApp
L’abbiamo scartata come prima versione perché porta:
- rumore
- spam
- moderazione
- complessità inutile

### Se mai fare chat, farla per singola partita
La scelta più sensata è:
- **thread interno per match**
- non chat community generale

Utilità:
- organizzarsi su quella specifica partita
- chiudere il quarto
- scrivere poche comunicazioni operative

Questa è eventuale fase successiva, ma non è il centro del prodotto.

---

## 10. Notifiche

Abbiamo chiarito che senza notifiche il sistema perde moltissimo valore.

### Cosa non ha senso come canale principale
- email come canale principale community
- chat generale come sostituto notifiche
- WhatsApp automatico broadcast come prima soluzione

### Scelta corretta
Il canale giusto è:

- **in-app sempre**
- **Web Push come canale principale di attivazione**

### Tipi di notifica utili
Per utenti coinvolti:
- ti sei unito alla partita
- qualcuno si è unito alla tua partita
- manca 1 giocatore
- partita completata
- partita modificata
- partita annullata

Per opportunità community:
- nuova partita compatibile
- match quasi completo

### Regola
Le notifiche devono essere:
- mirate
- non spam
- con rate limit
- con preferenze utente

---

## 11. Memoria / profilo utente

Abbiamo deciso che il sistema deve imparare **quando** l’utente gioca più probabilmente, ma in modo **molto leggero**.

### Nome corretto
Non “memoria interna”, ma:

**profilo di gioco probabilistico utente**

### Cosa deve fare
Capire, in modo deterministico:
- quali giorni usa più spesso
- quali fasce orarie usa più spesso
- quale livello sceglie più spesso
- quanto risponde alle notifiche

### Esempio
- A gioca spesso venerdì 17:30–21:00
- B gioca spesso martedì 11:00–14:00

Da qui il sistema può inviare notifiche mirate tipo:
- `Ciao Luca, venerdì alle 18:00 c’è una partita compatibile con i tuoi orari. Giochi?`

### Decisione tecnica
Tutto questo deve essere **deterministico**, senza AI, senza ML vero.

---

## 12. Profilazione: da fare subito

Qui la decisione aggiornata è precisa.

### Scelta
Il **profilo probabilistico va implementato subito**, non dopo.

### Perché
Se non salvi da subito i dati:
- non costruisci memoria
- non avrai base utile per attivare notifiche mirate più avanti

### Strategia corretta
V1:
- **profilazione attiva da subito**
- ma usata inizialmente solo per **raccogliere memoria**

Quindi in v1 fai entrambe le cose:
- **memoria/profilazione attiva**
- **notifiche iniziali semplici e deterministiche**

### Quando attivare notifiche mirate
Non solo dopo N giorni, ma con doppia soglia:

Attiva notifiche mirate quando c’è almeno una di queste condizioni:
- almeno **14–21 giorni** di dati
- oppure almeno **5–8 eventi utili** per utente

---

## 13. Come gestire la memoria senza gonfiare il database

Questo era un punto chiave.

Abbiamo deciso che la memoria non deve essere “ricca” o infinita.

### Cosa NON fare
Non salvare:
- cronologie enormi
- testo libero
- log dettagliati per sempre
- storico lungo non aggregato

### Cosa fare
Due livelli soli:

#### A. Eventi recenti a retention breve
Tabella essenziale con eventi utili, ad esempio:
- join match
- creazione match
- completamento match
- click su notifica
- apertura app da notifica
- livello scelto
- giorno settimana
- fascia oraria

Retention:
- 60 o 90 giorni massimo

Poi purge o archiviazione leggera.

#### B. Profilo aggregato compatto
Una riga per utente con punteggi tipo:
- score per giorno settimana
- score per fascia oraria
- score per livello
- engagement score
- last updated

### Decisione importante
Non si deve ricalcolare ogni volta tutto lo storico.

Si deve usare:
- aggiornamento incrementale
oppure
- job periodico leggero

In più:
- i dati vecchi devono decadere
- le abitudini recenti devono pesare di più

Quindi memoria **compatta, aggregata e con scadenza**.

---

## 14. Notifiche v1 e v2

### V1: notifiche semplici e deterministiche
Da subito:
- notifiche ai partecipanti della partita
- notifiche alla community opt-in
- filtro almeno per **livello**
- cap **max 3 notifiche al giorno per utente**
- distribuite su fasce diverse:
  - mattino
  - pranzo / primo pomeriggio
  - sera

### Priorità corretta delle notifiche
1. **3/4** = priorità alta
2. **2/4** = priorità media
3. **1/4** = priorità bassa, solo se match nuovo o slot interessante

### Regola importante
Non notificare indiscriminatamente tutti i match 1/4, 2/4, 3/4.

La logica corretta è:
- **3/4** sempre priorità massima
- **2/4** sì
- **1/4** solo con criterio, non in massa

### V2: notifiche mirate
Dopo soglia minima di dati:
- il sistema usa il profilo probabilistico
- notifica solo gli utenti con alta compatibilità
- sempre con frequency cap e rate limit

---

## 15. Con 4 campi e 400/500 utenti

Abbiamo chiarito che il problema non è il volume puro.

Se la memoria è fatta come sopra:
- PostgreSQL la gestisce bene
- i costi server restano bassi
- il problema si sposta sulla qualità delle regole, non sulla quantità di dati

Quindi è fattibile anche per club con:
- 4 campi
- 400/500 utenti community

A patto di usare:
- retention breve
- bucket orari
- profilo aggregato
- purge automatico

---

## 16. API / endpoint essenziali decisi

### Identità e onboarding
- `GET /api/play/me`
- `POST /api/play/identify`
- `POST /api/play/invite/{token}/accept` oppure equivalente

### Pagina play
- `GET /api/play/matches`
- `GET /api/play/slots`
- `POST /api/play/matches`
- `GET /api/play/matches/{id}`
- `POST /api/play/matches/{id}/join`
- `POST /api/play/matches/{id}/leave`
- `PATCH /api/play/matches/{id}`

### Condivisione
- link pubblico per match con token di share

### Notifiche
- subscribe/unsubscribe push
- preferenze notifiche
- log notifiche

---

## 17. Decisione finale di prodotto

La direzione consolidata è questa:

### Cuore del prodotto
- **pagina `/play`**
- **100% deterministica**

### Onboarding community
- **invito WhatsApp dal club**
- **invite token**
- **accettazione community**
- **creazione player**
- **player token persistente in cookie httpOnly**

### Crescita organica delle partite
- **link condivisibili via WhatsApp tra utenti**
- pagina match condivisibile
- join rapido
- self-service onboarding da share se necessario

### Retention e attivazione
- **web push**
- notifiche iniziali semplici
- profilo probabilistico attivo da subito
- notifiche mirate in seconda fase

### Da NON mettere al centro adesso
- chat AI
- LLM
- chat generale stile WhatsApp
- email come canale principale community

---

## 18. Sintesi secca finale

Abbiamo deciso di costruire un sistema così:

- una **pagina `/play` deterministica** dove gli utenti vedono partite aperte, si uniscono e ne creano di nuove
- il club fa entrare gli utenti nella community tramite **link WhatsApp con invite token**
- quando l’utente accetta, il backend crea o recupera il `Player` e genera un **player access token persistente in cookie httpOnly**
- ogni partita può essere condivisa dagli utenti via **WhatsApp** con link pubblico controllato
- chi apre il link e non è riconosciuto può fare **self-service onboarding** ed entrare nella community
- il sistema usa una **memoria leggera e aggregata** per capire quando l’utente gioca più spesso
- la **profilazione parte subito**, così la memoria si costruisce da v1
- in v1 le notifiche sono **semplici e deterministiche**
- in v2 le notifiche diventano **mirate**
- il completamento della partita al quarto giocatore è protetto con **transazione + `SELECT FOR UPDATE` + lock booking**
- tutto questo è **100% deterministico**, senza LLM

## 19. Schema operativo minimo da implementare

### Database / modelli
- `Club`
- `Player`
- `Match`
- `MatchPlayer`
- `CommunityInviteToken`
- `PlayerAccessToken` oppure `player_auth_tokens`
- `PlayerActivityEvent`
- `PlayerPlayProfile`
- `PlayerPushSubscription`
- `PlayerNotificationPreference`
- `NotificationLog`
- opzionale futuro: `MatchMessage`

### Backend services
- `PlayerIdentityService`
- `CommunityInviteService`
- `MatchService`
- `JoinMatchService`
- `CompleteMatchService`
- `NotificationService`
- `PlayerProfileService`

### Frontend principali
- `PlayPage`
- `MatchBoard`
- `MatchCard`
- `CreateMatchForm`
- `MyMatches`
- `JoinConfirmModal`
- `InviteAcceptPage`
- `SharedMatchPage`

### Priorità di implementazione
1. `/play` deterministica
2. invito community via WhatsApp
3. token player persistente in cookie httpOnly
4. join / create / complete match con lock corretto
5. share match via WhatsApp
6. web push v1
7. profilazione attiva da subito
8. notifiche mirate dopo soglia minima dati
9. opzionale futuro: thread per partita
