## Geolocalizzazione e visibilità dei club

Abbiamo deciso che i club presenti nell’app possono essere visibili anche a utenti esterni alla community.

Obiettivo

Consentire a un utente che:

non appartiene ancora a un club
è in viaggio
è in vacanza
cerca un posto dove giocare in una nuova zona

di:

vedere quali club usano l’app
trovare quelli vicini
aprire la pagina pubblica del club
capire se vale la pena entrare nella community del club
Regola di base

La struttura corretta è questa:

club pubblico e visibile
community del club privata/chiusa

Quindi:

il club può essere scoperto da tutti
la community e le funzioni interne restano accessibili solo agli utenti del club
Geolocalizzazione

Per la geolocalizzazione base non servono API Google.

Soluzione scelta

Usare:

Geolocation API del browser per ottenere la posizione dell’utente
coordinate già salvate per ogni club
calcolo distanza lato backend o lato app
Flusso corretto
l’utente apre la sezione tipo:
Trova club
Club vicino a me
l’utente può:
consentire la geolocalizzazione
oppure cercare manualmente per città / CAP / provincia
il sistema mostra:
club vicini
distanza
nome club
città / zona
eventuale numero campi
link alla pagina pubblica del club
Dati minimi pubblici del club

Ogni club deve avere almeno:

nome club
club_slug univoco
città / zona
indirizzo o coordinate
numero campi
eventuale contatto pubblico
eventuale indicazione se la community è aperta a nuovi ingressi
Club con stesso nome

Abbiamo chiarito che il nome del club non può essere l’identificatore pubblico univoco.

Regola corretta

Usare:

club_id come chiave interna
club_slug come identificatore pubblico univoco

Quindi due club con nomi simili o uguali devono avere slug diversi.

Esempio:

padel-savona-rocca
padel-savona-centro
Routing corretto

In prospettiva, la struttura migliore è:

directory club:
/clubs
/clubs/nearby
pagina pubblica club:
/c/{club_slug}
pagina community / club:
/c/{club_slug}/play

Se in v1 c’è un solo club, puoi partire in modo più semplice, ma l’architettura deve essere già pensata in chiave club-specifica.

Cosa vede un utente esterno

Un utente esterno deve poter vedere:

l’esistenza del club
le info pubbliche del club
il fatto che il club usa l’app
una vista pubblica leggera delle partite aperte
il bottone per entrare nella community o accedere al club
Cosa NON vede un utente esterno

Un utente esterno non deve vedere:

nomi dei giocatori
dettagli interni della community
chat interna
storico personale
notifiche
informazioni riservate del club
Obiettivo di business

Questa parte serve a:

rendere il prodotto scopribile
aumentare l’utilità in trasferta o vacanza
far crescere l’app anche fuori dal club abituale
dare più valore al network dei club presenti


## Partite aperte per utenti esterni

Abbiamo deciso che un utente esterno deve poter vedere, nella pagina pubblica del club, una vista leggera delle partite aperte.

Obiettivo

Aiutare un utente esterno a capire rapidamente:

se il club ha partite aperte
se ci sono partite compatibili con il suo livello
se il club è interessante per lui
se ha senso entrare nella community per unirsi

Questo è molto importante soprattutto per:

utenti in vacanza
utenti fuori città
utenti senza gruppo di gioco già formato
Vista pubblica partite aperte

La pagina pubblica del club deve mostrare:

solo partite OPEN
solo sui prossimi giorni utili
in forma sintetica e pubblica
filtrabili per livello
Filtro per livello

Abbiamo deciso che è utile aggiungere un menu livelli nella pagina pubblica del club.

Livelli
Principiante
Intermedio basso
Intermedio medio
Intermedio alto
Avanzato
Cosa deve fare il filtro

Permettere all’utente esterno di vedere più rapidamente:

quali partite sono aperte
per quale livello
con quanti posti liberi

Questa feature è utile perché un utente fuori zona spesso non ha compagni e deve trovare una partita già adatta a lui dentro il club.

Dati da mostrare nella vista pubblica delle partite

Per ogni partita aperta pubblica, mostrare:

giorno
data
orario
livello della partita
stato giocatori:
1/4
2/4
3/4
messaggio sintetico:
Manca 1 giocatore
Mancano 2 giocatori
Ordinamento corretto

Anche nella vista pubblica, l’ordine giusto è:

partite 3/4
partite 2/4
partite 1/4

Quindi l’utente esterno vede prima le occasioni più facili da chiudere.

Cosa NON mostrare nella vista pubblica

Nella pagina pubblica delle partite per utenti esterni non vanno mostrati:

nomi dei giocatori
numeri di telefono
chat partita
dettagli interni community
dati personali

I nomi restano visibili solo nella parte privata/community, non nella parte pubblica.

CTA corretta per utente esterno

L’utente esterno non deve poter entrare direttamente nel flusso privato senza passaggi.

Le CTA corrette sono:

Entra nella community
Accedi al club
Richiedi accesso
oppure, se previsto, onboarding self-service dal link partita
Relazione con la community chiusa

La logica corretta è:

la visibilità delle partite aperte può essere pubblica
il join e la gestione piena della partita restano privati/community

Quindi:

pubblico = scoperta
community = azione
Valore di questa scelta

Questa parte migliora:

conversione utenti esterni → community
utilità dell’app fuori dal club abituale
visibilità dei club presenti nel network
velocità con cui un utente capisce se in quel club troverà partite per il suo livello
Struttura finale corretta

Per utenti esterni, la struttura ideale è:

Directory pubblica club
elenco club
ricerca per luogo o città
ordinamento per vicinanza
Pagina pubblica del club
info club
filtro per livello
partite aperte in forma leggera
CTA per entrare nella community
Community del club
accesso completo a /play
join partite
nomi partecipanti
notifiche
funzioni utente
Sintesi finale
Geolocalizzazione e visibilità club
i club devono essere pubblicamente visibili nell’app
la ricerca deve funzionare per geolocalizzazione o per città/zona
non servono API Google per la geolocalizzazione base
ogni club deve avere club_slug univoco
la community del club resta privata/chiusa
Partite aperte per utenti esterni
gli utenti esterni devono poter vedere una vista pubblica leggera delle partite aperte del club
devono poter filtrare per livello
devono vedere giorno, orario, livello e stato 1/4, 2/4, 3/4
non devono vedere nomi o dati dei giocatori
la pagina pubblica deve servire a far capire rapidamente se quel club offre partite compatibili
l’azione completa resta nella community del club