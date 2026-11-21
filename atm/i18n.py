"""Hand-translated user-facing prompts for the demonstration."""
MESSAGES = {
'en': {
'welcome': 'Voice Aided ATM - Intermediate Edition',
'account': 'Demo account number:', 'pin': 'PIN (keyboard only):',
'menu': 'Commands: balance | withdraw 500 | transfer 300 to 1002 | history | exit',
'choose': 'Choose a transaction',
'amount': 'Amount in whole rupees:',
'recipient': 'Recipient account number:',
'confirmation': 'Answer yes or no:',
'confirm_withdraw': 'Withdraw Rs {amount}?',
'confirm_transfer': 'Transfer Rs {amount} to account {recipient}?',
'timeout': 'Session timed out.',
'empty_history': 'No transactions yet.',
'history_row': '{date} | {action} | Rs {amount}',
'rejected': 'Transaction rejected: {reason}',
'WITHDRAW': 'Withdrawal', 'TRANSFER': 'Transfer',
'TRANSFER_OUT': 'Transfer sent', 'TRANSFER_IN': 'Transfer received',
'balance': 'Available balance: Rs {amount}',
'success': '{action} completed. Reference {reference}. Balance: Rs {balance}',
'cancel': 'Cancelled. No money moved.', 'bye': 'Session closed.',
'unknown': 'I did not understand. Please repeat.', 'locked': 'Please retry or contact an administrator.',
},
'ta': {
'welcome': 'குரல் வழி ஏடிஎம் - இடைநிலை பதிப்பு',
'account': 'மாதிரி கணக்கு எண்:', 'pin': 'ரகசிய எண் (விசைப்பலகை மட்டும்):',
'menu': 'கட்டளைகள்: இருப்பு | பணம் எடு 500 | அனுப்பு 300 1002 | பரிவர்த்தனை | வெளியேறு',
'choose': 'ஒரு பரிவர்த்தனையைத் தேர்வு செய்யவும்',
'amount': 'தொகையை முழு ரூபாயில் உள்ளிடவும்:',
'recipient': 'பெறுநரின் கணக்கு எண்:',
'confirmation': 'ஆம் அல்லது இல்லை என்று பதிலளிக்கவும்:',
'confirm_withdraw': 'ரூ {amount} எடுக்கவா?',
'confirm_transfer': 'ரூ {amount} தொகையை {recipient} கணக்கிற்கு அனுப்பவா?',
'timeout': 'அமர்வு நேரம் முடிந்தது.',
'empty_history': 'இதுவரை பரிவர்த்தனைகள் இல்லை.',
'history_row': '{date} | {action} | ரூ {amount}',
'rejected': 'பரிவர்த்தனை நிராகரிக்கப்பட்டது: {reason}',
'WITHDRAW': 'பணம் எடுத்தல்', 'TRANSFER': 'பணப் பரிமாற்றம்',
'TRANSFER_OUT': 'அனுப்பிய தொகை', 'TRANSFER_IN': 'பெற்ற தொகை',
'balance': 'கிடைக்கும் இருப்பு: ரூ {amount}',
'success': '{action} முடிந்தது. குறிப்பு {reference}. இருப்பு: ரூ {balance}',
'cancel': 'ரத்து செய்யப்பட்டது. பணம் மாற்றப்படவில்லை.', 'bye': 'அமர்வு முடிந்தது.',
'unknown': 'கட்டளை புரியவில்லை. மீண்டும் முயற்சிக்கவும்.', 'locked': 'மீண்டும் முயற்சிக்கவும் அல்லது நிர்வாகியை அணுகவும்.',
},
}


def message(language, key, **kwargs):
    return MESSAGES[language][key].format(**kwargs)
