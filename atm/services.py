"""Banking use cases; amounts are integer rupees at the UI boundary."""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from uuid import uuid4
from .security import verify_pin
from .storage import connect, write_transaction


class ATMError(Exception):
    pass


@dataclass(frozen=True)
class Receipt:
    request_id: str
    kind: str
    amount_rupees: int
    balance_rupees: int


class BankService:
    def __init__(self, db_path):
        self.db_path = db_path

    def authenticate(self, account_id: str, pin: str) -> str:
        # Failed attempts are committed, not lost by rolling back an exception.
        result = None
        with write_transaction(self.db_path) as db:
            row = db.execute('SELECT * FROM accounts WHERE id=?', (account_id,)).fetchone()
            if row is None:
                # Do not distinguish unknown account vs invalid PIN in the UI.
                result = 'Invalid account or PIN'
            elif row['locked']:
                result = 'Account is locked'
            elif not verify_pin(pin, row['pin_hash']):
                attempts = row['failed_attempts'] + 1
                db.execute('UPDATE accounts SET failed_attempts=?,locked=? WHERE id=?',
                           (attempts, int(attempts >= 3), account_id))
                db.execute('INSERT INTO audit(account_id,event) VALUES (?,?)', (account_id, 'LOGIN_FAILED'))
                result = 'Invalid account or PIN'
            else:
                db.execute('UPDATE accounts SET failed_attempts=0 WHERE id=?', (account_id,))
                db.execute('INSERT INTO audit(account_id,event) VALUES (?,?)', (account_id, 'LOGIN_SUCCESS'))
        if result:
            raise ATMError(result)
        return account_id

    def balance(self, account_id: str) -> int:
        with closing(connect(self.db_path)) as db:
            row = db.execute('SELECT balance_paise FROM accounts WHERE id=?', (account_id,)).fetchone()
            if row is None:
                raise ATMError('Account not found')
            return row['balance_paise'] // 100

    @staticmethod
    def _check_amount(amount: int, *, multiples_of_100=False):
        if isinstance(amount, bool) or not isinstance(amount, int) or not 0 < amount <= 10_000:
            raise ATMError('Amount must be a whole number from Rs 1 to Rs 10000')
        if multiples_of_100 and amount % 100:
            raise ATMError('Withdrawal must be a multiple of Rs 100')

    def withdraw(self, account_id: str, amount: int, request_id: str | None = None) -> Receipt:
        self._check_amount(amount, multiples_of_100=True)
        request_id = request_id or uuid4().hex
        with write_transaction(self.db_path) as db:
            receipt = self._replay(db, request_id, account_id, 'WITHDRAW', amount)
            if receipt is not None:
                return receipt
            changed = db.execute('UPDATE accounts SET balance_paise=balance_paise-? '
                                 'WHERE id=? AND balance_paise>=?',
                                 (amount * 100, account_id, amount * 100)).rowcount
            if not changed:
                raise ATMError('Insufficient balance or account not found')
            balance = db.execute('SELECT balance_paise FROM accounts WHERE id=?', (account_id,)).fetchone()[0]
            entry = db.execute('INSERT INTO ledger(request_id,account_id,kind,amount_paise,balance_after_paise) '
                       'VALUES (?,?,?,?,?)', (uuid4().hex, account_id, 'WITHDRAW', amount * 100, balance))
            db.execute('INSERT INTO requests(request_id,ledger_id) VALUES (?,?)',
                       (request_id, entry.lastrowid))
            db.execute('INSERT INTO audit(account_id,event,detail) VALUES (?,?,?)',
                       (account_id, 'WITHDRAW_SUCCESS', request_id))
        return Receipt(request_id, 'WITHDRAW', amount, balance // 100)

    def transfer(self, sender: str, recipient: str, amount: int, request_id: str | None = None) -> Receipt:
        self._check_amount(amount)
        if sender == recipient:
            raise ATMError('Cannot transfer to the same account')
        request_id = request_id or uuid4().hex
        with write_transaction(self.db_path) as db:
            receipt = self._replay(db, request_id, sender, 'TRANSFER', amount, recipient)
            if receipt is not None:
                return receipt
            if not db.execute('SELECT 1 FROM accounts WHERE id=?', (recipient,)).fetchone():
                raise ATMError('Recipient not found')
            changed = db.execute('UPDATE accounts SET balance_paise=balance_paise-? '
                                 'WHERE id=? AND balance_paise>=?', (amount * 100, sender, amount * 100)).rowcount
            if not changed:
                raise ATMError('Insufficient balance or sender not found')
            db.execute('UPDATE accounts SET balance_paise=balance_paise+? WHERE id=?', (amount * 100, recipient))
            sender_balance = db.execute('SELECT balance_paise FROM accounts WHERE id=?', (sender,)).fetchone()[0]
            recipient_balance = db.execute('SELECT balance_paise FROM accounts WHERE id=?', (recipient,)).fetchone()[0]
            ledger_reference = uuid4().hex
            entry = db.execute('INSERT INTO ledger(request_id,account_id,kind,amount_paise,counterparty,balance_after_paise) '
                       'VALUES (?,?,?,?,?,?)', (ledger_reference + ':out', sender, 'TRANSFER_OUT', amount*100, recipient, sender_balance))
            db.execute('INSERT INTO ledger(request_id,account_id,kind,amount_paise,counterparty,balance_after_paise) '
                       'VALUES (?,?,?,?,?,?)', (ledger_reference + ':in', recipient, 'TRANSFER_IN', amount*100, sender, recipient_balance))
            db.execute('INSERT INTO requests(request_id,ledger_id) VALUES (?,?)',
                       (request_id, entry.lastrowid))
            db.execute('INSERT INTO audit(account_id,event,detail) VALUES (?,?,?)',
                       (sender, 'TRANSFER_SUCCESS', request_id))
        return Receipt(request_id, 'TRANSFER', amount, sender_balance // 100)

    @staticmethod
    def _replay(db, request_id, account_id, kind, amount, counterparty=None):
        entry = db.execute('''
            SELECT ledger.* FROM requests
            JOIN ledger ON ledger.id = requests.ledger_id
            WHERE requests.request_id = ?
        ''', (request_id,)).fetchone()
        if entry is None:
            return None
        ledger_kind = 'TRANSFER_OUT' if kind == 'TRANSFER' else kind
        if (entry['account_id'], entry['kind'], entry['amount_paise'], entry['counterparty']) != (
            account_id, ledger_kind, amount * 100, counterparty
        ):
            raise ATMError('Request ID conflicts with an earlier operation')
        return Receipt(request_id, kind, amount, entry['balance_after_paise'] // 100)

    def history(self, account_id: str, limit: int = 5):
        if not isinstance(limit, int) or not 1 <= limit <= 50:
            raise ATMError('Invalid history limit')
        with closing(connect(self.db_path)) as db:
            rows = db.execute('SELECT kind,amount_paise,counterparty,balance_after_paise,created_at '
                              'FROM ledger WHERE account_id=? ORDER BY id DESC LIMIT ?',
                              (account_id, limit)).fetchall()
            return [dict(row) for row in rows]
