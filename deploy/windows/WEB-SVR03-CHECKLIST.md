# CrashDataRefiner on WEB-SVR03

Use this checklist to stand up `CrashDataRefiner` at `https://crashrefiner.hanson-inc.com`.

## 1. Copy the app to the server

Place the repo at:

- `C:\Program Files\CrashDataRefiner`

## 2. Create the runtime folders

Run this in an elevated PowerShell session:

```powershell
New-Item -ItemType Directory -Force -Path `
  'C:\Program Files\CrashDataRefiner', `
  'C:\ProgramData\CrashDataRefiner\config', `
  'C:\ProgramData\CrashDataRefiner\logs', `
  'C:\ProgramData\CrashDataRefiner\outputs\web_runs', `
  'C:\ProgramData\CrashDataRefiner\outputs\preview'
```

## 3. Build the virtualenv and install the app

```powershell
Set-Location 'C:\Program Files\CrashDataRefiner'
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install .
```

## 4. Install the WEB-SVR03 app env file

Copy the checked-in server values to the live config path:

```powershell
Copy-Item `
  'C:\Program Files\CrashDataRefiner\deploy\windows\web-svr03.app.env' `
  'C:\ProgramData\CrashDataRefiner\config\app.env' `
  -Force
```

The current values are:

```env
APP_ENV=production
CDR_HOST=127.0.0.1
CDR_PORT=8081
CDR_THREADS=4
CDR_OUTPUT_ROOT=C:\ProgramData\CrashDataRefiner\outputs\web_runs
CDR_PREVIEW_ROOT=C:\ProgramData\CrashDataRefiner\outputs\preview
CDR_MAX_UPLOAD_BYTES=209715200
```

## 5. Manual localhost proof

```powershell
Set-Location 'C:\Program Files\CrashDataRefiner'
powershell -NoProfile -ExecutionPolicy Bypass -File `
  '.\deploy\windows\run-crash-data-refiner.ps1' `
  -AppRoot 'C:\Program Files\CrashDataRefiner' `
  -EnvFile 'C:\ProgramData\CrashDataRefiner\config\app.env'
```

Leave that PowerShell window running and validate from a second window:

```powershell
Invoke-WebRequest 'http://127.0.0.1:8081/'
Invoke-WebRequest 'http://127.0.0.1:8081/api/health'
```

## 6. Register startup

After the localhost proof passes:

```powershell
Set-Location 'C:\Program Files\CrashDataRefiner\deploy\windows'
powershell -NoProfile -ExecutionPolicy Bypass -File `
  '.\register-crash-data-refiner-task.ps1' `
  -AppRoot 'C:\Program Files\CrashDataRefiner' `
  -EnvFile 'C:\ProgramData\CrashDataRefiner\config\app.env'
```

If IT wants a specific service account, rerun the same command with `-TaskUser` and `-TaskPassword`.

## 7. Final server-side validation

- Confirm the scheduled task starts cleanly after a reboot or manual run.
- Confirm the app log is being written to `C:\ProgramData\CrashDataRefiner\logs\crash-data-refiner.log`.
- Confirm the IIS or reverse-proxy binding for `crashrefiner.hanson-inc.com` points to `127.0.0.1:8081`.
- Validate `https://crashrefiner.hanson-inc.com`.
