import json
import os
import shutil
from typing import List, Dict, Optional
from config import PROJECTS_DIR

class Project:
    def __init__(self, name: str, project_dir: str):
        self.name = name
        self.project_dir = project_dir
        self.json_path = os.path.join(project_dir, "project.json")
        self.segments_dir = os.path.join(project_dir, "segments")
        os.makedirs(self.segments_dir, exist_ok=True)
        self.segments: List[Dict] = []

    def save(self):
        data = {
            "name": self.name,
            "segments": self.segments
        }
        with open(self.json_path, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def create_new(name: str) -> "Project":
        project_dir = os.path.join(PROJECTS_DIR, name)
        os.makedirs(project_dir, exist_ok=True)
        proj = Project(name, project_dir)
        proj.save()
        return proj

    @staticmethod
    def load(project_dir: str) -> "Project":
        json_path = os.path.join(project_dir, "project.json")
        with open(json_path, 'r') as f:
            data = json.load(f)
        proj = Project(data["name"], project_dir)
        proj.segments = data["segments"]
        return proj

    def get_segment_dir(self, seg_idx: int) -> str:
        seg_dir = os.path.join(self.segments_dir, f"segment_{seg_idx}")
        os.makedirs(seg_dir, exist_ok=True)
        return seg_dir

    def get_chunk_audio_path(self, seg_idx: int, chunk_idx: int) -> str:
        seg_dir = self.get_segment_dir(seg_idx)
        return os.path.join(seg_dir, f"chunk_{chunk_idx}_audio.wav")

    def get_chunk_media_path(self, seg_idx: int, chunk_idx: int, filename: str = None) -> str:
        seg_dir = self.get_segment_dir(seg_idx)
        if filename:
            return os.path.join(seg_dir, filename)
        return os.path.join(seg_dir, f"chunk_{chunk_idx}_media")

    def add_segment(self, segment_data: Dict):
        self.segments.append(segment_data)
        self.save()

    def update_chunk_media(self, seg_idx: int, chunk_idx: int,
                           new_media_path: str = None, new_keyword: str = None):
        chunk = self.segments[seg_idx]["chunks"][chunk_idx]
        if new_media_path:
            ext = os.path.splitext(new_media_path)[1]
            dest = self.get_chunk_media_path(seg_idx, chunk_idx, f"user_media{ext}")
            shutil.copy2(new_media_path, dest)
            chunk["user_media_path"] = dest
        if new_keyword:
            chunk["current_keyword"] = new_keyword
            chunk["user_media_path"] = None
        self.save()

    def get_effective_media_path(self, seg_idx: int, chunk_idx: int) -> Optional[str]:
        chunk = self.segments[seg_idx]["chunks"][chunk_idx]
        return chunk.get("user_media_path") or chunk.get("local_media_path")

    def get_final_video_path(self) -> str:
        return os.path.join(self.project_dir, f"{self.name}_final.mp4")