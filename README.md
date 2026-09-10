# Accord

**Work agreements that settle their own arguments.**

Accord is a job marketplace where employers post roles, workers post profiles, and a plain skill-overlap algorithm shows both sides how well they match — before anyone signs anything. When a term like salary still doesn't line up, either party can raise a dispute. It's filed with [GenLayer's](https://genlayer.com) Internet Court, where a panel of AI validators reviews both positions and returns a ruling automatically.

🔗 **Live demo:** [accord-hazel.vercel.app](https://accord-hazel.vercel.app)

---

## Table of contents

- [Overview](#overview)
- [Features](#features)
- [How dispute resolution works](#how-dispute-resolution-works)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Environment variables](#environment-variables)
- [Usage walkthrough](#usage-walkthrough)
- [API reference](#api-reference)
- [Security notes](#security-notes)
- [Roadmap](#roadmap)

---

## Overview

Most hiring disagreements end the same way: a stalled email thread over a number nobody wants to be first to move on. Accord replaces that thread with two things:

1. **Transparent matching** — skill overlap is computed as shared skills ÷ total distinct skills across both lists, with no hidden weighting. You can read the same list the algorithm reads.
2. **Automated dispute resolution** — when pay, start date, or scope doesn't align, either side raises a dispute instead of negotiating manually. A panel of AI validators on GenLayer's network reviews both stated positions and rules on a settlement figure, without either party needing to agree first.

## Features

- **Role posting** — title, description, required skills, and monthly pay.
- **Candidate profiles** — name, résumé link, skills, and expected pay.
- **Skill-overlap matching** — computed server-side, sorted by strength of match.
- **Onchain dispute resolution** — disputes are settled by a real deployed GenLayer Intelligent Contract, not a locally-guessed number.
- **Accounts** — register/login with hashed passwords and session-based auth.

## How dispute resolution works

1. A dispute is filed with a role's offered pay, a candidate's expected pay, and a stated reason.
2. Accord's backend calls a small Node relay, which submits the dispute to a deployed [Intelligent Contract](contracts/dispute_contract.py) on GenLayer's network.
3. The contract prompts GenLayer's validators — a panel of independent LLMs — to review both figures and the stated reason, and return a fair settlement number.
4. Once a majority of validators agree, the verdict is finalized and stored.

If no GenLayer contract address or signing key is configured, Accord falls back to a simple placeholder rule (splitting the difference) so the rest of the app remains usable during local development.

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, SQLite |
| Frontend | HTML, CSS, vanilla JavaScript |
| Dispute contract | Python (GenLayer Intelligent Contract) |
| Dispute relay | Node.js, GenLayerJS |

## Project structure

```
Accord/
├── app.py                  # Flask backend — roles, profiles, matches, disputes, auth
├── index.html               # Single-page frontend
├── style.css                 # Styling
├── script.js                  # Frontend logic (forms, matching UI, dispute flow)
├── dispute_relay.js          # Node script that calls the deployed GenLayer contract
├── run_dispute.py            # CLI tool to test the verdict logic locally, no network needed
├── contracts/
│   └── dispute_contract.py   # The GenLayer Intelligent Contract itself
├── requirements.txt          # Python dependencies
├── package.json              # Node dependency (genlayer-js) for the relay
└── .env.example               # Template for local environment variables
```

## Getting started

### Prerequisites

- Python 3.10+
- Node.js (for the dispute relay)
- npm

### 1. Clone the repo

```bash
git clone https://github.com/0xAceBit/Accord.git
cd Accord
```

### 2. Set up the Python backend

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Set up the dispute relay

```bash
npm install
```

### 4. Configure environment variables

Copy the example file and fill in your own values:

```bash
cp .env.example .env
```

See [Environment variables](#environment-variables) below for what each one does.

### 5. Run it

```bash
python app.py
```

Open **http://127.0.0.1:5000**. The database is created automatically as `accord.db` and seeded with one example role and profile on first run.

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `ACCORD_SECRET_KEY` | Recommended | Signs session cookies. Set a long random value before deploying anywhere public. |
| `ACCORD_DATABASE` | No | Overrides the default SQLite path (`accord.db`). |
| `ACCORD_REQUIRE_AUTH` | No | Set to `1` to require login before posting roles/profiles. |
| `GENLAYER_CONTRACT_ADDR` | No | Address of the deployed `DisputeResolver` contract. Falls back to a default demo address if unset. |
| `GENLAYER_PRIVATE_KEY` | For live disputes | A GenLayer account private key used to sign dispute transactions. Without this, disputes fall back to a placeholder rule. |

> **Never commit a real private key.** Use a dedicated test account for `GENLAYER_PRIVATE_KEY`, and rotate it immediately if it's ever pasted somewhere outside your own `.env` file.

## Usage walkthrough

Here's a full round trip through Accord, end to end.

**1. Post a role**
An employer posts a Backend Engineer role at **2,000 USDC/month**, listing `node.js`, `postgresql`, and `rest-api` as required skills.

**2. Create a profile**
A candidate, Tunde, posts a profile listing the same three skills, with an expected rate of **1,600 USDC/month**.

**3. Check the match**
Accord's matching engine finds an 80% skill overlap between the two — a strong match — but flags that the pay figures differ.

**4. Raise a dispute**
Rather than negotiating by email, the employer clicks **Raise a dispute**, with the reason "salary mismatch — open to adjusting for experience level."

**5. GenLayer rules on it**
The dispute is filed with GenLayer's Internet Court. A panel of validators reviews both figures and the stated reason, and returns:

```
Case 5-2 · GenLayer Internet Court
Verdict returned
Settled at 1800 — the ruling is stored on the server.
```

**6. Both sides move forward**
Neither party set that number themselves — it's a ruling both can point to, and the role moves to an offer at 1,800 USDC/month.

## API reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/register` | Create an account |
| `POST` | `/api/login` | Log in |
| `POST` | `/api/logout` | Log out |
| `GET` | `/api/me` | Current session's user, if any |
| `GET` | `/api/roles` | List all posted roles |
| `POST` | `/api/roles` | Post a new role |
| `GET` | `/api/profiles` | List all posted profiles |
| `POST` | `/api/profiles` | Post a new profile |
| `GET` | `/api/matches` | List computed skill-overlap matches |
| `POST` | `/api/disputes` | Raise a dispute on a role/profile pair |

## Security notes

- Passwords are hashed with Werkzeug's `generate_password_hash` — never stored in plain text.
- `GENLAYER_PRIVATE_KEY` should always be a dedicated test/dev account key, supplied via environment variable — never hardcoded or committed.
- If a private key is ever exposed (chat log, screenshot, committed file), treat it as compromised and rotate it immediately.

## Roadmap

- [ ] Move dispute resolution off the request/response cycle into a background job, since validator consensus can take real time.
- [ ] Support keyed, multi-dispute contract storage (the current contract handles one dispute per call cleanly; a `TreeMap`-backed version for concurrent disputes is in progress).
- [ ] Expand dispute scope beyond salary to start date and role scope.
- [ ] Deploy the dispute contract to a persistent testnet ahead of production use, rather than Studionet alone.