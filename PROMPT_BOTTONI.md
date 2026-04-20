# PROMPT BOTTONI OPERATIVO PER COPILOT — CALIBRATO SUL REPOSITORY REALE

Agisci come un **Senior Product Designer**, **Senior Frontend Engineer React/TypeScript/Tailwind** e **UX/UI Debugger**.

Devi eseguire una **patch mirata, piccola e coerente** sulla sola tab **Dashboard admin** del frontend di PadelBooking.

## Obiettivo

Correggere due problemi UX/UI reali e ad alta visibilità nella Dashboard admin:

1. su mobile, quando si clicca un bottone della dashboard, ad esempio `Prenotazioni Attuali`, i CTA hero `Aggiorna dashboard` ed `Esci` non devono sparire, scorrere fuori vista o diventare irraggiungibili
2. i bottoni della tab `Dashboard admin` devono usare il feedback cromatico richiesto quando risultano cliccati / attivi:
   - stato chiaro: `#cffafe` con testo nero
   - stato scuro: `#0e7490` con testo bianco

## Contesto reale del repository

Il repository ha gia un design system funzionante, da non rifare.

In particolare:

- `frontend/src/index.css` contiene gia classi shared come:
  - `btn-primary`
  - `btn-secondary`
  - `surface-card`
  - `surface-muted`
- la pagina coinvolta e `frontend/src/pages/AdminDashboardPage.tsx`
- la navigazione admin e resa da `frontend/src/components/AdminNav.tsx`
- il brand testuale e in `frontend/src/components/AppBrand.tsx`
- la suite frontend e gia presente e va aggiornata solo se il comportamento atteso cambia davvero

## Regola fondamentale

Non devi fare un redesign generale.

Devi fare una **patch chirurgica sulla Dashboard admin**, mantenendo il layout esistente ma correggendo il comportamento mobile e il feedback dei bottoni.

## Problemi da risolvere davvero

### 1. CTA hero che spariscono su mobile

Quando l'utente interagisce con la dashboard su mobile, i CTA hero `Aggiorna dashboard` ed `Esci` non devono:

- sparire dopo il tap su altri bottoni
- essere spinti fuori viewport in modo inatteso
- risultare coperti dalla navigazione o da altri blocchi
- dipendere da una posizione fragile che su mobile peggiora l'uso della pagina

Devi cercare e correggere la causa reale nel codice, ad esempio:

- ordine dei blocchi nella hero
- layout responsive fragile
- uso improprio di `absolute`, `sticky`, `overflow`, `z-index`, `backdrop`, margini negativi o container che collassano
- conflitto tra toolbar hero e `AdminNav`

### 2. Colori dei bottoni nella Dashboard admin

Nella sola tab `Dashboard admin`, i bottoni devono esprimere in modo chiaro il feedback di interazione.

Richiesta precisa:

- un bottone cliccato / attivo deve poter usare `#cffafe` con testo nero
- un bottone cliccato / attivo in variante forte deve poter usare `#0e7490` con testo bianco

Importante:

- non applicare questi colori in modo casuale a tutto il sito
- non rompere la gerarchia tra bottoni primari, secondari e link discreti
- se serve, limita la modifica alla Dashboard admin o a una variante riusabile ma piccola

## Ambito stretto di intervento

Lavora prima su questi file, se presenti:

- `frontend/src/pages/AdminDashboardPage.tsx`
- `frontend/src/index.css`
- `frontend/src/components/AdminNav.tsx`
- `frontend/src/components/AppBrand.tsx`
- `frontend/src/pages/AdminDashboardPage.test.tsx`

Se bastano solo i primi due, non toccare gli altri inutilmente.

## Strategia di patch preferita

### Preferenza 1
Riusa le classi shared esistenti (`btn-primary`, `btn-secondary`) e aggiungi solo il minimo indispensabile.

### Preferenza 2
Se i colori richiesti servono solo nella Dashboard admin, preferisci una variante locale o una costante CSS/className mirata invece di cambiare tutto il sistema globale.

### Preferenza 3
Per il bug mobile, privilegia una soluzione strutturale semplice e robusta:

- ordine corretto dei blocchi
- comportamento prevedibile su viewport piccole
- nessuna toolbar che scompare dopo il tap
- nessun hack fragile se puo bastare un layout piu stabile

## Vincoli non negoziabili

- non introdurre dark mode
- non creare un nuovo design system
- non toccare la logica business
- non cambiare routing o navigazione funzionale
- non rifattorizzare componenti sani solo per uniformita teorica
- non modificare pagine fuori dalla Dashboard admin salvo dipendenze minime strettamente necessarie

## Cosa non fare

- non fare restyling generale dell'area admin
- non cambiare tutta la palette del progetto
- non applicare `#cffafe` e `#0e7490` a ogni bottone dell'app indiscriminatamente
- non introdurre nuove dipendenze
- non risolvere il problema mobile con spazi vuoti o padding casuali senza capire la causa reale

## Checklist di verifica richiesta

Verifica almeno:

- [ ] su mobile `Aggiorna dashboard` ed `Esci` restano visibili e raggiungibili anche dopo il tap su `Prenotazioni Attuali` o altri bottoni della dashboard
- [ ] i bottoni della Dashboard admin mostrano il feedback cromatico richiesto quando sono cliccati / attivi
- [ ] `#cffafe` e `#0e7490` sono usati in modo coerente e non casuale
- [ ] non e stato introdotto un redesign generale
- [ ] non sono state toccate parti sane senza motivo
- [ ] i test frontend rilevanti passano ancora

## Output atteso

Quando esegui il lavoro:

1. individua la causa reale del problema mobile
2. spiega perche il comportamento attuale e sbagliato lato UX/UI
3. applica patch minime file per file
4. indica chiaramente come hai assegnato i due stati colore richiesti
5. aggiorna i test solo dove il comportamento atteso cambia davvero
6. valida con test/build frontend dove serve

## Regola finale

Fai una **patch concreta, piccola e difendibile** sulla Dashboard admin.

L'obiettivo non e "rendere piu bella" la pagina in generale, ma:

- evitare che i CTA hero spariscano su mobile
- rendere coerente e chiaro il feedback dei bottoni con i colori richiesti