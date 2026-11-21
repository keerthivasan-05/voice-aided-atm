"""Entry point: python main.py --seed-demo --mode text --language en"""
import argparse
from pathlib import Path
from atm.controller import ATMController
from atm.io import ConsoleIO, VoiceIO
from atm.services import BankService
from atm.storage import initialize, seed_demo


def main():
    parser = argparse.ArgumentParser(description='Voice-aided ATM final-year simulator')
    parser.add_argument('--db', default=str(Path(__file__).parent / 'atm_demo.sqlite3'))
    parser.add_argument('--language', choices=('en', 'ta'), default='en')
    parser.add_argument('--mode', choices=('text', 'voice'), default='text')
    parser.add_argument('--seed-demo', action='store_true', help='Create sample accounts if absent')
    args = parser.parse_args()
    if args.seed_demo:
        seed_demo(args.db)
    else:
        initialize(args.db)
    io = ConsoleIO() if args.mode == 'text' else VoiceIO(args.language)
    ATMController(BankService(args.db), io, args.language).run()


if __name__ == '__main__':
    main()
