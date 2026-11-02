import numpy as np
import soundfile as sf
from pathlib import Path

def generate_piano_chord_progression(output_path: str = "test_samples/test_piano.wav"):
    """
    Generates a realistic synthetic piano-like audio test sample:
    Chord progression: C Major -> G Major -> A Minor -> F Major
    With acoustic decay and harmonics.
    """
    sr = 16000
    chord_duration = 1.5  # seconds per chord
    chords = [
        # (Bass notes, Treble notes)
        ([36, 48], [60, 64, 67, 72]),  # C Major: C2, C3, C4, E4, G4, C5
        ([31, 43], [59, 62, 67, 71]),  # G Major: G1, G2, B3, D4, G4, B4
        ([33, 45], [57, 60, 64, 69]),  # A Minor: A1, A2, A3, C4, E4, A4
        ([29, 41], [53, 57, 60, 65]),  # F Major: F1, F2, F3, A3, C4, F4
    ]

    def midi_to_freq(m):
        return 440.0 * (2.0 ** ((m - 69) / 12.0))

    full_audio = []

    for bass_notes, treble_notes in chords:
        t = np.linspace(0, chord_duration, int(sr * chord_duration), False)
        chord_wave = np.zeros_like(t)

        for note in bass_notes + treble_notes:
            f0 = midi_to_freq(note)
            # Add harmonics with exponential decay for piano-like timbre
            decay = np.exp(-3.5 * t)
            harmonics = (
                1.0 * np.sin(2 * np.pi * f0 * t) +
                0.5 * np.sin(2 * np.pi * 2 * f0 * t) +
                0.25 * np.sin(2 * np.pi * 3 * f0 * t) +
                0.12 * np.sin(2 * np.pi * 4 * f0 * t)
            )
            chord_wave += harmonics * decay

        full_audio.append(chord_wave)

    audio_signal = np.concatenate(full_audio)
    # Normalize
    audio_signal = audio_signal / np.max(np.abs(audio_signal)) * 0.9

    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, audio_signal, sr)
    print(f"Generated test audio at: {output_path} (Duration: {len(audio_signal)/sr:.1f}s)")
    return output_path

if __name__ == "__main__":
    generate_piano_chord_progression()
