from PySide6.QtCore import QThread, Signal
import os
import re
from pydub import AudioSegment
import whisper
from keyword_generator import KeywordGenerator
from media_fetcher import MediaFetcher
from config import MIN_CHUNK_SECONDS, MAX_CHUNK_SECONDS

class ProcessSegmentWorker(QThread):
    progress = Signal(str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, project, audio_path, segment_index):
        super().__init__()
        self.project = project
        self.audio_path = audio_path
        self.segment_index = segment_index

    def run(self):
        try:
            self.progress.emit("Loading and transcribing with word timestamps...")
            model = whisper.load_model("base")
            result = model.transcribe(self.audio_path, word_timestamps=True)
            full_text = result["text"]
            word_segments = []
            for seg in result["segments"]:
                for word in seg.get("words", []):
                    word_segments.append({
                        "word": word["word"].strip(),
                        "start": word["start"],
                        "end": word["end"]
                    })
            self.progress.emit(f"Transcribed {len(word_segments)} words.")

            # Group into sentences
            sentences = self._group_words_into_sentences(word_segments)
            self.progress.emit(f"Detected {len(sentences)} sentences.")

            # Merge short and split long sentences
            chunks = self._optimize_chunks(sentences)
            self.progress.emit(f"Final chunks: {len(chunks)} (each 3-10 seconds)")

            # Load full audio
            audio = AudioSegment.from_file(self.audio_path)

            # Process each chunk
            chunks_data = []
            for i, chunk in enumerate(chunks):
                start = chunk["start"]
                end = chunk["end"]
                start_ms = int(start * 1000)
                end_ms = int(end * 1000)
                chunk_text = chunk["text"]

                # Extract audio segment
                audio_chunk = audio[start_ms:end_ms]
                audio_path_chunk = self.project.get_chunk_audio_path(self.segment_index, i)
                audio_chunk.export(audio_path_chunk, format="wav")

                chunks_data.append({
                    "text": chunk_text,
                    "duration": end - start,
                    "audio_path": audio_path_chunk,
                    "start": start,
                    "end": end
                })

            # Generate keywords and fetch media
            self.progress.emit("Generating keywords and fetching media from Pexels...")
            kw_gen = KeywordGenerator()
            fetcher = MediaFetcher()
            final_chunks = []
            for i, chunk in enumerate(chunks_data):
                self.progress.emit(f"  Chunk {i+1}/{len(chunks_data)}: generating keyword...")
                keyword = kw_gen.generate_keyword(chunk["text"])
                self.progress.emit(f"    Keyword: '{keyword}'")
                
                # Fetch media from Pexels
                video_url = fetcher.search_video(keyword)
                local_media_path = None
                if video_url:
                    self.progress.emit(f"    Downloading media...")
                    ext = ".mp4"
                    media_filename = f"chunk_{i}_generated{ext}"
                    local_media_path = self.project.get_chunk_media_path(self.segment_index, i, media_filename)
                    fetcher.download_media(video_url, local_media_path)
                    self.progress.emit(f"    Media saved to {local_media_path}")
                else:
                    self.progress.emit(f"    No media found for keyword '{keyword}' - will use black screen.")
                
                final_chunks.append({
                    "text": chunk["text"],
                    "original_keyword": keyword,
                    "current_keyword": keyword,
                    "generated_media_url": video_url,
                    "local_media_path": local_media_path,
                    "user_media_path": None,
                    "duration": chunk["duration"]
                })

            segment_data = {
                "audio_path": self.audio_path,
                "transcription": full_text,
                "chunks": final_chunks
            }
            self.progress.emit(f"Segment processing complete: {len(final_chunks)} chunks with media.")
            self.finished.emit(segment_data)

        except Exception as e:
            self.error.emit(str(e))

    def _group_words_into_sentences(self, word_segments):
        sentences = []
        current_sentence = {"words": [], "start": None, "end": None, "text": ""}
        for w in word_segments:
            if current_sentence["start"] is None:
                current_sentence["start"] = w["start"]
            current_sentence["words"].append(w)
            current_sentence["end"] = w["end"]
            current_sentence["text"] += w["word"] + " "
            # Check for sentence boundary: punctuation followed by space or end of segment
            if w["word"] in ['.', '!', '?']:
                current_sentence["text"] = current_sentence["text"].strip()
                sentences.append(current_sentence)
                current_sentence = {"words": [], "start": None, "end": None, "text": ""}
        if current_sentence["words"]:
            current_sentence["text"] = current_sentence["text"].strip()
            sentences.append(current_sentence)
        return sentences

    def _optimize_chunks(self, sentences):
        # Convert to simple list
        chunks = []
        for sent in sentences:
            duration = sent["end"] - sent["start"]
            chunks.append({
                "text": sent["text"],
                "start": sent["start"],
                "end": sent["end"],
                "duration": duration
            })
        # Merge short consecutive chunks
        merged = []
        i = 0
        while i < len(chunks):
            current = chunks[i]
            if current["duration"] < MIN_CHUNK_SECONDS and i+1 < len(chunks):
                # Merge with next
                next_chunk = chunks[i+1]
                merged_text = current["text"] + " " + next_chunk["text"]
                merged_start = current["start"]
                merged_end = next_chunk["end"]
                merged_duration = merged_end - merged_start
                merged.append({
                    "text": merged_text,
                    "start": merged_start,
                    "end": merged_end,
                    "duration": merged_duration
                })
                i += 2
            else:
                merged.append(current)
                i += 1
        # Split long chunks
        final_chunks = []
        for chunk in merged:
            if chunk["duration"] <= MAX_CHUNK_SECONDS:
                final_chunks.append(chunk)
            else:
                # Split by sentences if possible
                sentences_in_chunk = re.split(r'(?<=[.!?])\s+', chunk["text"])
                if len(sentences_in_chunk) > 1:
                    total_dur = chunk["duration"]
                    total_chars = len(chunk["text"])
                    current_pos = chunk["start"]
                    for sent in sentences_in_chunk:
                        if not sent:
                            continue
                        sent_with_dot = sent + ". "
                        sent_len = len(sent_with_dot)
                        sent_dur = (sent_len / total_chars) * total_dur
                        end_pos = current_pos + sent_dur
                        if end_pos - current_pos >= MIN_CHUNK_SECONDS:
                            final_chunks.append({
                                "text": sent_with_dot.strip(),
                                "start": current_pos,
                                "end": end_pos,
                                "duration": sent_dur
                            })
                            current_pos = end_pos
                else:
                    # Split long sentence into two halves
                    half_dur = chunk["duration"] / 2
                    if half_dur < MIN_CHUNK_SECONDS:
                        final_chunks.append(chunk)
                    else:
                        text = chunk["text"]
                        half_char = len(text) // 2
                        split_pos = text.find(' ', half_char)
                        if split_pos == -1:
                            split_pos = half_char
                        part1 = text[:split_pos]
                        part2 = text[split_pos:]
                        part1_dur = (len(part1) / len(text)) * chunk["duration"]
                        part2_dur = chunk["duration"] - part1_dur
                        final_chunks.append({
                            "text": part1.strip(),
                            "start": chunk["start"],
                            "end": chunk["start"] + part1_dur,
                            "duration": part1_dur
                        })
                        final_chunks.append({
                            "text": part2.strip(),
                            "start": chunk["start"] + part1_dur,
                            "end": chunk["end"],
                            "duration": part2_dur
                        })
        return final_chunks