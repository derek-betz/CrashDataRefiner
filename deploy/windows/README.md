# Windows Deployment Baseline

Use this folder for the `WEB-SVR03` deployment shape that mirrors `CostEstimateGenerator`.

## Expected layout

- App code: `C:\Program Files\CrashDataRefiner`
- Virtualenv: `C:\Program Files\CrashDataRefiner\.venv`
- Config: `C:\ProgramData\CrashDataRefiner\config\app.env`
- Logs: `C:\ProgramData\CrashDataRefiner\logs\`
- Outputs: `C:\ProgramData\CrashDataRefiner\outputs\web_runs\`
- Preview artifacts: `C:\ProgramData\CrashDataRefiner\outputs\preview\`

## Files

- `crash-data-refiner.env.example`: baseline environment file for `WEB-SVR03`
- `web-svr03.app.env`: proposed runtime values for `WEB-SVR03`
- `run-crash-data-refiner.ps1`: starts the hosted web app on loopback
- `register-crash-data-refiner-task.ps1`: registers the supported startup path on `WEB-SVR03`
- `WEB-SVR03-CHECKLIST.md`: copy/paste bring-up and validation steps for the server

## Serving model

- App server: `waitress` on `127.0.0.1:8081`
- Final internal URL: `https://crashrefiner.hanson-inc.com`
- Writable runtime data: `C:\ProgramData\CrashDataRefiner`

## Bring-up order

1. Copy the repo to `C:\Program Files\CrashDataRefiner`.
2. Build the virtualenv and install dependencies.
3. Create the runtime directories under `C:\ProgramData\CrashDataRefiner`.
4. Copy `web-svr03.app.env` to the real config path as `app.env`.
5. Run `run-crash-data-refiner.ps1` manually on the server for the localhost proof.
6. Validate `http://127.0.0.1:8081/`.
7. Add the web-server binding for `crashrefiner.hanson-inc.com` on `WEB-SVR03`.
8. Register or update the scheduled task and validate the real URL.
