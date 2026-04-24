from moviepy.editor import *
import os
from typing import List
from config import VIDEO_WIDTH, VIDEO_HEIGHT, FPS, TRANSITION_DURATION

class VideoAssembler:
    @staticmethod
    def create_chunk_clip(audio_path: str, media_path: str = None, duration: float = None) -> VideoClip:
        audio_clip = AudioFileClip(audio_path)
        if duration is None:
            duration = audio_clip.duration

        if media_path and os.path.exists(media_path):
            if media_path.endswith(('.mp4', '.mov', '.avi', '.webm')):
                video_clip = VideoFileClip(media_path).subclip(0, duration)
                if video_clip.duration < duration:
                    video_clip = video_clip.loop(duration=duration)
            else:
                video_clip = ImageClip(media_path, duration=duration).resize(height=VIDEO_HEIGHT)
        else:
            # fallback: black screen with text
            video_clip = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(0,0,0), duration=duration)
            txt = TextClip("No media", fontsize=50, color='white', size=video_clip.size)
            txt = txt.set_duration(duration).set_position('center')
            video_clip = CompositeVideoClip([video_clip, txt])

        video_clip = video_clip.set_audio(audio_clip)
        return video_clip

    @staticmethod
    def concatenate_with_transitions(clips: List[VideoClip]) -> VideoClip:
        if not clips:
            return None
        if len(clips) == 1:
            return clips[0]
        final = clips[0]
        for next_clip in clips[1:]:
            final = CompositeVideoClip([
                final.crossfadeout(TRANSITION_DURATION),
                next_clip.crossfadein(TRANSITION_DURATION).set_start(final.duration - TRANSITION_DURATION)
            ])
            audio = CompositeAudioClip([
                final.audio.volumex(1.0).audio_fadeout(TRANSITION_DURATION),
                next_clip.audio.volumex(1.0).audio_fadein(TRANSITION_DURATION).set_start(final.duration - TRANSITION_DURATION)
            ])
            final = final.set_audio(audio)
        return final

    @staticmethod
    def assemble_segment(project, seg_idx: int, temp_dir: str) -> str:
        segment = project.segments[seg_idx]
        clips = []
        for chunk_idx, chunk in enumerate(segment["chunks"]):
            audio_chunk_path = project.get_chunk_audio_path(seg_idx, chunk_idx)
            media_path = project.get_effective_media_path(seg_idx, chunk_idx)
            duration = chunk.get("duration", 3.0)
            clip = VideoAssembler.create_chunk_clip(audio_chunk_path, media_path, duration)
            clips.append(clip)
        segment_video = VideoAssembler.concatenate_with_transitions(clips)
        out_path = os.path.join(temp_dir, f"segment_{seg_idx}.mp4")
        segment_video.write_videofile(out_path, fps=FPS, codec='libx264', audio_codec='aac', logger=None)
        return out_path

    @staticmethod
    def assemble_final(segment_video_paths: List[str], output_path: str):
        clips = [VideoFileClip(p) for p in segment_video_paths]
        final = VideoAssembler.concatenate_with_transitions(clips)
        final.write_videofile(output_path, fps=FPS, codec='libx264', audio_codec='aac', logger=None)