"""Orchestrate a single authenticated ATM session."""
import time

from .i18n import message
from .nlp import interpret
from .security import read_pin
from .services import ATMError


class SessionExpired(Exception):
    pass


class ATMController:
    def __init__(self, service, io, language='en', session_seconds=180, *, clock=time.monotonic):
        self.service = service
        self.io = io
        self.language = language
        self.session_seconds = session_seconds
        self.clock = clock

    def say(self, key, **values):
        self.io.say(message(self.language, key, **values))

    def _listen(self, key):
        if self.clock() >= self.deadline:
            raise SessionExpired
        response = self.io.listen(message(self.language, key))
        now = self.clock()
        if now >= self.deadline:
            raise SessionExpired
        self.deadline = now + self.session_seconds
        return response

    def run(self):
        self.say('welcome')
        try:
            account = input(message(self.language, 'account') + ' ').strip()
            self.service.authenticate(account, read_pin(message(self.language, 'pin')))
        except ATMError as exc:
            self.io.say(str(exc))
            return
        except (EOFError, KeyboardInterrupt):
            self.say('bye')
            return

        self.deadline = self.clock() + self.session_seconds
        self.say('menu')
        try:
            self._run_session(account)
        except SessionExpired:
            self.say('timeout')
        except (EOFError, KeyboardInterrupt):
            pass
        self.say('bye')

    def _run_session(self, account):
        while True:
            intent = interpret(self._listen('choose'))
            if intent.name == 'EXIT':
                return
            try:
                if intent.name == 'BALANCE':
                    self.say('balance', amount=self.service.balance(account))
                elif intent.name == 'HISTORY':
                    rows = self.service.history(account)
                    if not rows:
                        self.say('empty_history')
                    for row in rows:
                        self.say('history_row', date=row['created_at'],
                                 action=message(self.language, row['kind']),
                                 amount=row['amount_paise'] // 100)
                elif intent.name in ('WITHDRAW', 'TRANSFER'):
                    self._confirm_transaction(account, intent)
                else:
                    self.say('unknown')
            except ATMError as exc:
                self.say('rejected', reason=str(exc))

    def _confirm_transaction(self, account, intent):
        amount = intent.amount
        if amount is None:
            amount_input = interpret(self._listen('amount'))
            if amount_input.name != 'AMOUNT':
                self.say('cancel')
                return
            amount = amount_input.amount

        if intent.name == 'TRANSFER':
            recipient = intent.recipient or self._listen('recipient').strip()
            if not (recipient.isascii() and recipient.isdigit() and len(recipient) >= 4):
                self.say('cancel')
                return
            self.say('confirm_transfer', amount=amount, recipient=recipient)
        else:
            self.say('confirm_withdraw', amount=amount)

        if interpret(self._listen('confirmation')).name != 'CONFIRM':
            self.say('cancel')
            return
        if intent.name == 'TRANSFER':
            receipt = self.service.transfer(account, recipient, amount)
        else:
            receipt = self.service.withdraw(account, amount)
        self.say('success', action=message(self.language, receipt.kind),
                 reference=receipt.request_id, balance=receipt.balance_rupees)
