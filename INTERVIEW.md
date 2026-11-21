# SWE interview walkthrough

## A 45-second introduction

“I've been improving a bilingual ATM simulator built with Python and SQLite. It runs in the terminal and has an optional voice adapter. The most interesting part is keeping a money transfer consistent across both account balances, transaction history, and retries. A transfer writes everything in one SQLite transaction. If the same request ID is retried, the service returns the saved receipt, and if that ID is reused with different inputs, it rejects the request. I can demonstrate the transaction flow and show the tests that check rollback, concurrent withdrawals, and expired confirmations.”

## Five-minute demo

1. Start with a fresh file using `python3 main.py --db ./interview-demo.sqlite3 --seed-demo`. Sign in as `1001` with PIN `1234`, then enter `balance` to show Rs 50,000.
2. Enter `transfer 300 to 1002` and answer `no`. Run `balance` again to confirm it stays at Rs 50,000.
3. Enter the same transfer and answer `yes`. The sender's balance is Rs 49,700. Open `history` and show the transfer entry and its amount.
4. Exit and reopen the same database with `python3 main.py --db ./interview-demo.sqlite3 --language ta`. Sign in as `1002` with PIN `5678`. Use `இருப்பு` and `பரிவர்த்தனை` to show Rs 15,300 and the incoming transfer.
5. Run `python3 -m unittest discover -s tests -v`. Open `test_transfer_rolls_back_after_debit_and_credit` and explain why it forces an error at the second ledger insert.

## Questions to practice

| Question | What to explain |
| --- | --- |
| Where is the transaction boundary? | The service checks the request key and destination, debits and credits the accounts, and writes the ledger, request, and audit records inside one write transaction. An exception rolls all of it back. |
| What if two people withdraw from the same balance at once? | SQLite allows one writer at a time. The debit also includes the available-balance condition in the update itself. The concurrency test starts three Rs 10,000 withdrawals against Rs 15,000 and only one succeeds. |
| What if the transfer commits but the caller loses the response? | The caller retries with the same request ID. The original sender balance and amount come from the saved ledger row. Explain that retyping a command in the CLI creates a new operation. |
| Why store money in integer paise? | Integer addition and subtraction are exact. The UI accepts whole rupees and converts at the service boundary. |
| How did you verify a real rollback? | A temporary SQLite trigger makes the destination ledger insert fail after both balance updates. The test verifies both original balances, empty histories, and no request or audit rows, then retries successfully. |
| What can voice recognition get wrong? | It can transcribe the wrong amount or destination. Whole-command parsing avoids extracting a plausible amount from malformed input, and the confirmation reads back both details. The microphone integration requires a separate hardware test. |
| What would you change for a deployed multi-user system? | Start with service-side authorization tied to authenticated sessions, then revisit persistence and locking for concurrent writers. Measure expected traffic and use those requirements to justify a database choice. |

## Code to be ready to explain

- `BankService.transfer` and `write_transaction` show where the business rules and atomicity live.
- `BankService._replay` shows how the operation is validated on retry.
- `ATMController._listen` checks a monotonic clock before and after each prompt. Practice explaining why a late “yes” is discarded even when the input adapter blocks.
- `initialize` shows how a legacy receipt can survive a schema upgrade without changing balances.

Practice tracing one confirmed transfer line by line. In the interview, describe the parts you personally implemented or verified and be ready to explain what you changed.
