# PROMPT CLUB

Agisci come un:

- Prompt Engineer senior
- UX Specialist senior
- SaaS Product Architect senior
- Full-Stack Engineer senior
- Platform Engineer pragmatico
- QA tecnico rigoroso

Leggi obbligatoriamente prima questi file di contesto:

- ../prompt_engineering.md
- prompt_master.md
- STATO_FASE_9.MD
- ../frontend/src/App.tsx
- ../frontend/src/pages/AdminLoginPage.tsx
- ../frontend/src/pages/PublicBookingPage.tsx
- ../frontend/src/pages/PlayAccessPage.tsx
- ../frontend/src/components/PageBrandBar.tsx
- ../frontend/src/index.css
- ../backend/app/models/__init__.py
- ../backend/app/api/routers/platform.py
- ../backend/app/api/routers/admin_auth.py
- ../backend/app/schemas/billing.py
- ../backend/app/services/billing_service.py
- ../backend/app/services/tenant_service.py

Leggi inoltre le superfici reali piu vicine al problema prima di proporre o modificare codice:

- ../frontend/src/services/adminApi.ts
- ../frontend/src/services/api.ts
- ../backend/app/api/deps.py
- ../backend/app/main.py

## Obiettivo

Progetta e implementa l'architettura corretta, completa ed efficiente per la registrazione self-service dei club all'app, mantenendo il repository coerente con il codice esistente, con la UX/UI attuale e con il modello SaaS gia presente.

Il risultato deve introdurre un funnel pubblico club-first che permetta a un club di:

1. inserire i propri dati e quelli del referente;
2. verificare l'email tramite link con token;
3. verificare il numero telefonico dichiarato tramite OTP inviato via email;
4. attivare 1 mese di prova gratuita;
5. essere provisionato come tenant reale con admin owner;
6. arrivare a una pagina finale chiara con i prossimi passi.

## Verita del repository da rispettare

Parti da questi fatti gia verificati nel codice reale:

- oggi la pagina admin login e solo una superficie di accesso riservato; non esiste una registrazione club self-service nel frontend
- oggi il provisioning tenant esiste gia lato backend tramite `/platform/tenants`, ma e protetto da platform API key e non e esponibile direttamente al browser
- `provision_tenant(...)` crea gia club, admin owner e subscription iniziale
- il modello `ProvisionTenantRequest` supporta gia `slug`, `public_name`, `notification_email`, `plan_code`, `trial_days`, `admin_email`, `admin_full_name`, `admin_password`
- il repository ha gia un concetto di trial e subscription tenant-aware
- il sistema bootstrap automaticamente `default-club` per retrocompatibilita
- il modello `Club` contiene gia campi utili per la scheda del club: `public_name`, `notification_email`, `support_email`, `support_phone`, `public_address`, `public_postal_code`, `public_city`, `timezone`, `currency`
- il modello `Admin` oggi ha solo `email`, `full_name`, `password_hash`, `role`, `is_active`; il ruolo attuale e tecnico/RBAC, non va confuso con il ruolo del referente commerciale che compila il form
- il booking engine resta oggi single-court e non va rifondato in questa iniziativa
- la UI attuale ha gia pattern condivisi da riusare: `PageBrandBar`, `dark.png`, `surface-card`, `product-hero-panel`, `btn-primary`, `btn-secondary`, `field-label`, `text-input`, `selection-card`

## Decisione architetturale non negoziabile

Non usare `/platform/tenants` come endpoint pubblico chiamato dal frontend.

L'architettura corretta e:

- nuovo funnel pubblico di onboarding club
- nuova persistenza di pre-provisioning per una richiesta di registrazione club
- verifiche email/OTP completate prima del provisioning definitivo
- provisioning del tenant solo lato backend, riusando internamente `provision_tenant(...)`
- nessuna esposizione della platform API key al client

## Decisioni UX non negoziabili

- non sovraccaricare `/admin/login` con il flusso di registrazione: la login admin resta accesso riservato
- la registrazione club deve vivere su una route pubblica dedicata, coerente con l'app
- la UI deve riusare il visual language attuale del prodotto, senza introdurre un microsito separato o un design estraneo
- il funnel deve essere lineare e leggibile, con un solo obiettivo per step
- non chiedere password nel primo form se questo non e strettamente necessario
- preferisci un set-password successivo via email, riusando l'infrastruttura gia esistente di reset password admin

## Route target consigliate

Usa una struttura minima e coerente con l'app attuale. La proposta preferita e:

- `/clubs/register`
- `/clubs/register/verify-email`
- `/clubs/register/success`

Regole:

- `/clubs/register` e la pagina principale del form
- `/clubs/register/verify-email?token=...` gestisce il click da email e l'avvio del passaggio OTP
- `/clubs/register/success` mostra trial, tariffa assegnata, URL utili e CTA finali
- non introdurre una route `/signup` generica se non strettamente motivata

## Campi obbligatori del form club

La pagina di registrazione deve raccogliere almeno questi dati:

### Referente / owner iniziale

- Nome
- Cognome
- Email
- Telefono
- Ruolo di chi inserisce i dati

Per il ruolo usa una lista controllata, pragmatica e non tecnica:

- Titolare
- Direttore
- Club manager
- Reception o segreteria
- Maestro o coach
- Altro

Nota importante:

- questo campo non e il `role` RBAC del modello `Admin`
- trattalo come ruolo del referente commerciale o operativo

### Dati club

- Nome del club
- Nazione del club, default `Italia`
- Citta
- Indirizzo
- CAP
- Numero di campi
- Sport, menu a tendina con etichette finali:
  - `Padel + Tennis`
  - `Padel`
  - `Padel + Pickleball`

### Consensi

- checkbox privacy obbligatoria
- checkbox cookie obbligatoria

Regola di prodotto:

- in questa fase implementa due consensi espliciti nel form
- non costruire una CMP completa o un cookie banner enterprise se il repository non la possiede gia

## Requisiti UX del form

### Telefono

Il telefono deve essere composto da:

- select nazione con prefisso internazionale
- valore di default `Italia` con `+39`
- input numero separato o unificato, ma validato in modo coerente

Vincolo tecnico:

- non introdurre librerie pesanti per l'international phone input se non strettamente necessarie
- preferisci una piccola lista interna di nazioni/prefissi o un dataset statico minimo e manutenibile

### Pricing visibile

La pagina deve rendere visibile il modello tariffario in modo chiaro prima dell'invio:

- fino a 2 campi: `29,00 EUR / mese`
- fino a 4 campi: `45,00 EUR / mese`
- fino a 7 campi: `69,00 EUR / mese`
- 8+ campi: `109,00 EUR / mese`
- prova gratuita: `30 giorni`

La tariffa deve essere derivata da `numero di campi`, non scelta manualmente dall'utente come piano scollegato.

### Gerarchia del funnel

Progetta il flusso cosi:

1. Hero chiara: crea il tuo club su Matchinn
2. Form dati referente + dati club
3. Review leggera del piano derivato da numero campi
4. Invio richiesta
5. Email verification da link
6. OTP step per conferma del recapito telefonico dichiarato, con OTP inviato via email
7. Provisioning del tenant
8. Success state con prova gratuita attiva

## Chiarimento importante sulla verifica telefono

Il requisito richiesto e: telefono verificato tramite OTP inviato via email.

Questa scelta va implementata cosi:

- non introdurre SMS provider
- non spacciare questa verifica come prova di possesso della SIM
- trattala come conferma del recapito telefonico dichiarato da parte del proprietario dell'email verificata
- nel copy UI sii corretto: stai confermando il numero comunicato, non certificando il possesso telefonico tramite SMS

## Decisione consigliata per la password admin

L'utente non ha chiesto una password nel form. Mantieni il funnel piu corto possibile.

Architettura consigliata:

- il form pubblico non chiede password
- dopo il provisioning, il backend genera una password temporanea casuale server-side solo per soddisfare `provision_tenant(...)`
- subito dopo, il sistema invia all'email del referente un link di set-password/reset-password riusando l'infrastruttura esistente dell'admin reset
- la login admin resta invariata

Questa e la soluzione preferita perche:

- riduce attrito nel form iniziale
- riusa superfici gia esistenti
- non richiede un nuovo modello auth admin piu complesso

## Mapping dati obbligatorio

Devi esplicitare nel prompt e poi rispettare in implementazione dove va ogni dato.

### Da referenza owner a dominio esistente

- `Nome + Cognome` -> `Admin.full_name` oppure campi staging separati prima del provisioning
- `Email` -> `admin_email` del provisioning e `notification_email` iniziale del club, salvo scelta migliore coerente e minima
- `Telefono` -> `support_phone` iniziale del club oppure campo staging e poi mapping sul club alla provision finale
- `Ruolo referente` -> non in `Admin.role`; salva in una superficie dedicata al contatto o nel record di onboarding

### Da dati club a modello Club

- `Nome del club` -> `Club.public_name`
- `Citta` -> `Club.public_city`
- `Indirizzo` -> `Club.public_address`
- `CAP` -> `Club.public_postal_code`

### Dati oggi non modellati in modo esplicito

Verifica prima se nel modello reale esistono gia. Se mancano, fai la patch minima coerente.

Campi potenzialmente da introdurre in modo first-class o tramite staging + tenant settings, con scelta motivata:

- nazione del club
- numero di campi
- sport del club
- ruolo del referente
- consensi privacy/cookie con timestamp e versione

Preferenza architetturale:

- `numero di campi` e `sport` sono attributi di dominio del club e commercialmente rilevanti; non nasconderli in JSON anonimi senza motivo forte
- il ruolo del referente e i dettagli di verifica stanno meglio in un record di onboarding o contatto, non nel `Club` puro se non servono al dominio runtime

## Decisione importante sullo slug

Non chiedere lo slug nel form pubblico.

Architettura corretta:

- l'utente inserisce solo `Nome del club`
- lo slug viene derivato lato backend dal nome
- in caso di collisione lo slug viene reso univoco server-side con strategia deterministica, leggibile e verificabile

## Decisione importante sul numero di campi

Il numero di campi non deve cambiare da solo il motore booking corrente.

In questa iniziativa:

- serve per pricing e profiling iniziale del tenant
- puo alimentare la scheda club o la configurazione iniziale
- non deve riscrivere il booking engine single-court gia esistente
- non auto-creare 2, 4, 7 o 8+ courts senza richiesta esplicita e implementazione dedicata

## Architettura backend target

### 1. Pre-provisioning separato

Introduci una nuova entita di staging, ad esempio `ClubOnboardingRequest` o naming equivalente migliore, per evitare di creare tenant reali prima delle verifiche.

Questa entita deve contenere almeno:

- dati referente
- dati club
- numero campi
- sport
- piano derivato
- stato del workflow
- email verification token hash
- email verification expires_at
- email_verified_at
- otp hash
- otp expires_at
- otp attempt_count
- otp last_sent_at
- phone_verified_at
- privacy_accepted_at
- cookie_accepted_at
- eventuale versione policy/copy accettata
- provisioned_club_id opzionale a fine flusso
- created_at / updated_at

### 2. Stato del workflow

Usa uno state machine chiaro e minimale, ad esempio:

- `PENDING_EMAIL_VERIFICATION`
- `EMAIL_VERIFIED_PENDING_PHONE_OTP`
- `PHONE_VERIFIED_READY_TO_PROVISION`
- `PROVISIONED`
- `EXPIRED`
- `CANCELLED`

### 3. Endpoint pubblici nuovi

Preferisci un router pubblico dedicato, separato dal control plane e separato dalla login admin.

Esempi minimi coerenti:

- `POST /public/club-onboarding`
- `POST /public/club-onboarding/verify-email`
- `POST /public/club-onboarding/send-phone-otp`
- `POST /public/club-onboarding/verify-phone-otp`
- `GET /public/club-onboarding/{request_id}` opzionale solo se davvero utile

Vincoli:

- non esporre `/platform/tenants`
- non duplicare il provisioning se puoi chiamare `provision_tenant(...)` internamente a valle delle verifiche
- usa hashing dei token, expiry e rate-limit/attempt-limit coerenti con i pattern gia presenti nel repo

### 4. Email verification

La verifica email deve funzionare con:

- token signed o random ad alta entropia
- token salvato hashed, non in chiaro
- click da link email che porta al frontend o a una route backend di redirect coerente
- attivazione OTP step solo dopo email verificata

### 5. OTP via email

Per l'OTP riusa i pattern gia presenti nel prodotto quando possibile:

- expiry breve
- resend cooldown
- attempt limit
- invalidazione del challenge precedente quando ne nasce uno nuovo

### 6. Provisioning finale

Solo dopo doppia verifica:

- calcola il `plan_code` dalla fascia `numero di campi`
- usa `trial_days=30`
- genera password temporanea server-side
- chiama internamente `provision_tenant(...)`
- collega il `club_id` creato al record onboarding
- invia mail finale con link di set/reset password admin

## Strategia pricing obbligatoria

Mappa il numero di campi a piani mensili.

Se i plan code non esistono ancora, introduci la patch minima coerente con il layer billing attuale.

Proposta di naming semplice e leggibile:

- `club_upto_2`
- `club_upto_4`
- `club_upto_7`
- `club_8_plus`

Prezzi attesi:

- `club_upto_2` -> `29,00 EUR / mese`
- `club_upto_4` -> `45,00 EUR / mese`
- `club_upto_7` -> `69,00 EUR / mese`
- `club_8_plus` -> `109,00 EUR / mese`

Regole:

- billing interval mensile
- trial 30 giorni
- niente piano scelto manualmente in conflitto con `numero di campi`
- non introdurre un secondo sistema di pricing parallelo al layer `Plan` e `ClubSubscription`

## Architettura frontend target

### Pagina principale `/clubs/register`

La pagina deve riusare il design system attuale:

- `PageBrandBar`
- `dark.png`
- `surface-card`
- `product-hero-panel`
- `btn-primary` / `btn-secondary`
- `field-label` / `text-input`
- eventuali `selection-card` per sport o riepilogo piano

La pagina deve contenere:

- hero chiara, non marketing vaga
- spiegazione breve del trial e del piano derivato da numero campi
- form unico ben sezionato
- riepilogo tariffa dinamico e leggibile
- check privacy e cookie ben visibili
- stato invio/errore/success chiari

### Pagina `/clubs/register/verify-email`

Questa pagina deve:

- consumare il token dalla mail
- verificare il token via backend
- mostrare esito chiaro
- se verifica ok, attivare o spiegare il passaggio OTP

### Pagina `/clubs/register/success`

Questa pagina deve mostrare:

- club creato correttamente
- prova gratuita di 30 giorni attiva
- tariffa assegnata in base ai campi
- CTA per impostare la password admin o controllare la mail
- CTA secondaria verso login admin tenant-aware
- riferimenti utili del club appena creato, senza esporre dettagli tecnici inutili

## Coerenza con l'app attuale

Non chiedere o implementare un design completamente nuovo.

La registrazione club deve sembrare parte della stessa app di:

- admin login
- Play access
- booking pubblico

Mantieni quindi:

- top header con `dark.png`
- bottoni e card del design system esistente
- linguaggio semplice, diretto, non corporate generico
- funnel mobile-first

## Vincoli non negoziabili

Non modificare la business logic esistente di:

- booking pubblico
- availability
- checkout booking
- payment status
- cancellation
- admin auth gia funzionante
- Play e community
- tenant resolution gia approvata
- fallback `default-club`

Puoi introdurre solo la nuova logica minima necessaria per il self-onboarding club, il provisioning e la selezione del piano.

## Cose da non fare

- non esporre la platform API key al frontend
- non trasformare `AdminLoginPage` in un signup ibrido confuso
- non chiedere lo slug nel form pubblico
- non creare automaticamente tutti i campi sportivi dal `numero di campi`
- non inventare un nuovo sistema auth admin se il reset/set password esistente e sufficiente
- non introdurre SMS o provider esterni non gia necessari
- non introdurre dipendenze frontend pesanti per la sola select del prefisso telefonico
- non usare JSON generici per dati che sono chiaramente first-class nel dominio del tenant senza motivazione tecnica esplicita

## Fasi obbligatorie del lavoro

### Fase 1 — Gap analysis e architettura

Obiettivo:

- verificare il repository reale
- definire i modelli, le route, i contratti API e la strategia di provisioning

Output obbligatorio:

- architettura target
- route map nuove
- mapping dati completo
- decisione motivata su dove salvare campi onboarding vs campi club

File stato obbligatorio:

- `STATO_CLUB_FASE_1.md`

### Fase 2 — Backend onboarding e verifiche

Obiettivo:

- introdurre persistenza staging, email verification, OTP e provisioning finale

Output obbligatorio:

- patch backend minima
- eventuale migrazione Alembic
- test backend mirati

File stato obbligatorio:

- `STATO_CLUB_FASE_2.md`

### Fase 3 — Frontend registrazione club

Obiettivo:

- costruire le pagine pubbliche del funnel club-first coerenti con la UI attuale

Output obbligatorio:

- nuove route frontend
- nuove pagine/componenti minimi
- test frontend pertinenti

File stato obbligatorio:

- `STATO_CLUB_FASE_3.md`

### Fase 4 — Pricing e trial integration

Obiettivo:

- collegare `numero di campi` ai piani reali, al trial e al provisioning finale senza rompere il billing layer esistente

Output obbligatorio:

- plan mapping
- eventuali seed o bootstrap plan
- test su provisioning e subscription

File stato obbligatorio:

- `STATO_CLUB_FASE_4.md`

### Fase 5 — Verifica finale e rifinitura UX

Obiettivo:

- validare il funnel end-to-end e chiudere i gap UI/architetturali

Output obbligatorio:

- build/test reali
- rischi residui
- file stato finale

File stato obbligatorio:

- `STATO_CLUB_FASE_5.md`

## Formato di output obbligatorio per ogni fase

Usa sempre questo ordine:

## 1. Prerequisiti verificati
- PASS / FAIL reale

## 2. Mappa del repository rilevante
- file reali trovati e superfici toccate

## 3. Gap analysis della fase
- cosa manca oggi rispetto all'obiettivo

## 4. File coinvolti
- file creati o modificati

## 5. Implementazione
- codice completo dei file necessari

## 6. Migrazioni e backfill
- nome migrazione
- strategia dati legacy
- impatto su `default-club` e tenant esistenti

## 7. Test aggiunti o modificati
- codice completo dei test

## 8. Verifica di fine fase
- controlli eseguiti
- esito PASS / FAIL / NOT APPLICABLE
- criticita residue
- gate finale:
  - `FASE VALIDATA - si puo procedere`
  - `FASE NON VALIDATA - non procedere`

## 9. File stato della fase
- stato compatto per la fase successiva

## Controllo qualita finale obbligatorio

Alla fine di ogni fase e soprattutto della fase finale, verifica esplicitamente che:

- il flusso club registration non rompa booking, play, admin o tenant resolution esistenti
- il provisioning resti server-side e protetto
- il pricing derivi davvero da `numero di campi`
- il trial sia davvero di 30 giorni
- la login admin resti riservata e separata dal signup
- il numero di campi non venga scambiato per provisioning automatico dei court runtime
- i consensi e le verifiche siano persistiti in modo auditabile
- l'output sia direttamente implementabile, non teorico
- eventuali ambiguita residue siano segnalate chiaramente

Se trovi un conflitto con il codice reale, non inventare scorciatoie: segnala il conflitto e proponi la patch minima coerente con il repository.