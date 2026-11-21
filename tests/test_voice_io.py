import unittest
from unittest.mock import MagicMock, Mock, patch

from atm.io import VoiceIO


class VoiceIOTests(unittest.TestCase):
    def setUp(self):
        self.speech = Mock(
            UnknownValueError=type('UnknownValueError', (Exception,), {}),
            RequestError=type('RequestError', (Exception,), {}),
            WaitTimeoutError=type('WaitTimeoutError', (Exception,), {}),
        )
        self.speech.Microphone.return_value = MagicMock()
        with patch.dict('sys.modules', speech_recognition=self.speech, pyttsx3=Mock()):
            self.voice = VoiceIO()
        self.recognizer = self.speech.Recognizer.return_value

    @patch('builtins.print')
    def test_calibrates_once_for_multiple_commands(self, _print):
        self.recognizer.recognize_google.side_effect = ['balance', 'exit']
        self.assertEqual('balance', self.voice.listen('Choose a transaction'))
        self.assertEqual('exit', self.voice.listen('Choose a transaction'))
        source = self.speech.Microphone.return_value.__enter__.return_value
        self.recognizer.adjust_for_ambient_noise.assert_called_once_with(source, duration=0.3)
        self.assertEqual(2, self.recognizer.listen.call_count)

    @patch('builtins.print')
    @patch('builtins.input', return_value=' balance ')
    def test_network_timeout_falls_back_to_keyboard(self, keyboard, _print):
        self.recognizer.recognize_google.side_effect = TimeoutError
        self.assertEqual(8, self.recognizer.operation_timeout)
        self.assertEqual('balance', self.voice.listen('Choose a transaction'))
        keyboard.assert_called_once()
