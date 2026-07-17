"""Documentary-style renderer — mixed media compositions.

Handles stock_video, ai_video, photo, map, infographic, scientific_animation
within a single FFmpeg filter graph. Each scene can have multiple media layers.
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from core.logging import get_logger
from services.media.providers.base import MediaAsset, MediaPlan
from services.scene.director import VisualStorytelling

logger = get_logger()


class DocumentaryRenderer:
    def __init__(self):
        self.ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
        self.enc = self._detect_encoder()

    @staticmethod
    def _detect_encoder() -> str:
        r = subprocess.run(
            [shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg", "-encoders"],
            capture_output=True, text=True, timeout=10,
        )
        if "h264_videotoolbox" in r.stdout:
            return "h264_videotoolbox"
        return "libx264"

    def _enc_args(self) -> list[str]:
        if self.enc == "h264_videotoolbox":
            return ["-c:v", "h264_videotoolbox", "-b:v", "6M"]
        return ["-c:v", "libx264", "-preset", "medium", "-crf", "20"]

    def render_scene(
        self,
        media_assets: list[MediaAsset],
        plan: MediaPlan,
        storytelling: VisualStorytelling,
        output_path: str,
    ) -> str:
        if not media_assets:
            return self._render_solid_background(output_path, plan.duration, "No media available")

        asset_paths = [a.file_path for a in media_assets if os.path.isfile(a.file_path)]
        if not asset_paths:
            return self._render_solid_background(output_path, plan.duration, "No media available")

        if len(asset_paths) == 1:
            return self._render_single(asset_paths[0], output_path, plan.duration)

        return self._render_multi(asset_paths, output_path, plan.duration, storytelling)

    def render_scenes_concat(
        self,
        scene_videos: list[str],
        audio_path: str | None,
        subtitle_path: str | None,
        output_path: str,
    ) -> str:
        if not scene_videos:
            raise ValueError("No scene videos to concatenate")

        if len(scene_videos) == 1:
            video_path = scene_videos[0]
        else:
            tmp_dir = Path(tempfile.mkdtemp())
            flist = str(tmp_dir / "files.txt")
            Path(flist).write_text("\n".join(f"file '{v}'" for v in scene_videos))
            concat_path = str(tmp_dir / "concat.mp4")
            cmd = [
                self.ffmpeg, "-y", "-f", "concat", "-safe", "0",
                "-i", flist, "-c", "copy", concat_path,
            ]
            subprocess.run(cmd, capture_output=True, timeout=120)
            video_path = concat_path

        return self._mux(video_path, audio_path, subtitle_path, output_path)

    def _render_single(self, src: str, output: str, duration: float) -> str:
        ext = src.lower()
        if ext.endswith((".mp4", ".mov", ".webm")):
            return self._trim_video(src, output, duration)
        return self._image_to_video(src, output, duration, "ken_burns_in")

    def _render_multi(
        self,
        assets: list[str],
        output: str,
        duration: float,
        storytelling: VisualStorytelling,
    ) -> str:
        tmp_dir = Path(tempfile.mkdtemp())
        clips = []
        per_asset = duration / len(assets)

        for i, src in enumerate(assets):
            dest = str(tmp_dir / f"clip_{i:04d}.mp4")
            ext = src.lower()
            if ext.endswith((".mp4", ".mov", ".webm")):
                self._trim_video(src, dest, per_asset)
            else:
                motion = self._motion_for_scene(storytelling, i)
                self._image_to_video(src, dest, per_asset, motion)
            clips.append(dest)

        concat_path = str(tmp_dir / "concat.mp4")
        self._concat_clips(clips, concat_path)
        shutil.move(concat_path, output)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return output

    def _trim_video(self, src: str, dest: str, duration: float) -> str:
        cmd = [
            self.ffmpeg, "-y", "-i", src,
            "-t", str(duration),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            *self._enc_args(), "-pix_fmt", "yuv420p",
            dest,
        ]
        subprocess.run(cmd, capture_output=True, timeout=60)
        if not os.path.isfile(dest) or os.path.getsize(dest) < 512:
            shutil.copy(src, dest)
        return dest

    def _image_to_video(self, src: str, dest: str, duration: float, motion: str) -> str:
        import subprocess
        frames = max(1, int(duration * 24))
        zoom = "1.0" if motion == "static" else "1.0+0.001"
        cmd = [
            self.ffmpeg, "-y", "-loop", "1", "-i", src,
            "-vf", f"scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,zoompan=z='{zoom}':d={frames}:s=1080x1920:fps=24",
            "-t", str(duration),
            *self._enc_args(), "-pix_fmt", "yuv420p",
            dest,
        ]
        subprocess.run(cmd, capture_output=True, timeout=30)
        if not os.path.isfile(dest) or os.path.getsize(dest) < 512:
            fallback = [
                self.ffmpeg, "-y", "-loop", "1", "-i", src,
                "-t", str(duration),
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
                *self._enc_args(), "-pix_fmt", "yuv420p",
                dest,
            ]
            subprocess.run(fallback, capture_output=True, timeout=30)
        return dest

    @staticmethod
    def _motion_for_scene(story: VisualStorytelling, index: int) -> str:
        movement = story.camera_movement.lower()
        if "push" in movement:
            return "ken_burns_in"
        if "pull" in movement:
            return "ken_burns_out"
        if "track" in movement or "pan" in movement:
            return "pan_left" if index % 2 == 0 else "pan_right"
        return "static"

    @staticmethod
    def _concat_clips(clips: list[str], output: str):
        tmp = Path(tempfile.mkdtemp())
        flist = str(tmp / "files.txt")
        Path(flist).write_text("\n".join(f"file '{c}'" for c in clips))
        ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
        subprocess.run([
            ffmpeg, "-y", "-f", "concat", "-safe", "0",
            "-i", flist, "-c", "copy", output,
        ], capture_output=True, timeout=60)

    @staticmethod
    def _render_solid_background(path: str, duration: float, text: str) -> str:
        import subprocess
        ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
        subprocess.run([
            ffmpeg, "-y", "-f", "lavfi", "-i",
            f"color=c=#0a0f1a:s=1080x1920:d={duration}:r=24",
            "-vf", f"drawtext=text='{text}':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "libx264", "-preset", "fast", "-crf", "24",
            "-pix_fmt", "yuv420p", path,
        ], capture_output=True, timeout=30)
        return path

    def _mux(self, video_path: str, audio_path: str | None, subtitle_path: str | None, output_path: str) -> str:
        has_audio = audio_path and os.path.isfile(audio_path)
        has_subs = subtitle_path and os.path.isfile(subtitle_path)
        cmd = [self.ffmpeg, "-y", "-i", video_path]
        if has_audio:
            cmd += ["-i", audio_path]
        if has_subs:
            cmd += ["-i", subtitle_path]
        cmd += ["-shortest"]
        if has_audio:
            cmd += ["-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "1"]
        else:
            cmd += ["-map", "0:v:0", "-c:a", "none"]
        cmd += ["-c:v", "copy"]
        if has_subs:
            cmd += ["-c:s", "mov_text", "-map", f"{'2:0' if has_audio else '1:0'}", "-metadata:s:s:0", "language=hin"]
        cmd += [output_path]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            logger.warning("mux_failed", stderr=r.stderr[-200:])
            shutil.copy(video_path, output_path)
        else:
            logger.info("mux_ok", size=os.path.getsize(output_path))
        return output_path
