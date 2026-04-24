import whisper

class Transcriber:
    def __init__(self, model_name="base"):
        self.model = whisper.load_model(model_name)

    def transcribe_with_word_timestamps(self, audio_path: str):
        result = self.model.transcribe(audio_path, word_timestamps=True)
        full_text = result["text"]
        word_segments = []
        for seg in result["segments"]:
            for word in seg.get("words", []):
                word_segments.append({
                    "word": word["word"].strip(),
                    "start": word["start"],
                    "end": word["end"]
                })
        return full_text, word_segments