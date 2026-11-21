import sqlite3
import tempfile
from contextlib import closing
import threading
import unittest
from pathlib import Path
from atm.nlp import interpret
from atm.services import ATMError, BankService
from atm.storage import connect, initialize, seed_demo


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'test.sqlite3'
        seed_demo(self.db)
        self.bank = BankService(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def test_login_and_lockout(self):
        self.assertEqual('1001', self.bank.authenticate('1001', '1234'))
        for _ in range(3):
            with self.assertRaises(ATMError):
                self.bank.authenticate('1002', '0000')
        with self.assertRaisesRegex(ATMError, 'locked'):
            self.bank.authenticate('1002', '5678')

    def test_withdraw_and_idempotency(self):
        first = self.bank.withdraw('1001', 500, 'withdraw-1')
        second = self.bank.withdraw('1001', 500, 'withdraw-1')
        self.assertEqual(first, second)
        self.assertEqual(self.bank.balance('1001'), 49500)
        with self.assertRaises(ATMError):
            self.bank.withdraw('1001', 600, 'withdraw-1')

    def test_transfer_balances_and_ledger(self):
        initial_total = self.bank.balance('1001') + self.bank.balance('1002')
        self.bank.transfer('1001', '1002', 750, 'transfer-1')
        self.bank.transfer('1001', '1002', 750, 'transfer-1')
        self.assertEqual(initial_total, self.bank.balance('1001') + self.bank.balance('1002'))
        self.assertEqual(len(self.bank.history('1001')), 1)
        self.assertEqual(len(self.bank.history('1002')), 1)

    def test_rollback_for_missing_recipient(self):
        original = self.bank.balance('1001')
        with self.assertRaises(ATMError):
            self.bank.transfer('1001', '9999', 500)
        self.assertEqual(original, self.bank.balance('1001'))

    def test_overdraw_and_amount_validation(self):
        for value in (0, -1, True, 99, 10100):
            with self.assertRaises(ATMError):
                self.bank.withdraw('1001', value)
        with self.assertRaises(ATMError):
            self.bank.withdraw('1002', 10000)
            self.bank.withdraw('1002', 10000)

    def test_intents(self):
        self.assertEqual(interpret('withdraw 500').amount, 500)
        self.assertEqual(interpret('இருப்பு').name, 'BALANCE')
        self.assertEqual(interpret('transfer 300 to 1002').recipient, '1002')
        self.assertEqual(interpret('ஆம்').name, 'CONFIRM')

    def test_concurrent_withdrawals_cannot_overdraw(self):
        results = []
        lock = threading.Lock()
        def withdraw(i):
            try:
                self.bank.withdraw('1002', 10000, f'parallel-{i}')
                result = 'ok'
            except ATMError:
                result = 'rejected'
            with lock:
                results.append(result)
        threads = [threading.Thread(target=withdraw, args=(i,)) for i in range(3)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(results.count('ok'), 1)
        self.assertEqual(self.bank.balance('1002'), 5000)

    def test_request_id_namespace_is_shared(self):
        self.bank.transfer('1001', '1002', 500, 'shared-id')
        with self.assertRaisesRegex(ATMError, 'conflicts'):
            self.bank.withdraw('1001', 500, 'shared-id')
        self.bank.withdraw('1001', 500, 'shared-id:out')
        self.assertEqual(49000, self.bank.balance('1001'))

    def test_transfer_rolls_back_after_debit_and_credit(self):
        with closing(connect(self.db)) as db:
            db.execute('''
                CREATE TRIGGER reject_credit_entry BEFORE INSERT ON ledger
                WHEN NEW.kind = 'TRANSFER_IN'
                BEGIN SELECT RAISE(ABORT, 'simulated ledger error'); END
            ''')
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'simulated ledger error'):
            self.bank.transfer('1001', '1002', 500, 'retry-me')
        self.assertEqual((50000, 15000), (self.bank.balance('1001'), self.bank.balance('1002')))
        self.assertEqual([], self.bank.history('1001'))
        self.assertEqual([], self.bank.history('1002'))
        with closing(connect(self.db)) as db:
            self.assertEqual(0, db.execute('SELECT COUNT(*) FROM requests').fetchone()[0])
            self.assertEqual(0, db.execute('SELECT COUNT(*) FROM audit').fetchone()[0])
            db.execute('DROP TRIGGER reject_credit_entry')
        self.bank.transfer('1001', '1002', 500, 'retry-me')
        self.assertEqual((49500, 15500), (self.bank.balance('1001'), self.bank.balance('1002')))

    def test_migration_backfills_legacy_receipts(self):
        with closing(connect(self.db)) as db:
            db.execute('DROP TABLE requests')
            db.execute('PRAGMA user_version=0')
            db.execute('UPDATE accounts SET balance_paise=4950000 WHERE id=?', ('1001',))
            db.execute('UPDATE accounts SET balance_paise=1550000 WHERE id=?', ('1002',))
            db.executemany(
                'INSERT INTO ledger(request_id, account_id, kind, amount_paise, counterparty, balance_after_paise) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                [('legacy:out', '1001', 'TRANSFER_OUT', 50000, '1002', 4950000),
                 ('legacy:in', '1002', 'TRANSFER_IN', 50000, '1001', 1550000)],
            )
        initialize(self.db)
        initialize(self.db)
        self.assertEqual(49500, self.bank.transfer('1001', '1002', 500, 'legacy').balance_rupees)
        self.assertEqual(15500, self.bank.balance('1002'))
        self.assertEqual(1, len(self.bank.history('1001')))

    def test_audit_entries(self):
        self.bank.authenticate('1001', '1234')
        self.bank.withdraw('1001', 100)
        with closing(connect(self.db)) as db:
            events = [r[0] for r in db.execute('SELECT event FROM audit')]
        self.assertIn('LOGIN_SUCCESS', events)
        self.assertIn('WITHDRAW_SUCCESS', events)

if __name__ == '__main__':
    unittest.main()
