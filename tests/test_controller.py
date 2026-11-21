import unittest
from unittest.mock import Mock, patch

from atm.controller import ATMController
from atm.nlp import interpret
from atm.services import Receipt


class ControllerTests(unittest.TestCase):
    def run_session(self, commands, *, language='en', expire_on=None):
        bank = Mock()
        bank.transfer.return_value = Receipt('demo', 'TRANSFER', 300, 49_700)
        io = Mock()
        now = 0

        def listen(_prompt):
            nonlocal now
            command = next(commands)
            if command == expire_on:
                now += 180
            return command

        io.listen.side_effect = listen
        controller = ATMController(bank, io, language, clock=lambda: now)
        with patch('builtins.input', return_value='1001'), patch(
            'atm.controller.read_pin', return_value='1234'
        ):
            controller.run()
        return bank, [call.args[0] for call in io.say.call_args_list]

    def test_transfer_confirmation_names_recipient_and_honors_cancel(self):
        bank, output = self.run_session(iter(['transfer 300 to 1002', 'no', 'exit']))
        self.assertIn('Transfer Rs 300 to account 1002?', output)
        bank.transfer.assert_not_called()

    def test_expired_confirmation_never_debits(self):
        bank, output = self.run_session(iter(['withdraw 500', 'yes']), expire_on='yes')
        bank.withdraw.assert_not_called()
        self.assertIn('Session timed out.', output)

    def test_tamil_confirmed_transfer_passes_bound_amount_and_recipient(self):
        bank, output = self.run_session(iter(['அனுப்பு 300 1002', 'ஆம்', 'வெளியேறு']), language='ta')
        bank.transfer.assert_called_once_with('1001', '1002', 300)
        self.assertTrue(any('1002' in line for line in output))

    def test_invalid_commands_do_not_extract_partial_amounts(self):
        for command in ('withdraw -500', 'withdraw 500.5', 'withdraw 1,000',
                        'do not withdraw 500', 'transfer to 1002', 'withdraw ' + '9' * 5000):
            with self.subTest(command=command[:50]):
                self.assertEqual(interpret(command).name, 'UNKNOWN')
