import os
import subprocess
from pathlib import Path

class VisualizerBridge:
    """
    Bridge to MIDIVisualizer (kosua20).
    Provides real-time interactive playback on screen and video rendering (.mp4)
    with Rousseau-style aesthetics (particles, flashes, wave, two-hand colors),
    and audio track synchronization via FFmpeg.
    """
    def __init__(self, visualizer_exe: str = None):
        if visualizer_exe is None:
            project_root = Path(__file__).resolve().parent.parent
            self.visualizer_exe = project_root / "tools" / "MIDIVisualizer" / "MIDIVisualizer.exe"
        else:
            self.visualizer_exe = Path(visualizer_exe)

        if not self.visualizer_exe.exists():
            raise FileNotFoundError(f"MIDIVisualizer executable not found at: {self.visualizer_exe}")

    def play(self, midi_path: str):
        """
        Launches MIDIVisualizer GUI on the user's desktop with falling notes and particles.
        """
        midi_path = str(Path(midi_path).resolve())
        cmd = (
            f'start "" "{self.visualizer_exe}" '
            f'--midi "{midi_path}" '
            f'--show-particles 1 '
            f'--show-flashes 1 '
            f'--show-wave 1 '
            f'--colors-per-set 1'
        )
        print(f"[Visualizer] Launching GUI on desktop for: {midi_path}")
        return subprocess.Popen(cmd, shell=True, cwd=str(self.visualizer_exe.parent))

    def render_video(
        self,
        midi_path: str,
        output_video_path: str,
        audio_path: str = None,
        framerate: int = 60,
        bitrate_mb: int = 15
    ):
        """
        Renders the MIDI performance into an MP4 video file at 60 FPS with particle effects.
        If audio_path is provided, synchronizes the song's audio track into the MP4 via FFmpeg.
        """
        midi_path = str(Path(midi_path).resolve())
        output_video_path = str(Path(output_video_path).resolve())
        os.makedirs(os.path.dirname(output_video_path), exist_ok=True)

        temp_video = output_video_path
        if audio_path and os.path.exists(audio_path):
            temp_video = str(Path(output_video_path).parent / f"{Path(output_video_path).stem}_visual.mp4")

        cmd = [
            str(self.visualizer_exe),
            "--midi", midi_path,
            "--export", temp_video,
            "--format", "MPEG4",
            "--framerate", str(framerate),
            "--bitrate", str(bitrate_mb),
            "--hide-window", "1",
            "--show-particles", "1",
            "--show-flashes", "1",
            "--show-wave", "1",
            "--colors-per-set", "1",
            "--quality", "HIGH"
        ]

        print(f"[Visualizer] Rendering video frames to: {temp_video} ({framerate} FPS)...")
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.visualizer_exe.parent))
        if proc.returncode != 0 or not os.path.exists(temp_video):
            raise RuntimeError(
                f"MIDIVisualizer render failed: {proc.stderr or proc.stdout or 'output video was not created'}"
            )

        # If audio is available, inject audio track with FFmpeg
        if audio_path and os.path.exists(audio_path) and os.path.exists(temp_video):
            print(f"[Visualizer] Synchronizing audio track with FFmpeg...")
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", temp_video,
                "-i", str(Path(audio_path).resolve()),
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "256k",
                "-shortest",
                output_video_path
            ]
            ff_proc = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            if ff_proc.returncode == 0:
                print(f"[Visualizer] Audio synchronized successfully!")
                try:
                    if temp_video != output_video_path and os.path.exists(temp_video):
                        os.remove(temp_video)
                except Exception:
                    pass
            else:
                raise RuntimeError(f"FFmpeg audio mux failed: {ff_proc.stderr or ff_proc.stdout}")

        print(f"[Visualizer] Final video ready: {output_video_path}")
        return output_video_path
