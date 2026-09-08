# Accord backend

A small Flask + SQLite backend for the Accord frontend.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>.

The database is created automatically as `accord.db` and seeded with the demo role and profile on first run. Set `ACCORD_DATABASE` to use a different SQLite path.

## API

- `GET /api/health`
- `GET /api/roles`
- `POST /api/roles`
- `GET /api/profiles`
- `POST /api/profiles`
- `GET /api/matches`
- `POST /api/disputes`

Disputes currently use the placeholder split-the-difference rule shown in the UI. Replace that calculation in `create_dispute()` when connecting a real GenLayer Intelligent Contract.

## GenLayer contract example

The tiny contract is in `contracts/dispute_contract.py`. The public method accepts a role and two integer salary values. Amounts such as `100k` must be passed as `100000` in Python.

Run the same verdict logic locally:

```powershell
\.venv\Scripts\python.exe run_dispute.py --role "Senior Engineer" --offered 100000 --expected 120000
```

This prints a verdict at `110000 USDC/month`. The local runner verifies the contract logic; deploying and executing the `genlayer` contract requires GenLayer Studio, GLSim, or a configured GenLayer network.

## GenLayer relay

The optional Node relay is in `dispute_relay.js` and uses the configured Studio contract address. The address is safe to keep in source; the signing key is not.

Before using live disputes, revoke the private key that was shared in chat and create or use a funded Studio test account. In PowerShell, enter the replacement key directly in your local terminal:

```powershell
$env:ACCORD_SECRET_KEY = "replace-with-a-long-random-secret"
$env:ACCORD_REQUIRE_AUTH = "1"
$env:GENLAYER_PRIVATE_KEY = Read-Host "Enter the rotated GenLayer private key"
\.venv\Scripts\python.exe app.py
```

The app will be available at `http://127.0.0.1:5000`. The relay uses `GENLAYER_CONTRACT_ADDR` from the environment when present; otherwise it uses the configured contract address in `app.py`.
