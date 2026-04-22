# Comandi Test

Comandi principali da usare per validare il progetto in locale.

Nota pratica:

- backend: usare sempre il Python della virtualenv del repository
- esempi scritti per PowerShell su Windows

## 1. Backend mirato hardening operativo

Da usare quando tocchi rate limit, healthcheck, logging o scheduler.

```powershell
Set-Location 'D:/Padly/PadelBooking/backend'
D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_hardening_ops.py -q --tb=short
```

## 2. Backend mirato booking e admin

Da usare quando tocchi flussi prenotazioni, dashboard admin, recurring o API operative.

```powershell
Set-Location 'D:/Padly/PadelBooking/backend'
D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests/test_booking_api.py tests/test_admin_and_recurring.py -q -x --tb=short
```

## 3. Suite backend completa

Da usare quando tocchi middleware, dependency condivise, modelli, migrazioni o segnali operativi globali.

```powershell
Set-Location 'D:/Padly/PadelBooking/backend'
D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests -q -x --tb=short
```

## 4. Build frontend

Da usare ogni volta che tocchi componenti React, pagine, tipi TypeScript o servizi frontend.

```powershell
Set-Location 'D:/Padly/PadelBooking/frontend'
npm run build
```

## 5. Test frontend

Esegue la suite frontend una volta sola.

```powershell
Set-Location 'D:/Padly/PadelBooking/frontend'
npm run test:run
```

## 6. Test frontend in watch

Utile durante sviluppo locale su una singola pagina o componente.

```powershell
Set-Location 'D:/Padly/PadelBooking/frontend'
npm run test
```

## 7. Validazione completa consigliata prima di chiudere una fase

```powershell
Set-Location 'D:/Padly/PadelBooking/backend'
D:/Padly/PadelBooking/.venv/Scripts/python.exe -m pytest tests -q -x --tb=short

Set-Location 'D:/Padly/PadelBooking/frontend'
npm run build
npm run test:run
```

## 8. Riferimenti utili

- comandi base documentati anche in README.md
- checklist di rilascio in RELEASE_CHECKLIST.md
- runbook operativi in docs/operations/RUNBOOKS.md