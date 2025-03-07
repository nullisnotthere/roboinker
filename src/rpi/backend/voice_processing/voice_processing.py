"""
Source: https://github.com/alphacep/vosk-api/
        blob/master/python/example/test_microphone.py
"""

import queue
import sys
import json
import sounddevice as sd

from vosk import Model, KaldiRecognizer


class VoiceProcessor:
    """Class to process voice. Can start/stop listening and retreive
    speech via the microphone as text."""
    def __init__(self,
                 lang: str = "en-us",
                 samplerate: int = 16000,
                 blocksize: int = 8000,
                 device=None):
        self.model = Model(lang=lang)
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.device = device

        self.recogniser = KaldiRecognizer(self.model, self.samplerate)
        self.q = queue.Queue()
        self.stream = None

    def _callback(self, indata, _frames, _time, status):
        # This is called (from a separate thread) for each audio block.
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def start_listening(self):
        """Initialise and start the listener stream."""
        self.stream = sd.RawInputStream(
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            device=self.device,
            dtype="int16",
            channels=1,
            callback=self._callback
        )
        self.stream.start()
        print("Listening...")

    def stop_listening(self):
        """Stop and close the listener stream."""
        if self.stream:
            self.stream.stop()
            self.stream.close()
        print("Stopped listening.")

    def process_voice(self) -> dict[str, str]:
        """Recognises voice as text from microphone data."""
        data = self.q.get()
        if self.recogniser.AcceptWaveform(data):
            result = self.recogniser.Result()
        else:
            result = self.recogniser.PartialResult()
        return json.loads(result)
