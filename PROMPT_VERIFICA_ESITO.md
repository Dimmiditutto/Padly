# VERIFICA HOME MATCHINN, BOOKING PUBBLICO TENANT-AWARE E CAPARRA PER-CLUB

## 1. Esito sintetico generale

FAIL PARZIALE

L'integrazione recente e ampia e nel complesso ben costruita: routing frontend, tenant resolution pubblica, settings admin, snapshot di booking, home Matchinn, discovery e Play risultano coerenti tra loro e supportati da validazioni reali.

Verifiche eseguite durante questa analisi:

- frontend test completo: npm run test:run -> PASS, 17 file test, 136 test passati
- frontend build: npm run build -> PASS
- backend suite estesa: .venv/Scripts/python.exe -m pytest tests/test_booking_api.py tests/test_tenant_backend_context.py tests/test_admin_and_recurring.py tests/test_payment_flows.py tests/test_play_phase3.py tests/test_play_phase6_public_directory.py tests/test_play_phase7_public_discovery.py -q -> PASS, 132 test passati

Il codice quindi non e rotto in senso generale. Tuttavia la verifica tecnica rigorosa ha evidenziato una criticita bloccante e una criticita significativa non intercettate dalla suite verde:

- il layer pagamenti continua a validare importo e valuta con assunzioni legacy, quindi il nuovo modello di caparra per-club non e rispettato end-to-end nel checkout e nelle conferme pagamento
- la compatibilita legacy delle sessioni Play nel browser non e completa: navigare un altro club puo cancellare il vecchio cookie globale ancora valido

Di conseguenza il progetto non e ancora pronto per il rilascio della nuova policy caparra per-club senza fix mirati.

## 2. Verifica per area

### Coerenza complessiva del codice

Esito: PASS CON RISERVE

Problemi trovati:

- backend, frontend, API e schema dati sono allineati sul nuovo perimetro: home Matchinn su /, booking pubblico esplicito su /booking, caparra pubblica per club, flag Play di ereditarieta, tenant obbligatorio sui flussi pubblici di booking quando esistono piu club attivi
- i modelli e le migrazioni sono coerenti con l'obiettivo di congelare i termini di caparra su ogni booking tramite deposit_amount, deposit_currency e deposit_policy_snapshot
- resta una divergenza importante tra il nuovo source of truth della caparra nel service layer booking e il service layer pagamenti, che continua a ragionare con formula e valuta legacy

Gravita del problema:

- critica sul layer pagamenti

Impatto reale:

- il progetto appare coerente e testato, ma il flusso checkout/pagamento non e ancora pienamente compatibile con la nuova business logic per-club

### Coerenza tra file modificati

Esito: FAIL PARZIALE

Problemi trovati:

- backend/app/services/booking_service.py risolve correttamente la caparra dal club, salva snapshot e valuta sul booking, e backend/app/services/settings_service.py espone coerentemente la nuova policy nei settings tenant-scoped
- backend/app/api/routers/public.py, backend/app/schemas/public.py, frontend/src/types.ts e frontend/src/pages/PublicBookingPage.tsx sono coerenti tra loro sul nuovo flusso no-deposit vs deposit-required
- backend/app/services/payment_service.py pero continua a ricalcolare l'importo atteso tramite calculate_deposit e a forzare EUR nei gateway Stripe/PayPal, rompendo la coerenza con i nuovi campi deposit_currency e deposit_policy_snapshot
- backend/app/api/routers/play.py e backend/app/api/deps.py introducono correttamente i cookie club-specifici, ma la logica di cleanup puo eliminare anche il cookie globale legacy mentre l'utente sta semplicemente consultando un altro club

Gravita del problema:

- critica sulla coerenza booking_service <-> payment_service
- media sulla compatibilita legacy dei cookie Play

Impatto reale:

- i file modificati sono per lo piu coerenti, ma due comportamenti chiave restano disallineati dal nuovo contratto di dominio

### Conflitti o blocchi introdotti dai file modificati

Esito: FAIL PARZIALE

Problemi trovati:

- il checkout pubblico e i path di conferma pagamento possono andare in conflitto con booking validi quando la caparra del club non coincide con la vecchia formula 20/10/30
- il supporto ai cookie club-specifici non spezza i nuovi flussi, ma puo degradare l'esperienza di chi arriva ancora da sessioni legacy non ancora migrate al nuovo doppio-cookie
- non emergono invece conflitti di build, tipi, import/export, routing o serializzazione tra frontend e backend sulle superfici Matchinn, booking pubblico e settings admin

Gravita del problema:

- critica sul checkout con caparra custom
- media sulla sessione legacy Play

Impatto reale:

- il rilascio della caparra per-club non e ancora sicuro finche il pagamento non usa lo stesso contratto persistito sul booking

### Criticita del progetto nel suo insieme

Esito: PASS CON RISERVE

Problemi trovati:

- il perimetro recente e ben isolato: home Matchinn, discovery pubblica, route booking tenant-aware e settings admin non mostrano regressioni evidenti nelle suite complete rieseguite
- la criticita principale e nascosta da un gap di copertura: le suite verdi non esercitano il path pagamento pubblico dopo avere cambiato davvero la policy di caparra del club, quindi il bug di coerenza col payment layer non emerge automaticamente
- la compatibilita backward con il cookie Play legacy e stata pensata, ma non e coperta da test dedicati sul caso cross-club che oggi resta fragile

Gravita del problema:

- media sul gap di regressione test

Impatto reale:

- l'architettura regge, ma manca ancora la prova automatica sui due punti che oggi sono piu esposti a regressione reale

### Rispetto della logica di business

Esito: FAIL PARZIALE

Problemi trovati:

- la business logic chiesta per il booking pubblico tenant-aware e quasi tutta rispettata: la root non e piu booking-first, il booking pubblico non parte piu senza contesto club in scenario multi-club, il club puo disattivare la caparra pubblica, il Play puo ereditare la stessa caparra con flag dedicato, le prenotazioni esistenti non vengono ricalcolate quando cambiano le regole
- la parte non rispettata correttamente e l'ultimo miglio dei pagamenti: il booking memorizza la policy per-club ma il checkout continua a validare come se la caparra fosse ancora globale e sempre in EUR
- il fallback legacy delle sessioni community nel browser non e completamente preservato quando l'utente attraversa club diversi

Gravita del problema:

- critica sulla logica pagamento vs caparra per-club
- media sulla continuita del rientro community legacy

Impatto reale:

- il comportamento applicativo e corretto fino alla creazione del booking e alla UX, ma non e ancora affidabile nel punto piu sensibile: la monetizzazione del deposito configurato dal club

## 3. Elenco criticita

### 1. Il layer pagamenti non usa il nuovo contratto di caparra per-club

Descrizione tecnica:

- backend/app/services/booking_service.py ricava la valuta del club e i termini della caparra dal club corrente, poi salva deposit_amount, deposit_currency e deposit_policy_snapshot sul booking
- backend/app/services/payment_service.py continua invece a:
  - ricalcolare l'importo atteso con la formula legacy calculate_deposit
  - validare la currency come EUR fissa
  - creare checkout Stripe/PayPal con EUR hardcoded

Perche e un problema reale:

- se il club imposta una caparra diversa dalla formula legacy 20/10/30, il booking viene creato con valori corretti ma il checkout e la conferma pagamento restano ancorati alla logica vecchia
- se un club usa una currency diversa da EUR, il booking memorizza una valuta ma il layer pagamenti continua a lavorare come se EUR fosse sempre l'unica valuta valida

Dove si manifesta:

- backend/app/services/booking_service.py linee 146, 151, 659, 660, 721, 722
- backend/app/models/__init__.py linee 632, 633
- backend/app/services/payment_service.py linee 87, 177, 222, 402, 410, 425, 495, 726

Gravita: critica

Blocca il rilascio: si

### 2. Il fallback legacy delle sessioni Play puo essere cancellato navigando un altro club

Descrizione tecnica:

- il nuovo supporto ai cookie club-specifici e corretto e utile, ma get_current_player_optional usa anche il cookie legacy globale come fallback
- nei router Play, quando current_player e None ma esiste qualunque player session cookie, la logica di cleanup cancella sia il cookie del club corrente sia il cookie legacy globale
- questo significa che un utente ancora sostenuto solo dal vecchio cookie globale puo perdere la sessione legacy semplicemente aprendo il Play di un club diverso da quello a cui il cookie appartiene

Perche e un problema reale:

- la home Matchinn dichiara esplicitamente il supporto parallelo tra cookie legacy e cookie club-specifici
- con la logica attuale, quel fallback puo essere interrotto in modo silenzioso durante una navigazione cross-club, costringendo a un nuovo OTP anche se la sessione legacy era ancora valida

Dove si manifesta:

- backend/app/api/deps.py linea 125
- backend/app/api/routers/play.py linee 72, 77, 80, 100, 101, 245, 246, 261, 262, 277, 278
- backend/app/api/routers/public.py linee 181, 191

Gravita: media

Blocca il rilascio: no

### 3. La regressione sul checkout con caparra custom non e coperta da test dedicati

Descrizione tecnica:

- la suite completa backend e frontend passa, ma i test che coprono checkout pubblico e payment flows usano solo il comportamento legacy di importo atteso
- non esiste una prova automatica che aggiorni la policy pubblica del club e poi eserciti davvero:
  - POST /api/public/bookings/{id}/checkout
  - mock complete / webhook Stripe
  - return / webhook PayPal

Perche e un problema reale:

- e la ragione per cui la divergenza tra booking_service e payment_service e arrivata a suite verde
- senza quel test il bug puo rientrare facilmente anche dopo il fix

Dove si manifesta:

- backend/tests/test_booking_api.py
- backend/tests/test_payment_flows.py

Gravita: media

Blocca il rilascio: no, ma il test va aggiunto insieme al fix bloccante

## 4. Prioritizzazione finale

### Da correggere prima del rilascio

- allineare completamente backend/app/services/payment_service.py al nuovo contratto di booking persistito, usando deposit_amount e deposit_currency del booking come source of truth per checkout, conferma pagamento e refund
- eliminare ogni ricalcolo legacy con calculate_deposit dal path pagamento pubblico/admin compatibile con la nuova caparra per-club
- aggiungere test backend che cambino davvero la policy pubblica del club e coprano checkout, mock complete e webhooks/return con importi non legacy

### Da correggere prima della beta pubblica

- rendere il cleanup delle sessioni Play backward-safe, evitando di cancellare il cookie globale legacy solo perche il giocatore sta visitando un club diverso
- aggiungere un test dedicato sul caso di cookie legacy valido e navigazione cross-club

### Miglioramenti differibili

- rendere piu esplicito il contratto API di creazione booking no-deposit evitando dettagli di checkout non utili quando il booking e gia confermato
- valutare se esporre deposit_currency e deposit_policy_snapshot anche nei payload admin di dettaglio se serve audit operativo lato supporto

## 5. Verdetto finale

Il codice e quasi pronto ma richiede fix mirati prima del rilascio.

La parte architetturale e di UX e buona: home Matchinn, tenant-aware public booking, settings admin, snapshot della caparra e integrazione Play sono coerenti e supportati da test ampi. Il punto che manca per chiudere davvero la feature e il layer pagamenti, che oggi non usa ancora lo stesso contratto persistito sul booking. Finche quel disallineamento resta aperto, la caparra per-club non e affidabile in produzione.

## 6. Prompt operativo per i fix

Agisci come un Senior Software Architect, Senior Backend Engineer FastAPI/SQLAlchemy e QA tecnico rigoroso.

Devi correggere solo le criticita reali emerse dalla verifica di:

- home Matchinn su /
- booking pubblico esplicito su /booking
- caparra pubblica per-club
- snapshot immutabile della caparra su Booking
- flag Play che eredita la caparra pubblica del club
- cookie Play club-specifici con fallback legacy

Non fare refactor ampi. Non toccare logica non coinvolta di ranking, discovery, notifiche, recurring, reminder o billing SaaS. Mantieni patch minime e locali.

### Contesto reale gia integrato da preservare

Queste integrazioni esistono gia e non vanno rifatte:

- backend/app/api/deps.py introduce PUBLIC_TENANT_REQUIRED_DETAIL e il tenant obbligatorio sui flussi pubblici di booking quando esistono piu club attivi
- backend/app/services/settings_service.py introduce public_booking_deposit_policy e play_community_use_public_deposit
- backend/app/services/booking_service.py salva deposit_amount, deposit_currency e deposit_policy_snapshot sui booking
- backend/alembic/versions/20260429_0016_public_booking_deposit_policy_snapshot.py aggiunge i campi nuovi su bookings
- backend/app/services/play_service.py puo ereditare la caparra pubblica del club e supporta cookie club-specifici
- backend/app/api/routers/public.py espone la home Matchinn e il booking pubblico tenant-aware
- frontend/src/App.tsx usa / come MatchinnHomePage e /booking come PublicBookingPage
- frontend/src/pages/PublicBookingPage.tsx gestisce i casi deposit-required e no-deposit
- frontend/src/pages/AdminDashboardPage.tsx gestisce la policy caparra pubblica e il flag Play di ereditarieta
- le validazioni ampie sono gia verdi: frontend completo 136 test, backend esteso 132 test, frontend build PASS

### Obiettivi obbligatori, in ordine di priorita

1. Allinea il layer pagamenti al contratto persistito sul booking.

   In backend/app/services/payment_service.py elimina il vincolo legacy che ricalcola l'importo atteso tramite calculate_deposit per booking pubblici e admin.

   Regole minime da rispettare:

   - il source of truth per l'importo atteso deve diventare booking.deposit_amount
   - il source of truth per la valuta deve diventare booking.deposit_currency
   - StripeGateway.create_checkout deve usare la valuta del booking, non EUR hardcoded
   - PayPalGateway.create_checkout e refund devono usare la valuta del booking, non EUR hardcoded
   - _assert_payment_amount deve validare contro booking.deposit_currency
   - _ensure_booking_payment deve salvare la stessa currency del booking
   - mantieni il comportamento gia corretto per i booking Play, ma evita branching inutili se puo bastare un unico criterio robusto basato sul booking stesso

2. Non rompere no-deposit e snapshot immutabile.

   Verifica che i fix al payment layer non cambino questi comportamenti gia corretti:

   - booking pubblico senza caparra -> status CONFIRMED senza checkout
   - booking pubblico con caparra -> status PENDING_PAYMENT e checkout attivabile
   - booking admin e recurring gia esistenti non devono essere ricalcolati retroattivamente
   - Play community con use_public_deposit deve continuare a ereditare importo e policy snapshot dal booking pubblico del club

3. Rendi backward-safe il cleanup dei cookie Play legacy.

   In backend/app/api/routers/play.py evita di cancellare il cookie globale legacy solo perche l'utente ha aperto il Play di un altro club.

   Regole minime da rispettare:

   - se manca current_player per il club corrente, puoi pulire il cookie club-specifico di quel club se risulta invalido o inutile
   - non cancellare automaticamente il cookie legacy globale se non hai prova che sia invalido per il club cui appartiene davvero
   - mantieni intatta la strategia nuova con doppio-cookie e la lettura della home Matchinn basata su cookie club-specifici piu fallback legacy

4. Aggiungi solo i test strettamente necessari a blindare i bug emersi.

   Aggiungi o aggiorna test backend mirati per coprire almeno:

   - checkout pubblico con policy caparra custom del club, ad esempio 18 base + 9 extra
   - conferma pagamento mock o webhook con caparra custom non legacy
   - currency coerente tra booking e payment record, oppure una guardia esplicita se la piattaforma decide di limitarsi a EUR in modo dichiarato
   - navigazione cross-club che non deve cancellare una sessione legacy valida di un altro club

### Vincoli non negoziabili

- niente refactor ampi
- niente riscrittura dei router pubblici o Play oltre il minimo necessario
- niente cambi di UX nel frontend se non imposti dai fix backend strettamente necessari
- non toccare MatchinnHomePage, ClubDirectoryPage o discovery se non emerge un blocco diretto dai fix sopra
- non introdurre nuovi modelli o nuove API se il fix puo stare nei servizi esistenti

### Verifica finale obbligatoria

Prima di chiudere:

- esegui i test backend mirati sui payment flows e sul caso cross-club legacy cookie
- riesegui almeno npm run build se tocchi contratti condivisi o payload
- dichiara PASS o FAIL reale
- se resta un limite intenzionale sulla currency, dichiaralo esplicitamente e fallo rispettare in modo coerente a livello di dominio, non lasciarlo implicito nel gateway