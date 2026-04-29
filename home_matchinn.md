# Home Matchinn — Hub operativo self-service

## 1. Obiettivo

La home di Matchinn non deve essere una semplice pagina di prenotazione, ma un **hub operativo leggero** da cui:

1. l’utente entra nelle proprie community;
2. l’utente scopre club e campi vicino a sé;
3. l’utente vede partite aperte in modo leggero;
4. l’utente ottiene accesso alla community in autonomia;
5. l’admin o gestore accede alla dashboard del club.

La home deve restare semplice, mobile-first e deterministica.
Non deve diventare un social network, una dashboard complessa o una landing marketing generica.

---

## 2. Scelta dominio e struttura

Soluzione consigliata:

```text
matchinn.app
→ landing pubblica / marketing / presentazione prodotto

join.matchinn.app
→ home prodotto operativa Matchinn

token.matchinn.app
→ dominio tecnico per invio email tramite Resend

join@token.matchinn.app
→ mittente email inviti e accesso community
```

La home prodotto deve vivere su:

```text
https://join.matchinn.app
```

---

## 3. Gerarchia della home

La home deve avere questa priorità:

```text
1. Le tue community
2. Trova campi vicino a te
3. Partite aperte vicino a te
4. Area club / dashboard admin
```

Ordine mobile:

```text
1. Header essenziale
2. Le tue community
3. Trova campi vicino a te
4. Partite da completare vicino a te
5. Area club
```

Ordine logico delle partite aperte in home:

```text
1. Partite 3/4 compatibili con il livello utente
2. Partite 2/4 compatibili con il livello utente
3. Partite 1/4 compatibili con il livello utente
4. Più vicine
5. Più prossime temporalmente
```

Prima vengono i match più facili da chiudere e coerenti con il livello dell’utente, poi la distanza.

---

## 4. Blocco 1 — Le tue community

Questo è il blocco principale per l’utente già riconosciuto.

### Se l’utente è riconosciuto

Mostrare le community a cui appartiene:

```text
Le tue community

Padel Savona
Partite aperte: 3
Manca 1 giocatore in una partita
[Entra]

Altro Club
Partite aperte: 1
[Entra]
```

CTA principale:

```text
Entra
```

La destinazione deve essere:

```text
/c/{club_slug}/play
```

Esempio:

```text
/c/padel-savona/play
```

### Se l’utente non è riconosciuto

Mostrare:

```text
Sei già in una community?
Richiedi il tuo codice OTP e rientra, oppure cerca un club vicino a te.
```

CTA consigliata:

```text
Ottieni codice OTP
```

Non introdurre login e password nella V1.

---

## 5. Come riconoscere l’utente

Scelta efficiente V1:

```text
Cookie httpOnly con PlayerAccessToken
```

Regole:

- niente login e password;
- niente localStorage per token sensibili;
- cookie sicuro, persistente e rinnovabile;
- il token riconosce il player sul browser corrente;
- le community visibili dipendono dalle membership attive del player;
- se l’utente usa lo stesso browser o dispositivo, vede subito le sue community;
- se cambia browser o dispositivo, rientra in autonomia tramite OTP.

### Recupero e rientro

Per la V1 non serve introdurre una feature separata di magic link.

Il rientro deve coincidere con il flusso standard di accesso self-service:

```text
Sei già in una community?
Inserisci email
Ricevi OTP
Verifica OTP
Rientri nelle tue community
```

Nota pratica:

- per la V1 l’email OTP è la scelta più semplice e coerente;
- il telefono può essere esteso in una fase successiva;
- il link invito del club continua a esistere, ma non deve essere l’unica porta di ingresso.

---

## 6. Community, club pubblici e preferiti

Distinzione definitiva:

```text
Le tue community
→ club in cui l’utente è già dentro

Club vicino a te
→ directory pubblica e geolocalizzata

Partite aperte vicino a te
→ vista pubblica leggera per capire dove vale la pena entrare

Preferiti
→ fuori scope V1
```

### Decisione sui preferiti

Non creare subito una feature “Preferiti” server-side.

Per la V1:

- mostrare solo “Le tue community”, “Club vicino a te” e “Partite aperte vicino a te”;
- non introdurre una tabella dedicata ai preferiti;
- non rendere i preferiti un concetto principale della home;
- se in futuro serve una scorciatoia discovery, valutarla solo dopo uso reale della directory pubblica.

Motivo: le community coprono già il caso più importante. I preferiti aggiungono un terzo contenitore mentale senza migliorare il core della V1.

---

## 7. Blocco 2 — Trova campi vicino a te

La geolocalizzazione va proposta, non forzata.

UX corretta:

```text
Trova campi vicino a te

[Usa la mia posizione]
oppure
[Cerca per città o CAP]
```

Non chiedere il permesso di geolocalizzazione all’apertura della home.
Chiederlo solo dopo click esplicito su “Usa la mia posizione”.

### Dati club da mostrare

Per ogni club:

```text
Nome club
Città / zona
Distanza
Sport disponibili
Numero partite aperte
Stato più interessante: "Manca 1 giocatore"
[Apri club]
```

Esempio:

```text
Padel Savona
Savona · 2,4 km
3 partite aperte · Manca 1 giocatore
[Apri club]
```

La CTA della card deve portare a:

```text
/c/{club_slug}
```

La home non deve saltare direttamente alla creazione partita.
Prima si apre il club, poi si entra nella community, poi si agisce.

---

## 8. Blocco 3 — Partite aperte vicino a te

La home può mostrare una vista leggera delle partite aperte, ma senza diventare una board completa.

Mostrare solo:

```text
Data
Ora
Livello partita
Stato 1/4, 2/4, 3/4
Club
Distanza
CTA
```

Non mostrare:

```text
Telefono
Email
Profili utenti
Chat
Storico
```

Ordinamento:

```text
1. Partite 3/4 compatibili con il livello dell’utente
2. Partite 2/4 compatibili con il livello dell’utente
3. Partite 1/4 compatibili con il livello dell’utente
4. Più vicine
5. Più prossime temporalmente
```

CTA consigliata:

```text
Apri club
```

Oppure, se l’utente è già riconosciuto sul browser corrente:

```text
Entra e gioca
```

La home deve restare un hub, non una playboard completa.

---

## 9. Pagina club pubblica

Rotta:

```text
/c/{club_slug}
```

Funzione:

- mostrare il club;
- mostrare informazioni pubbliche;
- mostrare partite aperte in forma leggera;
- permettere ingresso self-service alla community.

### Contenuti pubblici

Mostrare:

```text
Nome club
Indirizzo / zona
Sport disponibili
Numero campi
Partite aperte
Livelli disponibili
CTA ingresso community
```

Non mostrare:

```text
Telefoni
Email
Dati community interni
Profili giocatori
```

CTA community:

```text
Entra nella community
```

Se l’utente non è riconosciuto, la CTA apre il flusso OTP self-service.

---

## 10. Creazione partita da utente esterno

Regola definitiva:

```text
Un utente esterno non può creare una partita senza entrare nella community del club.
```

Flusso:

```text
Utente trova un club
↓
Apre pagina club
↓
Clicca "Crea partita" oppure "Entra nella community"
↓
Se non è riconosciuto:
  richiede OTP in autonomia
↓
Verifica OTP
↓
Entra nella community
↓
Può creare partita
```

### Modello accesso community V1

Per la V1 non conviene introdurre tre modalità diverse come OPEN, APPROVAL_REQUIRED e INVITE_ONLY.

Scelta operativa consigliata:

```text
SELF_SERVICE_OTP
→ l’utente richiede OTP in autonomia
→ verifica il codice
→ entra nella community dal browser corrente
```

Motivo:

- riduce complessità di prodotto e implementazione;
- evita dipendenza dal club per il primo ingresso;
- rende la home coerente con la promessa “entra nelle tue community”; 
- mantiene l’invito come canale utile ma non obbligatorio.

---

## 11. Accesso admin

L’accesso admin deve essere presente ma secondario.

Label consigliata:

```text
Area club
```

Non usare come label principale:

```text
Admin
```

Perché l’utente finale non deve percepire la home come una pagina tecnica.

Posizione:

```text
Header desktop
Footer mobile
```

CTA:

```text
Accedi alla dashboard
```

Destinazione:

```text
/admin
```

Oppure, in futuro:

```text
/c/{club_slug}/admin
```

Per ora mantenere la dashboard admin esistente senza complicare routing e permessi.

---

## 12. Rotte consigliate

Rotte prodotto:

```text
/
→ home Matchinn su join.matchinn.app

/clubs
→ directory club

/clubs/nearby
→ risultati geolocalizzati o ricerca città/CAP

/c/{club_slug}
→ pagina pubblica club

/c/{club_slug}/play
→ community/playboard del club

/c/{club_slug}/play/access
→ ingresso o rientro self-service via OTP

/c/{club_slug}/play/invite/{token}
→ accettazione invito canonica

/c/{club_slug}/play/matches/{match_token}
→ pagina pubblica controllata della partita condivisa

/admin
→ dashboard admin esistente
```

Il link canonico di invito deve restare:

```text
https://join.matchinn.app/c/{club_slug}/play/invite/{TOKEN}
```

Esempio:

```text
https://join.matchinn.app/c/default-club/play/invite/<TOKEN>
```

Il link canonico di accesso self-service deve essere:

```text
https://join.matchinn.app/c/{club_slug}/play/access
```

Non usare come link stabile:

```text
/play/invite/<TOKEN>
```

perché dipende dal tenant o da parametri aggiuntivi.

---

## 13. Modello dati minimo utile

Per supportare questa home senza overengineering servono questi concetti minimi.

### Club

Già previsto.

Campi utili:

```text
id
slug
name
city
address
latitude
longitude
sports
courts_count
is_public
```

### Player

Già previsto.

Campi utili:

```text
id
name
surname
phone
email
```

### PlayerClubMembership

Serve per distinguere le community reali dell’utente.

Campi minimi:

```text
id
player_id
club_id
status
joined_at
left_at
```

Stati minimi V1:

```text
ACTIVE
LEFT
```

Questa tabella è importante perché l’utente può appartenere a più community.

### PlayerAccessToken

Serve per riconoscere il player sul browser corrente.

Campi minimi:

```text
id
player_id
token_hash
issued_at
expires_at
last_used_at
```

Principio chiave:

```text
Il token autentica il player.
Le membership determinano quali community mostrare in home.
```

### Preferiti

Non introdurre tabella V1.

---

## 14. Home anonima vs home riconosciuta

### Home anonima

Mostrare:

```text
Sei già in una community?
[Ottieni codice OTP]

Trova campi vicino a te
Cerca per città o CAP
Partite quasi complete vicino a te
Area club
```

Non mostrare “Le tue community” come blocco vuoto centrale.

### Home riconosciuta

Mostrare:

```text
Le tue community
Trova altri campi vicino a te
Partite quasi complete
Area club
```

Le community dell’utente devono avere priorità assoluta.

---

## 15. Cosa non aggiungere ora

Non aggiungere:

```text
Chat utenti
Feed social
Ranking
Recensioni giocatori
Profili pubblici ricchi
Follow utenti
Preferiti server-side complessi
Magic link separato di recupero accesso
Marketplace club
Login e password
App nativa
Wallet
Tornei complessi
AI/chatbot
```

Queste funzioni aumentano complessità senza migliorare il core della V1.

---

## 16. Priorità implementativa

Ordine consigliato:

```text
1. Home prodotto semplice su join.matchinn.app
2. Riconoscimento utente con cookie httpOnly
3. Accesso self-service via OTP
4. Blocco "Le tue community"
5. Directory club pubblica base
6. Geolocalizzazione e ricerca città/CAP
7. Pagina pubblica club
8. Vista leggera partite aperte
9. Accesso admin da "Area club"
```

---

## 17. Decisione finale

La home Matchinn deve essere:

```text
un hub operativo leggero e self-service per giocatori e club
```

Non deve essere:

```text
una landing marketing pura
una dashboard complessa
un social network
una pagina admin mascherata
```

Formula finale:

```text
join.matchinn.app
→ entra nelle tue community
→ trova club vicino a te
→ vedi partite aperte leggere
→ ottieni accesso via OTP
→ entra nella community
→ gioca
```

La soluzione più efficiente per la V1 è:

```text
Le tue community
+ Club vicino a te
+ Partite aperte leggere
+ Accesso self-service OTP
+ Area club
```

Gli inviti restano supportati, ma non devono essere il meccanismo principale su cui costruire la home prodotto.
