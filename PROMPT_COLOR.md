# PROMPT COLORE OPERATIVO PER COPILOT — CALIBRATO SUL REPOSITORY REALE

Agisci come un **Senior Product Designer**, **Senior Frontend Engineer React/TypeScript/Tailwind** e **UI Consistency Reviewer**.

Devi eseguire una **verifica cromatica e di gerarchia UI minima, precisa e coerente** sul frontend attuale di PadelBooking.

## Obiettivo

Allineare colori, gerarchia dei bottoni, badge, feedback inline e piccoli comportamenti visuali ai pattern gia presenti nel repository, **senza rifare il design system** e senza introdurre un nuovo layer di token.

## Palette reale del repository

Questa e la palette canonica da rispettare:

- shell scura: `ink.950 = #04111f`, `ink.900 = #0f172a`
- testo e superfici: famiglia `slate-*` + classi condivise in `index.css`
- accent principale: `brand/cyan`
  - `#ecfeff`
  - `#cffafe`
  - `#06b6d4`
  - `#0891b2`
  - `#0e7490`
- feedback positivi: `emerald-*`
- feedback di attenzione: `amber-*`
- feedback errore/blocco: `rose-*`
- superfici card: `surface-card`, `surface-muted`
- `#00497a` esiste nel lockup pubblico/logo e **non deve diventare un colore CTA generico**

## Pattern gia presenti da riusare

Nel repository esistono gia pattern condivisi che hanno priorita alta:

- `btn-primary`
  - CTA primaria
  - azione dominante dell'area
  - pieno, leggibile, riconoscibile
- `btn-secondary`
  - azione secondaria
  - stessa altezza e stessa grammatica del primario
- `btn-ghost`
  - azioni locali a bassa enfasi
- `alert-info`, `alert-success`, `alert-warning`, `alert-error`
  - feedback inline standard
- `status-pill`
  - base comune per badge di stato
- `surface-card`, `surface-muted`
  - contenitori e box di supporto

## Regola fondamentale

Se due bottoni hanno **stesso ruolo e stesso peso UX**, devono avere una gerarchia cromatica coerente e lo stesso comportamento responsivo.

Quindi:

- non lasciare un bottone con colore custom isolato se esiste gia una classe condivisa equivalente
- non mischiare CTA primarie scure, CTA cyan custom e CTA bianche senza una ragione reale
- non usare il colore come unica distinzione se il ruolo UX non cambia

## Vincoli non negoziabili

- non introdurre dark mode
- non creare un nuovo token system globale
- non sostituire la palette slate di base
- non rifare header, sidebar o layout globale
- non cambiare la logica di business
- non fare refactor teorici
- applica **solo patch piccole, locali e difendibili**

## Cosa verificare davvero nel codice

Cerca e correggi solo incongruenze reali come:

- bottoni primari che usano colori custom fuori gerarchia
- bottoni secondari che cambiano colore senza cambiare funzione
- badge semantici con classi hardcoded scollegate dal layer shared
- alert o feedback inline che ignorano le classi `alert-*`
- CTA che su mobile escono dal contenitore o perdono allineamento
- pannelli espandibili che partono aperti quando l'UX richiede stato compresso iniziale

## Target prioritari reali del repository

Lavora prima su questi file se esistono:

- `frontend/src/pages/AdminDashboardPage.tsx`
- `frontend/src/components/StatusBadge.tsx`
- `frontend/src/index.css`
- `frontend/src/components/SectionCard.tsx`

## Incongruenze gia note da verificare

### 1. Dashboard admin
- il pulsante `Aggiorna dashboard` non deve sembrare di un'altra famiglia cromatica rispetto agli altri CTA dell'area admin
- la hero admin deve mantenere la gerarchia primaria/secondaria senza introdurre colori ad hoc non necessari
- su mobile i CTA della hero devono stare allineati e contenuti bene

### 2. Prenotazioni e occupazione
- i bottoni devono restare contenuti nella card su mobile
- su desktop devono risultare allineati con il blocco testuale, non sospesi o disassati
- se necessario, i CTA possono stare sotto la descrizione anziche nel lato destro dell'header, ma senza rifare la card

### 3. Sezioni collassabili
- nella dashboard admin le sezioni collassabili devono partire **compresse/chiuse**
- mantieni invariata la logica di espansione/chiusura

### 4. Badge di stato
- `StatusBadge.tsx` deve usare una base condivisa (`status-pill`) e varianti coerenti
- evita combinazioni semantiche sparse direttamente nel componente se possono essere centralizzate in `index.css`

## Strategia di patch preferita

### Preferenza 1
Riusa classi gia presenti in `frontend/src/index.css`.

### Preferenza 2
Se manca solo un piccolo tassello shared, aggiungilo in `index.css` e poi riusalo nei componenti.

### Preferenza 3
Per i problemi responsive, preferisci:

- `w-full` su mobile
- `sm:w-auto` o equivalenti da tablet/desktop
- layout stacked su mobile quando evita overflow o disallineamenti

## Cosa non fare

- non introdurre nuove palette globali
- non diffondere `#00497a` fuori dal suo uso attuale
- non trasformare i pulsanti secondari in primari solo per farli "risaltare"
- non cambiare componenti sani per uniformita teorica
- non toccare il booking flow se il problema e solo visuale

## Checklist di verifica richiesta

Verifica almeno:

- [ ] nessun riferimento a dark mode e stato introdotto
- [ ] la palette slate/ink di base e rimasta invariata
- [ ] i CTA della Dashboard admin hanno una gerarchia coerente col design system reale
- [ ] la card `Prenotazioni e occupazione` non ha overflow mobile
- [ ] i pannelli collassabili della dashboard partono chiusi
- [ ] `StatusBadge.tsx` usa un layer shared piu coerente

## Output atteso

Quando esegui il lavoro:

1. indica le incongruenze reali trovate
2. spiega perche sono problemi UX/UI concreti
3. applica patch minime file per file
4. specifica cosa hai lasciato invariato
5. verifica con test o build solo dove serve

## Regola finale

Non fare un redesign.
Non inseguire la purezza teorica.

Fai una **patch cromatica e gerarchica chirurgica**, concreta e coerente con il repository reale.