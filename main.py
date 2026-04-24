import sys
import os
import tempfile
import shutil
from datetime import datetime
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt
from project_manager import Project
from worker_threads import ProcessSegmentWorker
from video_assembler import VideoAssembler
from chunk_editor import ChunkEditorDialog

try:
    from config import PROJECTS_DIR, TEMP_DIR
except ImportError:
    PROJECTS_DIR = "projects"
    TEMP_DIR = "temp"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Video Generator")
        self.setGeometry(100, 100, 1000, 700)
        self.current_project = None
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        top_bar = QHBoxLayout()
        self.new_project_btn = QPushButton("New Project")
        self.load_project_btn = QPushButton("Load Project")
        self.save_project_btn = QPushButton("Save Project")
        self.generate_full_btn = QPushButton("Generate Full Video")
        top_bar.addWidget(self.new_project_btn)
        top_bar.addWidget(self.load_project_btn)
        top_bar.addWidget(self.save_project_btn)
        top_bar.addStretch()
        top_bar.addWidget(self.generate_full_btn)
        layout.addLayout(top_bar)

        layout.addWidget(QLabel("Segments:"))
        self.segment_list = QListWidget()
        self.segment_list.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.segment_list)

        seg_buttons = QHBoxLayout()
        self.add_segment_btn = QPushButton("Add Audio Segment")
        self.edit_chunks_btn = QPushButton("Edit Selected Segment's Chunks")
        self.delete_segment_btn = QPushButton("Delete Selected Segment")
        seg_buttons.addWidget(self.add_segment_btn)
        seg_buttons.addWidget(self.edit_chunks_btn)
        seg_buttons.addWidget(self.delete_segment_btn)
        layout.addLayout(seg_buttons)

        layout.addWidget(QLabel("Progress Log:"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.new_project_btn.clicked.connect(self.new_project)
        self.load_project_btn.clicked.connect(self.load_project)
        self.save_project_btn.clicked.connect(self.save_project)
        self.add_segment_btn.clicked.connect(self.add_segment)
        self.edit_chunks_btn.clicked.connect(self.edit_segment_chunks)
        self.delete_segment_btn.clicked.connect(self.delete_segment)
        self.generate_full_btn.clicked.connect(self.generate_full_video)
        self.segment_list.itemDoubleClicked.connect(self.edit_segment_chunks)

    def log_message(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{timestamp}] {msg}")

    def new_project(self):
        name, ok = QInputDialog.getText(self, "New Project", "Project Name:")
        if not ok or not name:
            return
        try:
            os.makedirs(PROJECTS_DIR, exist_ok=True)
            self.current_project = Project.create_new(name)
            if self.current_project is None:
                QMessageBox.critical(self, "Error", "Failed to create project.")
                return
            self.log_message(f"Created project: {name}")
            self.refresh_segment_list()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def load_project(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Project Folder", PROJECTS_DIR)
        if not dir_path:
            return
        try:
            self.current_project = Project.load(dir_path)
            self.log_message(f"Loaded project: {self.current_project.name}")
            self.refresh_segment_list()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def save_project(self):
        if self.current_project:
            self.current_project.save()
            self.log_message("Project saved.")

    def refresh_segment_list(self):
        self.segment_list.clear()
        if not self.current_project:
            return
        for idx, seg in enumerate(self.current_project.segments):
            audio_name = os.path.basename(seg.get('audio_path', 'unknown'))
            self.segment_list.addItem(f"Segment {idx+1}: {audio_name}")

    def add_segment(self):
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "Create or load a project first.")
            return
        audio_path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", "", "Audio (*.mp3 *.wav *.m4a *.flac)")
        if not audio_path:
            return
        seg_idx = len(self.current_project.segments)
        self.log_message(f"Processing segment {seg_idx+1}...")
        self.worker = ProcessSegmentWorker(self.current_project, audio_path, seg_idx)
        self.worker.progress.connect(lambda msg: self.log_message(msg))
        self.worker.finished.connect(lambda data: self.on_segment_processed(seg_idx, data))
        self.worker.error.connect(lambda err: self.log_message(f"ERROR: {err}"))
        self.worker.start()

    def on_segment_processed(self, seg_idx, segment_data):
        self.current_project.add_segment(segment_data)
        self.refresh_segment_list()
        self.log_message(f"Segment {seg_idx+1} processed successfully.")

    def delete_segment(self):
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "Load a project first.")
            return
        current_row = self.segment_list.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Select Segment", "Please select a segment to delete.")
            return
        seg_idx = current_row
        segment = self.current_project.segments[seg_idx]
        audio_name = os.path.basename(segment.get('audio_path', 'unknown'))
        reply = QMessageBox.question(self, "Confirm Delete", 
                                     f"Delete segment '{audio_name}'?\nThis will also remove all its chunks and media files.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            # Delete the segment folder
            seg_dir = self.current_project.get_segment_dir(seg_idx)
            shutil.rmtree(seg_dir, ignore_errors=True)
            # Remove from project data
            self.current_project.segments.pop(seg_idx)
            self.current_project.save()
            self.refresh_segment_list()
            self.log_message(f"Deleted segment {seg_idx+1}: {audio_name}")

    def edit_segment_chunks(self):
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "Load a project first.")
            return
        current_row = self.segment_list.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Select Segment", "Please select a segment.")
            return
        seg_idx = current_row
        segment = self.current_project.segments[seg_idx]
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit Segment {seg_idx+1} Chunks")
        dialog.resize(800, 500)
        layout = QVBoxLayout(dialog)
        table = QTableWidget(len(segment["chunks"]), 3)
        table.setHorizontalHeaderLabels(["Chunk Text (preview)", "Keyword", "Media Path"])
        for i, chunk in enumerate(segment["chunks"]):
            table.setItem(i, 0, QTableWidgetItem(chunk["text"][:60] + "..."))
            table.setItem(i, 1, QTableWidgetItem(chunk["current_keyword"]))
            media = self.current_project.get_effective_media_path(seg_idx, i) or "None"
            table.setItem(i, 2, QTableWidgetItem(media))
        layout.addWidget(table)
        edit_btn = QPushButton("Edit Selected Chunk")
        layout.addWidget(edit_btn)
        def on_edit():
            row = table.currentRow()
            if row >= 0:
                editor = ChunkEditorDialog(self.current_project, seg_idx, row, self)
                if editor.exec():
                    chunk = self.current_project.segments[seg_idx]["chunks"][row]
                    table.setItem(row, 1, QTableWidgetItem(chunk["current_keyword"]))
                    media = self.current_project.get_effective_media_path(seg_idx, row) or "None"
                    table.setItem(row, 2, QTableWidgetItem(media))
        edit_btn.clicked.connect(on_edit)
        dialog.exec()

    def generate_full_video(self):
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "Load a project first.")
            return
        if not self.current_project.segments:
            QMessageBox.warning(self, "No Segments", "Add at least one audio segment.")
            return
        temp_dir = tempfile.mkdtemp()
        segment_videos = []
        try:
            for seg_idx in range(len(self.current_project.segments)):
                self.log_message(f"Assembling segment {seg_idx+1}...")
                seg_video = VideoAssembler.assemble_segment(self.current_project, seg_idx, temp_dir)
                segment_videos.append(seg_video)
            self.log_message("Concatenating all segments...")
            output_path = self.current_project.get_final_video_path()
            VideoAssembler.assemble_final(segment_videos, output_path)
            self.log_message(f"Video saved to {output_path}")
            QMessageBox.information(self, "Done", f"Video generated at {output_path}")
        except Exception as e:
            self.log_message(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error", str(e))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())