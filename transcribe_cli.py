import sys
from pathlib import Path
import argparse

# Print immediate feedback before heavy CUDA/torch DLL loading
print("=" * 60)
print("  PIANO MIDI STUDIO - AUDIO TRANSCRIPTION")
print("=" * 60)
print("[1/4] Inicializando motor de transcripción...")

from src.transcriber import AudioToMidiTranscriber
from src.visualizer_bridge import VisualizerBridge

def main():
    parser = argparse.ArgumentParser(
        description="Transcribe piano recordings or create rough piano reductions from full songs."
    )
    parser.add_argument(
        "audio_path",
        type=str,
        help="Ruta al archivo de audio (.mp3, .wav, .flac, etc.)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Ruta donde guardar el MIDI (por defecto: output/<nombre>.mid)"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["auto", "piano_solo", "piano_solo_pedal", "piano_with_accompaniment", "full_song"],
        default="auto",
        help=("Tipo de fuente: auto, piano_solo (Transkun), piano_solo_pedal (ByteDance), "
              "piano_with_accompaniment o full_song (reduccion aproximada)")
    )
    parser.add_argument(
        "--arrangement-style",
        choices=["block", "arpeggio", "pop", "ballad", "waltz"],
        default="pop",
        help="Acompañamiento para full_song: acordes sostenidos o arpegios",
    )
    parser.add_argument(
        "--play",
        action="store_true",
        help="Abrir el visualizador con notas cayendo en tiempo real"
    )
    parser.add_argument(
        "--render-video",
        action="store_true",
        help="Renderizar directamente a video MP4 a 60 FPS con audio sincronizado"
    )

    args = parser.parse_args()

    audio_file = Path(args.audio_path)
    if not audio_file.is_file():
        print(f"\n[Error] El archivo de audio no existe o no es un archivo: {audio_file}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    if args.output:
        output_file = Path(args.output)
    else:
        output_file = output_dir / f"{audio_file.stem}.mid"

    print(f"\nArchivo de Entrada: {audio_file.name}")
    print(f"Salida MIDI:        {output_file}")
    print(f"Modo:               {args.mode.upper()}")
    print("-" * 60)

    try:
        transcriber = AudioToMidiTranscriber()
        transcriber.transcribe(str(audio_file), str(output_file), mode=args.mode,
                               arrangement_style=args.arrangement_style)

        print("[4/4] Transcripcion finalizada.")
        print("=" * 60)
        print("  TU ARCHIVO MIDI ESTA LISTO:")
        print(f"  -> {output_file.resolve()}")
        print("=" * 60)

        # Render Video
        if args.render_video:
            bridge = VisualizerBridge()
            video_path = output_dir / f"{audio_file.stem}.mp4"
            print("\n[Video] Renderizando video MP4 con efectos de particulas y audio sincronizado...")
            bridge.render_video(str(output_file), str(video_path), audio_path=str(audio_file))
            print(f"[Video] Video guardado en: {video_path.resolve()}")

        # Live Playback
        if args.play:
            bridge = VisualizerBridge()
            print("\n[Visualizador] Lanzando reproductor en pantalla...")
            bridge.play(str(output_file))

    except Exception as e:
        print(f"\n[Error en el proceso]: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
