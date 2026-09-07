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
