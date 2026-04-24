## Regole di pagamento per il flusso community

Qui la decisione più recente è molto importante.

Per /play e flusso community

La regola di default è:

nessun pagamento online
nessuna caparra
quando la partita arriva a 4/4
il sistema prenota automaticamente il campo
crea la booking
la booking va in stato confermato
il pagamento avviene al campo

Questa scelta è coerente con il comportamento reale dei club.

Motivazione
più vicina all’esperienza reale
meno attrito
più semplice da spiegare
meno complessità tecnica
niente problemi di refund / stripe / paypal nel flusso community
Rischi
no-show
affidabilità utenti
Contromisure
storico no-show
stato NO_SHOW
admin può segnare completed / cancelled / no-show
notifiche ai partecipanti
log di chi si è unito


## caparra opzionale configurabile da admin

Abbiamo deciso che il club può comunque scegliere di attivare una caparra anche per il flusso community.

Configurazione admin

Il club può decidere:

caparra community attiva: sì / no
importo caparra
timeout pagamento
Regola

Questa impostazione vale per il flusso community /play.

Default consigliato
caparra community OFF
Se attivata

Quando la partita arriva a 4:

si crea la booking
la booking può andare in stato PENDING_DEPOSIT
se la caparra viene pagata entro il timeout:
booking CONFIRMED
se non viene pagata:
booking EXPIRED
slot rilasciato o gestito da admin
Decisione pratica
feature opzionale
default OFF
una sola regola per il flusso community