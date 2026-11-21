"""Parse a small English/Tamil command grammar for text and speech input."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    name: str
    amount: int | None = None
    recipient: str | None = None


NUMBERS = {
    'five hundred': 500, 'one thousand': 1000, 'two thousand': 2000,
    'ஐநூறு': 500, 'ஆயிரம்': 1000,
}
COMMANDS = {
    'CONFIRM': ('yes', 'y', 'confirm', 'ஆம்', 'சரி'),
    'CANCEL': ('no', 'n', 'cancel', 'இல்லை', 'வேண்டாம்'),
    'EXIT': ('exit', 'quit', 'logout', 'வெளியேறு', 'முடி'),
    'HISTORY': ('history', 'statement', 'transactions', 'வரலாறு', 'பரிவர்த்தனை'),
    'BALANCE': ('balance', 'இருப்பு'),
}
AMOUNT = r'(?:[0-9]{1,5}|' + '|'.join(NUMBERS) + ')'
WITHDRAW = re.compile(rf'(?:withdraw|cash|பணம் எடு|எடுக்க)(?: ({AMOUNT}))?')
TRANSFER = re.compile(
    rf'(?:transfer|send|அனுப்பு|மாற்று)(?: ({AMOUNT})(?: (?:to )?([0-9]{{4,}}))?)?'
)


def interpret(utterance: str) -> Intent:
    text = ' '.join(utterance.casefold().split())
    for action, commands in COMMANDS.items():
        if text in commands:
            return Intent(action)

    for action, pattern in (('WITHDRAW', WITHDRAW), ('TRANSFER', TRANSFER)):
        match = pattern.fullmatch(text)
        if match:
            raw_amount = match[1]
            amount = None
            if raw_amount is not None:
                amount = NUMBERS[raw_amount] if raw_amount in NUMBERS else int(raw_amount)
            recipient = match[2] if action == 'TRANSFER' else None
            return Intent(action, amount, recipient)

    if re.fullmatch(r'[0-9]{1,5}', text):
        return Intent('AMOUNT', int(text))
    return Intent('UNKNOWN')
