# Piano MIDI Studio

Aplicación local para convertir audio en MIDI, escuchar el resultado con MIDIVisualizer y renderizarlo como MP4. La calidad depende mucho de la fuente: una grabación de piano aislado se puede transcribir como interpretación de piano; una canción mezclada requiere una reducción aproximada y no se convierte automáticamente en una partitura exacta para piano.

## Modos

- **`auto`** (predeterminado): Demucs analiza la mezcla. Si detecta voz o batería prominentes, aplica el flujo de canción completa; si no, transcribe el audio original con Transkun. Esta detección es heurística, puede equivocarse y clasifica la fuente, no el género.
- **`piano_solo`**: recomendado para piano solo limpio. Usa Transkun V2, una alternativa más reciente que predice intervalos de notas y estima sus ataques, duraciones y velocidades.
- **`piano_solo_pedal`**: usa el modelo CRNN de ByteDance/Kong, que predice notas y pedal de sostenido. Es una alternativa para comparar cuando el pedal es importante.
- **`piano_with_accompaniment`**: separa con Demucs y transcribe la mezcla armónica con Transkun. Demucs no ofrece una pista de piano dedicada en el modelo estándar, por lo que otros instrumentos en esa mezcla pueden afectar el resultado.
- **`full_song`**: separa la voz con Demucs, transcribe su melodia con Basic Pitch y reconoce los acordes del audio original con el modelo entrenado lv-chordia. Genera un MIDI de dos manos con bajos, acordes, inversiones y nombres de acordes. La web permite elegir Pop, Balada, Vals, Arpegios o Acordes sostenidos. Es un arreglo aproximado que puede requerir revision musical.

Para la transcripción más fiel de una melodía de piano, usa una grabación limpia y elige `piano_solo`; compara con `piano_solo_pedal` si necesitas pedal explícito. Las métricas publicadas de Transkun V2 en MAESTRO son buenas, pero no predicen por sí solas el resultado en tus grabaciones y no demuestran superioridad para todos los estilos. Si la fuente es una canción completa, ninguna selección de género puede recuperar con certeza qué notas habría tocado un pianista; la separación de fuentes introduce errores y el MIDI debe revisarse.

## Instalación

El entorno activo de este proyecto es `.venv311` con Python 3.11.9. En este equipo la GPU detectada es una NVIDIA GeForce GTX 1660 SUPER. El paquete `transkun` incluye su checkpoint; el checkpoint ByteDance/Kong de aproximadamente 165 MB se descarga en el primer uso de `piano_solo_pedal` si no existe localmente. Si Transkun no está instalado, `piano_solo` avisa y usa ByteDance/Kong como alternativa.

```powershell
.\instalar_dependencias.bat
```

El instalador crea `.venv311`, instala PyTorch CUDA 12.4, los requisitos de `full_song` y Transkun. Instala Transkun sin `ncls`: esa dependencia se usa para preparación/evaluación de datasets y requiere compilador C++ en Windows, pero no interviene en la inferencia de este proyecto. Para comandos directos, usa Python de `.venv311\Scripts\python.exe`.

El modo `full_song` usa Basic Pitch; por eso sus dependencias están en `requirements-full-song.txt` y el entorno necesita Python 3.10/3.11.

El checkpoint ByteDance/Kong se puede fijar con `PIANO_TRANSCRIPTION_CHECKPOINT`. En Windows, FFmpeg debe estar disponible en `PATH` para que Demucs pueda leer formatos comunes y para combinar audio al renderizar video.

## Uso por consola

```powershell
.\.venv311\Scripts\python.exe transcribe_cli.py "ruta\a\piano.wav" --mode piano_solo
.\.venv311\Scripts\python.exe transcribe_cli.py "ruta\a\piano.wav" --mode piano_solo_pedal
.\.venv311\Scripts\python.exe transcribe_cli.py "ruta\a\cancion.mp3" --mode auto
.\.venv311\Scripts\python.exe transcribe_cli.py "ruta\a\cancion.mp3" --mode full_song --arrangement-style block --play
.\.venv311\Scripts\python.exe transcribe_cli.py "ruta\a\piano.wav" --mode piano_solo --render-video
```

El MIDI se guarda en `output/<nombre>.mid` o en la ruta indicada con `--output`. Las opciones son `auto`, `piano_solo`, `piano_solo_pedal`, `piano_with_accompaniment` y `full_song`.

## Interfaz web

Ejecuta `iniciar_web.bat` o:

```powershell
.\.venv311\Scripts\python.exe web_app.py
```

Abre `http://localhost:8000`. Los audios subidos y los resultados se guardan en `uploads/` y `output/`. En `full_song` puedes descargar tanto el MIDI como la lista de acordes detectados para revisar dónde cambia la armonía. El reproductor y el renderizador necesitan `tools/MIDIVisualizer/MIDIVisualizer.exe`.

## Componentes

- `src/transcriber.py`: selección del flujo y transcripción.
- `src/visualizer_bridge.py`: reproducción y exportación MP4 con MIDIVisualizer/FFmpeg.
- `src/midi_processor.py`: utilidades MIDI independientes; no forma parte de los flujos principales de transcripción.
- `transcribe_cli.py`: interfaz de consola.
- `web_app.py`: interfaz web local basada en FastAPI.

## Límites conocidos

La transcripción automática no equivale a una transcripción musical editada por una persona. El modelo piano-especializado es la ruta correcta para piano aislado; Basic Pitch es generalista y se usa aquí solo para la reducción de mezclas. En audio polifónico mixto son comunes las notas omitidas/falsas, los ataques desalineados y las duraciones afectadas por reverb o pedal. Evalúa resultados comparándolos con el audio original.

Referencias: [Transkun V2 y sus modelos publicados](https://github.com/Yujia-Yan/Transkun), [modelo de piano ByteDance/Kong](https://arxiv.org/abs/2010.01815), [Basic Pitch](https://github.com/spotify/basic-pitch), [Demucs y sus fuentes separadas](https://github.com/facebookresearch/demucs).

El detector de acordes incluido en `vendor/lv-chordia` conserva su licencia MIT y cinco pesos preentrenados. El modo `full_song` requiere `pydub`, incluido en `requirements-full-song.txt`. Su salida adicional `<nombre>.chords.json` contiene la progresion detectada para revisar cada acorde y su tiempo.

Investigacion de piano-cover: [PiCoGen (2024), extraccion de lead sheet y generacion simbolica](https://arxiv.org/abs/2407.20883), [Pop2Piano (2023), generacion directa de covers pop](https://arxiv.org/abs/2211.00895), [AMT-APC (2024), ajuste fino de transcripcion para arreglos](https://arxiv.org/abs/2409.14086), [Large-Vocabulary Chord Recognition (ISMIR 2019)](https://archives.ismir.net/ismir2019/paper/000078.pdf).
