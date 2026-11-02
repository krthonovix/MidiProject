"""Piano arrangement from a vocal melody and learned chord recognition."""

from itertools import product
import json
from pathlib import Path
import sys

import librosa
import numpy as np
import pretty_midi


VENDOR = Path(__file__).resolve().parent.parent / "vendor" / "lv-chordia"


def _chord_model():
    if not (VENDOR / "weights").is_dir():
        raise RuntimeError("Faltan los pesos del modelo de acordes en vendor/lv-chordia.")
    location = str(VENDOR)
    if location not in sys.path:
        sys.path.insert(0, location)
    from lv_chordia.chord_recognition import chord_recognition
    from lv_chordia.complex_chord import Chord

    return chord_recognition, Chord


def recognize_chords(audio_path: str, device: str) -> list[dict]:
    """Recognize time-aligned chords in the original full mix."""
    chord_recognition, _ = _chord_model()
    return chord_recognition(str(Path(audio_path).resolve()),
                             chord_dict_name="submission", device=device)


def _chord_pitches(name: str):
    """Return root, bass, and at most three useful left-hand chord tones."""
    _, Chord = _chord_model()
    chord = Chord(name)
    if chord.root < 0:
        return None
    triads = {
        1: (0, 4, 7), 2: (0, 3, 7), 3: (0, 5, 7),
        4: (0, 2, 7), 5: (0, 3, 6), 6: (0, 4, 8),
    }
    intervals = triads.get(chord.triad, (0, 4, 7))
    seventh = {1: 11, 2: 10, 3: 9}.get(chord.seventh)
    ninth = {1: 14, 2: 15, 3: 13}.get(chord.ninth)
    if ninth is not None and seventh is not None:
        harmony = (intervals[1], seventh, ninth)
    elif seventh is not None:
        harmony = (intervals[1], intervals[2], seventh)
    else:
        harmony = intervals
    return chord.root, chord.bass, tuple((chord.root + i) % 12 for i in harmony)


def _select_voicing(pitch_classes: tuple[int, ...], previous=None) -> list[int]:
    choices = [[pitch for pitch in range(43, 61) if pitch % 12 == pc]
               for pc in pitch_classes]
    possible = []
    for notes in product(*choices):
        pitches = sorted(notes)
        if len(set(pitches)) != len(pitches) or pitches[-1] - pitches[0] > 15:
            continue
        movement = (sum(abs(a - b) for a, b in zip(previous, pitches))
                    if previous and len(previous) == len(pitches) else 0)
        cost = movement + 0.12 * (pitches[-1] - pitches[0]) + 0.10 * abs(np.mean(pitches) - 52)
        possible.append((cost, pitches))
    if not possible:
        return sorted(48 + pc for pc in pitch_classes)[:3]
    return min(possible, key=lambda item: item[0])[1]


def _clean_melody(melody_midi: pretty_midi.PrettyMIDI) -> list[pretty_midi.Note]:
    candidates = [note for instrument in melody_midi.instruments for note in instrument.notes
                  if note.end - note.start >= 0.075 and 48 <= note.pitch <= 88]
    kept = []
    for note in sorted(candidates, key=lambda value: (value.start, -value.velocity)):
        overlapping = [prev for prev in kept
                       if min(note.end, prev.end) - max(note.start, prev.start) > 0.08]
        if overlapping and max(prev.velocity for prev in overlapping) >= note.velocity:
            continue
        kept = [prev for prev in kept if prev not in overlapping]
        kept.append(note)

    merged = []
    for note in sorted(kept, key=lambda value: value.start):
        if merged and note.pitch == merged[-1].pitch and 0 <= note.start - merged[-1].end <= 0.075:
            merged[-1].end = note.end
            merged[-1].velocity = max(merged[-1].velocity, note.velocity)
        else:
            merged.append(pretty_midi.Note(
                pitch=note.pitch, velocity=max(48, min(108, note.velocity)),
                start=note.start, end=note.end))
    for current, following in zip(merged, merged[1:]):
        gap = following.start - current.end
        if 0.025 < gap < 0.11:
            current.end = following.start - 0.015
    return merged


def _beat_duration(drums_audio: np.ndarray, sample_rate: int = 44100) -> float:
    if drums_audio.ndim == 2:
        drums_audio = drums_audio.mean(axis=1)
    _, frames = librosa.beat.beat_track(y=drums_audio.astype(np.float32),
                                        sr=sample_rate, hop_length=512, trim=False)
    if len(frames) < 2:
        return 0.5
    beat_times = librosa.frames_to_time(frames, sr=sample_rate, hop_length=512)
    return float(np.clip(np.median(np.diff(beat_times)), 0.25, 1.0))


def _add_notes(track: pretty_midi.Instrument, pitches, start: float, end: float,
               velocity: int):
    if end - start < 0.06:
        return
    for pitch in pitches:
        track.notes.append(pretty_midi.Note(pitch=int(pitch), velocity=velocity,
                                            start=float(start), end=float(end)))


def arrange_piano(melody_midi: pretty_midi.PrettyMIDI, chords: list[dict],
                  drums_audio: np.ndarray, output_path: str, style: str = "pop") -> str:
    """Write a two-hand piano MIDI with chord symbols and compact voicings."""
    if style not in {"block", "arpeggio", "pop", "ballad", "waltz"}:
        raise ValueError(f"Patron de acompanamiento desconocido: {style}")
    beat = _beat_duration(drums_audio)
    midi = pretty_midi.PrettyMIDI(initial_tempo=60.0 / beat)
    # Fast pop beats often feel more natural with a half-time piano pattern.
    accompaniment_pulse = beat * 2 if beat < 0.43 else beat
    right = pretty_midi.Instrument(program=0, name="Mano derecha - melodia")
    left = pretty_midi.Instrument(program=0, name="Mano izquierda - acordes")
    right.notes = _clean_melody(melody_midi)
    previous_voicing = None

    for segment in chords:
        start = max(0.0, float(segment["start_time"]))
        end = float(segment["end_time"])
        if end - start < 0.12:
            continue
        label = segment["chord"]
        parsed = _chord_pitches(label)
        if parsed is None:
            continue
        _, bass_pc, harmony_pcs = parsed
        bass = 36 + bass_pc
        voicing = _select_voicing(harmony_pcs, previous_voicing)
        previous_voicing = voicing
        midi.text_events.append(pretty_midi.Text(text=label, time=start))
        if style in {"pop", "ballad", "block"}:
            left.control_changes.append(pretty_midi.ControlChange(
                number=64, value=110, time=start))
            left.control_changes.append(pretty_midi.ControlChange(
                number=64, value=0, time=max(start + 0.08, end - 0.04)))

        if style == "block":
            move = min(beat * 0.28, 0.12)
            _add_notes(left, (bass,), start, min(end, start + move), 77)
            _add_notes(left, voicing, start + move, end - 0.03, 67)
        elif style == "arpeggio":
            pattern = [bass] + voicing + list(reversed(voicing[1:-1]))
            step = beat / 2
            count = int(np.ceil((end - start) / step))
            for index in range(count):
                t = start + index * step
                _add_notes(left, (pattern[index % len(pattern)],), t,
                           min(end, t + step * 0.86), 74 if index % len(pattern) == 0 else 64)
        else:
            pulse = beat if style == "waltz" else accompaniment_pulse
            count = int(np.ceil((end - start) / pulse))
            for index in range(count):
                t = start + index * pulse
                if t >= end:
                    break
                if style == "waltz":
                    is_bass = index % 3 == 0
                else:
                    is_bass = index % 2 == 0
                pitches = (bass,) if is_bass else voicing
                velocity = 76 if is_bass else (61 if style == "ballad" else 67)
                length = pulse * (0.90 if style == "ballad" else 0.78)
                _add_notes(left, pitches, t, min(end, t + length), velocity)

    if not right.notes and not left.notes:
        raise RuntimeError("No se detectaron notas de melodia ni acordes en el audio.")
    midi.instruments = [right, left]
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    midi.write(str(output))
    output.with_suffix(".chords.json").write_text(
        json.dumps(chords, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(output)
