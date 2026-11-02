import os
import pretty_midi

class MidiProcessor:
    """
    Cleans, refines, and enhances MIDI files for piano visualization.
    Enables left-hand / right-hand separation (for 2-color falling notes like Rousseau),
    noise filtering, and velocity normalization.
    """
    def __init__(self, midi_path: str):
        self.midi_path = midi_path
        self.midi = pretty_midi.PrettyMIDI(midi_path)

    def filter_noise(self, min_velocity: int = 15, min_duration: float = 0.04):
        """
        Removes ghost notes (extremely soft or microsecond glitch clicks).
        """
        for instrument in self.midi.instruments:
            cleaned_notes = []
            for note in instrument.notes:
                duration = note.end - note.start
                if note.velocity >= min_velocity and duration >= min_duration:
                    cleaned_notes.append(note)
            instrument.notes = cleaned_notes

    def split_hands(self, split_pitch: int = 60) -> pretty_midi.PrettyMIDI:
        """
        Splits single-track piano notes into two separate tracks:
        - Track 1 (Left Hand / Bass): Pitches below split_pitch (Default C4 = 60)
        - Track 2 (Right Hand / Treble): Pitches equal or above split_pitch
        
        This enables visualizers (MIDIVisualizer, SeeMusic) to assign distinct colors
        (e.g., Rousseau's classic Blue for Left Hand and Gold/Cyan for Right Hand).
        """
        new_midi = pretty_midi.PrettyMIDI(initial_tempo=self.midi.estimate_tempo() or 120.0)

        left_hand = pretty_midi.Instrument(program=0, name="Left Hand (Bass)")
        right_hand = pretty_midi.Instrument(program=0, name="Right Hand (Treble)")

        all_notes = []
        for instrument in self.midi.instruments:
            all_notes.extend(instrument.notes)

        for note in all_notes:
            if note.pitch < split_pitch:
                left_hand.notes.append(note)
            else:
                right_hand.notes.append(note)

        # Copy control changes (sustain pedal CC#64, etc.) to both hands
        for instrument in self.midi.instruments:
            for cc in instrument.control_changes:
                left_hand.control_changes.append(cc)
                right_hand.control_changes.append(cc)

        new_midi.instruments.append(left_hand)
        new_midi.instruments.append(right_hand)
        return new_midi

    def save(self, output_path: str, split_hands: bool = True, min_velocity: int = 15):
        """
        Process and save the optimized MIDI file.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        self.filter_noise(min_velocity=min_velocity)
        
        if split_hands:
            processed_midi = self.split_hands()
        else:
            processed_midi = self.midi

        processed_midi.write(output_path)
        print(f"[MidiProcessor] Processed MIDI saved to: {output_path}")
        return output_path
