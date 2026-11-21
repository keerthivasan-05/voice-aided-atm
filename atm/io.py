"""Replaceable console / optional voice interaction; never speak a secret PIN."""


class ConsoleIO:
    def say(self, text):
        print(text)

    def listen(self, prompt):
        return input(prompt + '\n> ').strip()


class VoiceIO(ConsoleIO):
    def __init__(self, language='en'):
        try:
            import speech_recognition as sr
            import pyttsx3
        except ImportError as exc:
            raise RuntimeError('Install requirements-voice.txt for microphone mode') from exc
        self.sr = sr
        self.recognizer = sr.Recognizer()
        self.recognizer.operation_timeout = 8
        self._calibrated = False
        self.engine = pyttsx3.init()
        self.language = 'ta-IN' if language == 'ta' else 'en-IN'

    def say(self, text):
        print(text)
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception:
            print('[TTS unavailable; printed instead]')

    def listen(self, prompt):
        self.say(prompt)
        try:
            with self.sr.Microphone() as source:
                if not self._calibrated:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                    self._calibrated = True
                print('[listening]', flush=True)
                audio = self.recognizer.listen(source, timeout=6, phrase_time_limit=6)
            command = self.recognizer.recognize_google(audio, language=self.language)
            print('[recognized]', command)
            return command
        except (self.sr.UnknownValueError, self.sr.RequestError, self.sr.WaitTimeoutError, OSError):
            return input('Voice unavailable; type command: ').strip()
