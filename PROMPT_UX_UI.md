# PROMPT UX/UI OPERATIVO PER COPILOT

Agisci come un **Senior Product Designer**, **Senior Frontend Engineer React/TypeScript/Tailwind** e **Design System Maintainer**.

Devi eseguire una **patch UX/UI mirata e minima** sull’app di prenotazione padel attuale, adattandoti alla struttura reale del repository.

## Obiettivo

Portare il frontend a un livello visivo più alto, coerente e professionale, applicando una palette/design system unificati e rimuovendo i principali punti in cui i componenti usano colori o classi Tailwind hardcoded invece dei token di tema.

L’obiettivo non è rifare il frontend.  
L’obiettivo è:

- consolidare il design system
- uniformare i colori tra light/dark mode
- migliorare la qualità percepita della UI
- eliminare gli hardcode cromatici principali
- mantenere patch minima
- evitare regressioni

## Vincoli non negoziabili

- **patch minima**
- non toccare logica di business
- non toccare routing
- non toccare autenticazione
- non toccare API
- non toccare modelli dati
- non toccare stato applicativo salvo strettamente necessario per il rendering
- non rinominare file
- non spostare file
- non cambiare struttura dei componenti
- non riscrivere pagine da zero
- non introdurre librerie UI nuove
- non introdurre dipendenze inutili
- non fare refactor ampi

## Regola di adattamento al repository reale

I file di riferimento del progetto attuale **non sono quelli dell’esempio base**.

Devi quindi:

1. identificare nel repository attuale i file reali che svolgono il ruolo di:
   - global stylesheet / global theme CSS
   - theme tokens / theme hook / theme constants
   - componenti UI del flusso pubblico booking
   - componenti UI dell’area admin
2. applicare la patch sugli equivalenti reali
3. mantenere la modifica più piccola possibile

Se i nomi file differiscono, **non inventare nuovi file**: modifica quelli esistenti equivalenti.

## Priorità della patch

Applica le modifiche in quest’ordine:

1. file globale di stile / token CSS
2. file di configurazione del tema o token TS
3. componenti pubblici centrali del booking flow
4. componenti admin con colori hardcoded
5. verifica finale light/dark + coerenza visuale

## Obiettivo estetico

La UI finale deve risultare:

- più coerente
- più pulita
- più moderna
- più leggibile
- più “product-like”
- meno dipendente da classi Tailwind hardcoded sparse
- più governata da token e variabili di tema

Il risultato deve sembrare una web app reale e curata, non una somma di componenti disallineati.

## Regola fondamentale sul design system

Tutti i colori principali devono arrivare da:

- CSS variables globali, oppure
- theme tokens TypeScript, oppure
- layer centralizzato equivalente già presente nel progetto

Non devono restare hardcoded nei componenti, salvo casi marginali veramente neutri o strutturali.

## Interventi richiesti

Devi eseguire una patch con queste finalità:

### 1. Allineamento palette globale
Individua il file globale che definisce i colori applicativi e porta il sistema a una palette coerente light/dark.

La palette deve prevedere almeno token equivalenti a:

- background app principale
- background alternativo
- panel / card
- panel strong
- border
- border strong / secondary
- text primary
- text muted
- text subtle
- accent primary
- accent hover
- accent soft
- accent gradient
- success
- warning
- danger
- info
- eventuali token CTA hover / glow / bubble se già coerenti con il progetto

Se il progetto ha già un set di token, **non sostituire l’architettura**: aggiorna i valori e completa solo i token mancanti realmente necessari.

### 2. Allineamento theme config / hook / constants
Individua il file reale che espone i colori tema al frontend, ad esempio:
- hook tema
- constants tema
- oggetto themeColors
- config token

Aggiorna solo la parte colori, mantenendo invariata l’API interna del file, salvo piccole aggiunte strettamente necessarie.

### 3. Eliminazione hardcoded nei componenti critici
Trova i componenti che usano classi hardcoded tipo:
- `bg-*`
- `text-*`
- `border-*`
- classi slate/gray/zinc/emerald/red/amber/blue hardcoded
- colori inline hardcoded non governati dal tema

Applica sostituzioni minime usando:
- CSS variables
- token di tema
- stili inline minimi solo dove la struttura del componente lo rende più sicuro
- classi semanticamente agganciate ai token, se già presenti

## Componenti prioritari da correggere

Parti dai componenti più visibili del prodotto reale.

### Area pubblica — priorità alta
Correggi prima i componenti che impattano la UX utente del booking flow, ad esempio gli equivalenti reali di:

- card disponibilità slot
- selettore durata
- riepilogo prenotazione
- box caparra
- box tariffe informative
- stato pagamento
- stato prenotazione confermata / annullata / scaduta
- badge di stato
- CTA principali

### Area admin — priorità media
Correggi poi i componenti admin più esposti visivamente, ad esempio gli equivalenti reali di:

- card prenotazione
- tabella/lista prenotazioni
- badge stato
- azioni rapide
- box ricorrenze
- box blackout/chiusure
- pannelli di dettaglio

### Componenti trasversali — priorità alta
Correggi gli equivalenti reali di:

- alert success/warning/error/info
- badge
- card
- modali
- pannelli
- bottoni primari/secondari/danger
- empty states
- skeleton/loading state se usano colori hardcoded

## Regola sulla patch dei componenti

Per ogni componente modificato:

- cambia **solo** la parte visuale
- non cambiare props
- non cambiare logica
- non cambiare struttura JSX salvo minimo indispensabile
- non cambiare comportamento
- non cambiare naming
- non estrarre nuovi componenti, salvo caso davvero necessario e minimo

## Modalità di sostituzione preferita

Usa questa gerarchia:

### Preferenza 1
Sostituisci colori hardcoded con classi o stili che puntano ai token già esistenti.

### Preferenza 2
Se il progetto non ha classi semantiche già pronte, usa `style={{ ... }}` con `var(--token)` nei componenti più problematici.

### Preferenza 3
Aggiungi solo piccole utility semanticamente coerenti se davvero indispensabili, senza introdurre refactor.

## Cosa cercare esplicitamente nel codice

Scansiona il frontend e individua almeno:

- classi `bg-white`, `bg-black`
- classi `bg-slate-*`, `bg-gray-*`, `bg-zinc-*`
- classi `text-slate-*`, `text-gray-*`, `text-zinc-*`
- classi `border-slate-*`, `border-gray-*`, `border-zinc-*`
- classi `bg-emerald-*`, `text-emerald-*`
- classi `bg-red-*`, `text-red-*`
- classi `bg-amber-*`, `text-amber-*`
- classi `bg-blue-*`, `text-blue-*`
- stili inline con hex hardcoded
- override dark mode basati su cascade Tailwind che andrebbero sostituiti con token

Non fare sostituzioni cieche su tutto il progetto: concentrati sui componenti centrali e sui punti più visibili.

## Regole UX/UI da far emergere dopo la patch

Il risultato visivo deve migliorare soprattutto su:

### Booking flow pubblico
- chiarezza della CTA prenota
- leggibilità di date/orari/durate
- distinzione tra slot disponibile e non disponibile
- evidenza della caparra
- separazione netta tra caparra online e saldo al campo
- leggibilità delle tariffe informative
- feedback chiaro sugli stati di pagamento e conferma

### Area admin
- leggibilità delle liste
- badge stato coerenti
- call to action più pulite
- pannelli meno “Tailwind default”
- migliore contrasto in light/dark

### Design system complessivo
- maggiore uniformità tra panel, border, text e alert
- riduzione dei colori fuori sistema
- dark mode più solida
- niente elementi che sembrano staccati dal resto

## Regola sulla sidebar / navigazione / shell applicativa

Se nel progetto esistono componenti shell tipo:
- sidebar
- topbar
- nav link
- section title
- page surface

verifica se i colori sono ancora hardcoded o dipendono da override Tailwind fragili.

Se sì:
- correggi anche questi punti
- mantieni patch minima
- non cambiare layout
- non cambiare markup salvo minimi aggiustamenti

## Regola sui bottoni

Controlla i bottoni principali del progetto:

- primary
- secondary
- danger
- ghost / outline
- CTA booking
- CTA admin

Se usano colori hardcoded non coerenti con il tema:
- riallineali ai token
- mantieni stessa logica
- mantieni stessa semantica
- migliora hover/focus solo se già supportati dalla struttura attuale

## Regola sugli stati semantici

I colori semantici devono essere governati da token per:

- success
- warning
- danger
- info

Applicali in modo coerente su:
- badge
- alert
- small cards
- status chip
- box di conferma / errore / warning

## Regola sugli override dark mode

Se trovi override dark mode del tipo:
- selettori a cascata che correggono classi Tailwind (`[class*='text-gray-']`, ecc.)
- correzioni sparse solo per far “funzionare” il dark theme
- hack visivi difficili da mantenere

rimuovili **solo se** diventano superflui grazie ai token tema corretti.

Non rimuovere override utili se la loro eliminazione produce regressioni.

## Output atteso

Voglio un output operativo e disciplinato.

### 1. Mappa file reali
Prima indica quali file reali del repository hai identificato come equivalenti di:
- stylesheet globale
- theme tokens / useTheme / constants
- componenti pubblici critici
- componenti admin critici

### 2. Piano patch minimo
Elenca in modo breve:
- quali file tocchi
- perché
- che cosa cambi
- che cosa lasci invariato

### 3. Patch file per file
Mostra le modifiche file per file.

Per ogni file:
- mostra solo il codice realmente modificato oppure il file completo se necessario
- non mostrare codice invariato non utile
- non inventare file

### 4. Verifica finale
Chiudi con una checklist di verifica concreta.

## Checklist di verifica richiesta

Verifica almeno:

- [ ] light mode coerente su background, panel, text, border
- [ ] dark mode coerente su background, panel, text, border
- [ ] booking flow pubblico coerente con i token
- [ ] area admin coerente con i token
- [ ] i componenti modificati non usano più colori hardcoded critici
- [ ] badge success/warning/danger/info allineati al tema
- [ ] nessuna regressione su props, logica, routing o API
- [ ] nessun errore TypeScript introdotto
- [ ] nessuna regressione visuale evidente su CTA principali
- [ ] nessuna rottura del layout mobile-first

## Criterio finale di qualità

Il lavoro è corretto solo se:

- la patch è piccola
- la UI migliora davvero
- il design system è più coerente
- i componenti più visibili smettono di dipendere da colori hardcoded
- non vengono toccate logiche non UX/UI
- il codice resta semplice e mantenibile

## Regola finale

Non fare un redesign totale.  
Non fare refactor architetturali.  
Non fare pulizia generica del codice.

Fai una **patch UX/UI chirurgica, intelligente e coerente**, adattata ai file reali del progetto attuale.