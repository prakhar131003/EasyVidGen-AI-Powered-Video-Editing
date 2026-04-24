import os
import tempfile
import subprocess
import shutil
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt
from moviepy.editor import AudioFileClip, VideoFileClip, ImageClip, ColorClip
from config import VIDEO_WIDTH, VIDEO_HEIGHT

class ChunkEditorDialog(QDialog):
    def __init__(self, project, seg_idx, chunk_idx, parent=None):
        super().__init__(parent)
        self.project = project
        self.seg_idx = seg_idx
        self.chunk_idx = chunk_idx
        self.chunk_data = project.segments[seg_idx]["chunks"][chunk_idx]
        self.setWindowTitle(f"Edit Chunk {chunk_idx+1}")
        self.setModal(True)
        self.resize(650, 550)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Chunk Text (editable):"))
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.chunk_data["text"])
        self.text_edit.setMaximumHeight(150)
        layout.addWidget(self.text_edit)

        layout.addWidget(QLabel("Keyword:"))
        self.keyword_edit = QLineEdit(self.chunk_data["current_keyword"])
        layout.addWidget(self.keyword_edit)

        btn_layout = QHBoxLayout()
        self.regenerate_from_text_btn = QPushButton("Regenerate Keyword from Text")
        self.gen_btn = QPushButton("Generate Media from Keyword")
        self.browse_btn = QPushButton("Browse Local File")
        self.preview_btn = QPushButton("Preview Chunk")
        btn_layout.addWidget(self.regenerate_from_text_btn)
        btn_layout.addWidget(self.gen_btn)
        btn_layout.addWidget(self.browse_btn)
        btn_layout.addWidget(self.preview_btn)
        layout.addLayout(btn_layout)

        self.preview_label = QLabel("Current media: " + 
            (self.project.get_effective_media_path(self.seg_idx, self.chunk_idx) or "None"))
        layout.addWidget(self.preview_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.regenerate_from_text_btn.clicked.connect(self.regenerate_keyword_from_text)
        self.gen_btn.clicked.connect(self.generate_new_media)
        self.browse_btn.clicked.connect(self.browse_local)
        self.preview_btn.clicked.connect(self.preview_chunk)

    def regenerate_keyword_from_text(self):
        new_text = self.text_edit.toPlainText().strip()
        if not new_text:
            QMessageBox.warning(self, "Error", "Chunk text cannot be empty.")
            return
        self.chunk_data["text"] = new_text
        from keyword_generator import KeywordGenerator
        kw_gen = KeywordGenerator()
        new_keyword = kw_gen.generate_keyword(new_text)
        self.keyword_edit.setText(new_keyword)
        self.chunk_data["current_keyword"] = new_keyword
        self.project.save()
        QMessageBox.information(self, "Success", f"Keyword updated to: {new_keyword}")

    def generate_new_media(self):
        new_keyword = self.keyword_edit.text().strip()
        if not new_keyword:
            return
        from media_fetcher import MediaFetcher
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            fetcher = MediaFetcher()
            url = fetcher.search_video(new_keyword)
            if url:
                ext = ".mp4"
                media_filename = f"chunk_{self.chunk_idx}_kw{new_keyword.replace(' ', '_')}{ext}"
                local_path = self.project.get_chunk_media_path(self.seg_idx, self.chunk_idx, media_filename)
                fetcher.download_media(url, local_path)
                self.chunk_data["current_keyword"] = new_keyword
                self.chunk_data["generated_media_url"] = url
                self.chunk_data["local_media_path"] = local_path
                self.chunk_data["user_media_path"] = None
                self.project.save()
                self.preview_label.setText(f"Current media: {local_path}")
                QMessageBox.information(self, "Success", "New media downloaded and assigned.")
            else:
                QMessageBox.warning(self, "Error", "No video found for keyword.")
        finally:
            QApplication.restoreOverrideCursor()

    def browse_local(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Media", "",
            "Video/Image (*.mp4 *.mov *.avi *.jpg *.png *.jpeg)")
        if file_path:
            ext = os.path.splitext(file_path)[1]
            media_filename = f"chunk_{self.chunk_idx}_user{ext}"
            dest = self.project.get_chunk_media_path(self.seg_idx, self.chunk_idx, media_filename)
            shutil.copy2(file_path, dest)
            self.chunk_data["user_media_path"] = dest
            self.project.save()
            self.preview_label.setText(f"Current media: {dest}")
            QMessageBox.information(self, "Success", "Media replaced with your file.")

    def preview_chunk(self):
        audio_path = self.project.get_chunk_audio_path(self.seg_idx, self.chunk_idx)
        if not os.path.exists(audio_path):
            QMessageBox.warning(self, "Preview Error", "Audio chunk file not found.")
            return
        media_path = self.project.get_effective_media_path(self.seg_idx, self.chunk_idx)
        duration = self.chunk_data.get("duration", 3.0)
        temp_dir = tempfile.mkdtemp()
        temp_video = os.path.join(temp_dir, "preview.mp4")
        try:
            audio_clip = AudioFileClip(audio_path)
            if media_path and os.path.exists(media_path):
                if media_path.endswith(('.mp4', '.mov', '.avi', '.webm')):
                    video_clip = VideoFileClip(media_path).subclip(0, duration)
                    if video_clip.duration < duration:
                        video_clip = video_clip.loop(duration=duration)
                else:  # image
                    video_clip = ImageClip(media_path, duration=duration).resize(height=VIDEO_HEIGHT)
            else:
                # Fallback: black screen without text (avoids ImageMagick)
                video_clip = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(0, 0, 0), duration=duration)
            video_clip = video_clip.set_audio(audio_clip)
            video_clip.write_videofile(temp_video, fps=24, codec='libx264', audio_codec='aac', logger=None, verbose=False)
            # Play with default system player
            if os.name == 'nt':
                os.startfile(temp_video)
            elif os.name == 'posix':
                subprocess.call(('xdg-open', temp_video))
            else:
                QMessageBox.information(self, "Preview", f"Preview video saved to {temp_video}")
        except Exception as e:
            QMessageBox.critical(self, "Preview Error", f"Failed to create preview:\n{str(e)}")

    def accept(self):
        new_text = self.text_edit.toPlainText().strip()
        if new_text:
            self.chunk_data["text"] = new_text
            self.project.save()
        super().accept()