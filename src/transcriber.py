"""Audio-to-MIDI pipelines for piano recordings and full musical mixes."""

import os
import gc
import shutil
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf
import torch


class AudioToMidiTranscriber:
    """Select a piano-specialized or mixed-song transcription pipeline.

    ``auto`` detects whether a recording contains prominent vocals/drums. It is
    a source-type heuristic, not a music-genre classifier; ambiguous material
    should be assigned explicitly by the user.
    """

    MODES = (
            "auto", "piano_solo", "piano_solo_pedal",
        "piano_with_accompaniment", "full_song",
    )

    def __init__(self, device: str = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._piano_model = None
        self._demucs_separator = None
        self._basic_pitch_model_path = None
        print(f"[Transcriber] Engine initialized on device: {self.device.upper()}")

    def _get_piano_model(self):
        if self._piano_model is None:
            from piano_transcription_inference import PianoTranscription

            checkpoint = os.environ.get("PIANO_TRANSCRIPTION_CHECKPOINT")
            if checkpoint:
                checkpoint_path = Path(checkpoint).expanduser()
                if not checkpoint_path.is_file() or checkpoint_path.stat().st_size < 160_000_000:
                    raise FileNotFoundError(f"Valid piano checkpoint not found: {checkpoint_path}")
            else:
                checkpoint_path = (
                    Path.home() / "piano_transcription_inference_data"
                    / "note_F1=0.9677_pedal_F1=0.9186.pth"
                )
                if not checkpoint_path.is_file() or checkpoint_path.stat().st_size < 160_000_000:
                    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                    partial = checkpoint_path.with_suffix(checkpoint_path.suffix + ".part")
                    url = (
                        "https://zenodo.org/record/4034264/files/"
                        "CRNN_note_F1%3D0.9677_pedal_F1%3D0.9186.pth?download=1"
                    )
                    print("[Transcriber] Downloading the 165 MB piano model checkpoint...")
                    try:
                        request = urllib.request.Request(url, headers={"User-Agent": "PianoMIDIStudio/1.0"})
                        with urllib.request.urlopen(request, timeout=60) as response, partial.open("wb") as target:
                            shutil.copyfileobj(response, target)
                        if partial.stat().st_size < 160_000_000:
                            raise RuntimeError("Downloaded piano checkpoint is incomplete.")
                        partial.replace(checkpoint_path)
                    except Exception:
                        partial.unlink(missing_ok=True)
                        raise
            print("[Transcriber] Loading piano-specialized onset/offset/velocity model...")
            self._piano_model = PianoTranscription(device=self.device, checkpoint_path=str(checkpoint_path))
        return self._piano_model

    def _get_demucs(self):
        if self._demucs_separator is None:
            from demucs.api import Separator

            print("[Transcriber] Loading Demucs htdemucs for source analysis/separation...")
            self._demucs_separator = Separator(model="htdemucs", device=self.device)
        return self._demucs_separator

    def _get_basic_pitch_path(self):
        if self._basic_pitch_model_path is None:
            from basic_pitch import ICASSP_2022_MODEL_PATH

            self._basic_pitch_model_path = ICASSP_2022_MODEL_PATH
        return self._basic_pitch_model_path

    @staticmethod
    def _stem_energy(stem) -> float:
        return float(torch.mean(stem.float() ** 2).sqrt().item())

    def _separate(self, audio_path: str):
        _, stems = self._get_demucs().separate_audio_file(audio_path)
        return stems

    def _release_demucs(self):
        self._demucs_separator = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _detect_source_mode(self, stems) -> str:
        """Route obvious vocal/drum mixes away from the solo-piano model."""
        mixture_energy = max(
            sum(self._stem_energy(stem) for stem in stems.values()), 1e-8
        )
        voice_and_drums = self._stem_energy(stems["vocals"]) + self._stem_energy(
            stems["drums"]
        )
        ratio = voice_and_drums / mixture_energy
        detected = "full_song" if ratio >= 0.12 else "piano_solo"
        print(
            f"[Transcriber] Auto source analysis: vocal/drum share {ratio:.1%}; "
            f"selected {detected}."
        )
        return detected

    def transcribe_piano_solo(self, audio_path: str, output_midi_path: str) -> str:
        """Use Transkun V2, an event-based piano transcription model."""
        try:
            import transkun  # noqa: F401
        except ModuleNotFoundError:
            print(
                "[Transcriber Warning] Transkun is not installed; falling back to "
                "the ByteDance/Kong piano model. Install requirements.txt for Transkun V2."
            )
            return self.transcribe_piano_solo_pedal(audio_path, output_midi_path)

        import librosa
        import moduleconf
        import pkg_resources
        from transkun.Data import writeMidi

        output = Path(output_midi_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        package = "transkun"
        checkpoint_path = pkg_resources.resource_filename(package, "pretrained/2.0.pt")
        config_path = pkg_resources.resource_filename(package, "pretrained/2.0.conf")
        config_manager = moduleconf.parseFromFile(config_path)
        model_class = config_manager["Model"].module.TransKun
        model = model_class(conf=config_manager["Model"].config).to(self.device)
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        state = checkpoint.get("best_state_dict", checkpoint.get("state_dict"))
        model.load_state_dict(state, strict=False)
        model.eval()

        # Decode with librosa so WAV/FLAC/MP3/M4A all use one path. Transkun's
        # packaged CLI forces MP3 decoding, which rejects other accepted types.
        audio, sample_rate = librosa.load(audio_path, sr=None, mono=False)
        if audio.ndim == 1:
            audio = audio[:, None]
        else:
            audio = audio.T
        if sample_rate != model.fs:
            audio = librosa.resample(
                audio, orig_sr=sample_rate, target_sr=model.fs, axis=0
            )
        audio_tensor = torch.from_numpy(np.asarray(audio, dtype=np.float32)).to(self.device)
        with torch.inference_mode():
            estimated_notes = model.transcribe(audio_tensor, discardSecondHalf=False)
        writeMidi(estimated_notes).write(str(output))
        del audio_tensor, model, checkpoint
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        print(f"[Transcriber] Transkun piano MIDI saved: {output}")
        return str(output)

    def transcribe_piano_solo_pedal(self, audio_path: str, output_midi_path: str) -> str:
        """Use ByteDance/Kong CRNN, including its sustain-pedal prediction."""
        import librosa
        from piano_transcription_inference import sample_rate

        print(f"[Transcriber] Loading piano recording at {sample_rate} Hz: {audio_path}")
        audio, _ = librosa.load(audio_path, sr=sample_rate, mono=True)
        output = Path(output_midi_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        self._get_piano_model().transcribe(audio, str(output))
        print(f"[Transcriber] Piano MIDI saved: {output}")
        return str(output)

    def transcribe_piano_with_accompaniment(
        self, audio_path: str, output_midi_path: str, stems=None
    ) -> str:
        """Remove vocal/drum-heavy material, then use the event-based piano model."""
        stems = stems or self._separate(audio_path)
        # htdemucs has no piano stem. ``other`` plus bass is therefore only a
        # best-effort harmonic mix; use this when piano is the intended source.
        piano_candidate = stems["other"] + stems["bass"]
        mono = piano_candidate.mean(dim=0).detach().cpu().numpy()
        # Demucs htdemucs outputs 44.1 kHz audio.
        import librosa
        from piano_transcription_inference import sample_rate

        mono = librosa.resample(
            mono.astype(np.float32), orig_sr=44100, target_sr=sample_rate
        )
        del stems, piano_candidate
        self._release_demucs()
        output = Path(output_midi_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        # Reuse the common Transkun inference path; the stem is temporarily
        # written at 16 kHz because its CLI decodes audio files itself.
        import soundfile as sf
        with tempfile.TemporaryDirectory(prefix="midi_piano_stem_") as temp_dir:
            stem_path = Path(temp_dir) / "piano_candidate.wav"
            sf.write(stem_path, mono, sample_rate)
            return self.transcribe_piano_solo(str(stem_path), str(output))

    def transcribe_full_song(self, audio_path: str, output_midi_path: str, stems=None,
                             arrangement_style="pop") -> str:
        """Recognize the song's chords and arrange them with its vocal lead."""
        try:
            from basic_pitch.inference import predict
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "El modo full_song requiere Basic Pitch y TensorFlow. "
                "En Windows usa Python 3.10/3.11 e instala requirements-full-song.txt."
            ) from exc
        from .piano_arranger import arrange_piano, recognize_chords

        stems = stems or self._separate(audio_path)
        vocals = stems["vocals"].detach().cpu()
        drums = stems["drums"].detach().cpu()
        del stems
        self._release_demucs()

        print("[Transcriber] Recognizing chord progression with the trained ensemble...")
        chords = recognize_chords(audio_path, self.device)

        output = Path(output_midi_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="midi_piano_") as temp_dir:
            vocal_path = Path(temp_dir) / "vocals.wav"
            sf.write(vocal_path, vocals.transpose(0, 1).numpy(), 44100)

            model_path = self._get_basic_pitch_path()
            print("[Transcriber] Transcribing lead/vocal line with Basic Pitch...")
            _, midi_vocals, _ = predict(
                str(vocal_path), model_or_model_path=model_path,
                onset_threshold=0.55, frame_threshold=0.40,
                minimum_note_length=75,
            )
            print("[Transcriber] Arranging the piano part...")
            arrange_piano(midi_vocals, chords, drums.transpose(0, 1).numpy(),
                          str(output), style=arrangement_style)
        return str(output)

    def transcribe(self, audio_path: str, output_midi_path: str, mode: str = "auto",
                   arrangement_style: str = "pop") -> str:
        if mode not in self.MODES:
            raise ValueError(f"Unknown mode {mode!r}. Choose one of: {', '.join(self.MODES)}")

        stems = None
        if mode == "auto":
            stems = self._separate(audio_path)
            mode = self._detect_source_mode(stems)
            if mode == "full_song":
                try:
                    from basic_pitch.inference import predict  # noqa: F401
                except ModuleNotFoundError:
                    print(
                        "[Transcriber Warning] Basic Pitch/TensorFlow no está disponible; "
                        "Auto usará la mezcla armónica con Transkun."
                    )
                    mode = "piano_with_accompaniment"
        if mode == "piano_solo":
            if stems is not None:
                del stems
                self._release_demucs()
            return self.transcribe_piano_solo(audio_path, output_midi_path)
        if mode == "piano_solo_pedal":
            return self.transcribe_piano_solo_pedal(audio_path, output_midi_path)
        if mode == "piano_with_accompaniment":
            return self.transcribe_piano_with_accompaniment(
                audio_path, output_midi_path, stems=stems
            )
        return self.transcribe_full_song(audio_path, output_midi_path, stems=stems,
                                         arrangement_style=arrangement_style)
