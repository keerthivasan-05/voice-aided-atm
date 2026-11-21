# Voice-Aided ATM Simulator

A Python and SQLite ATM simulator with English and Tamil commands, an optional microphone interface, and keyboard-only PIN entry. It models authentication, withdrawals, transfers, and transaction history for demo accounts.

## Run locally

Use Python 3.9 or newer. Text mode uses the standard library.

```bash
python3 main.py --db ./interview-demo.sqlite3 --seed-demo --language en
python3 main.py --db ./interview-demo.sqlite3 --language ta
python3 -m unittest discover -s tests -v
```

| Demo account | PIN | Initial balance |
| --- | --- | --- |
| 1001 | 1234 | Rs 50,000 |
| 1002 | 5678 | Rs 15,000 |

Try `balance`, `withdraw 500`, `transfer 300 to 1002`, `history`, and `exit`. Confirm or cancel monetary actions with `yes` or `no`. In Tamil, try `இருப்பு`, `பணம் எடு 500`, `அனுப்பு 300 1002`, `ஆம்`, `இல்லை`, `பரிவர்த்தனை`, and `வெளியேறு`.

Use a new database path for a fresh demo. Seeding adds missing accounts and preserves balances. Three incorrect PIN attempts lock a demo account. Existing databases upgrade automatically on startup.

### Optional microphone mode

```bash
python3 -m pip install -r requirements-voice.txt
python3 main.py --db ./interview-demo.sqlite3 --mode voice --language en
```

Voice mode sends captured command audio to Google's speech recognition endpoint and requires working audio drivers and network access. Tamil speech output depends on the system voice configuration. Text mode is the verified demo path. Service rejection reasons currently appear in English.

## How it works

- [`main.py`](main.py) initializes the database and selects the input/output adapter. [`atm/io.py`](atm/io.py) provides console and microphone adapters.
- [`atm/controller.py`](atm/controller.py) manages the session, gathers missing inputs, displays the amount and destination, and checks expiry before applying a confirmation. [`atm/nlp.py`](atm/nlp.py) matches a small command grammar, and [`atm/i18n.py`](atm/i18n.py) supplies interface text.
- [`atm/services.py`](atm/services.py) validates amounts, verifies PINs, and applies mutations. A transfer commits the debit, credit, two ledger rows, request record, and audit event together.
- [`atm/storage.py`](atm/storage.py) owns the schema and write transactions. It stores money in integer paise, starts writes with `BEGIN IMMEDIATE`, and records the schema version with SQLite's `user_version`.
- [`atm/security.py`](atm/security.py) handles PIN hashing with a random salt and PBKDF2-SHA256. The service persists failed attempts before returning an authentication error.

The idempotency key identifies one successful mutation across withdrawal and transfer. Reusing the key with the same operation, source, amount, and destination returns the original receipt. Reusing it with different inputs fails. The migration preserves ledger history and uses the earliest receipt if legacy operations shared the same key. Service callers must reuse the key across retries. The CLI generates a fresh key for each confirmed command.

This is a local educational simulator. The service trusts its caller to authenticate the account, SQLite serializes writes, and idle expiry is enforced when a blocking prompt returns. Demo credentials are public. There is no real banking or cash-dispenser integration.

See the [interview guide](INTERVIEW.md) for the demo, design tradeoffs, and questions to practice.
