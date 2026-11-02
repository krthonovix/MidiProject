import shutil
import threading
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse

# Initialize transcriber global instance
transcriber_instance = None
TRANSCRIPTION_LOCK = threading.Lock()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global transcriber_instance
    print("=" * 60)
    print(" [Web Server] Iniciando servidor web de Piano MIDI...")
    print(" [Web Server] Cargando motor de transcripción...")
    from src.transcriber import AudioToMidiTranscriber
    transcriber_instance = AudioToMidiTranscriber()
    print(f" [Web Server] Motor listo en {transcriber_instance.device.upper()}.")
    print("=" * 60)
    yield
    print(" [Web Server] Cerrando servidor.")

app = FastAPI(title="Piano MIDI Studio", lifespan=lifespan)

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("output")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

HTML_CONTENT = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Piano MIDI Studio | Audio a MIDI Rousseau</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #07090e;
            --card-bg: rgba(18, 24, 38, 0.7);
            --card-border: rgba(255, 255, 255, 0.08);
            --primary: #8b5cf6;
            --primary-glow: rgba(139, 92, 246, 0.4);
            --cyan: #06b6d4;
            --cyan-glow: rgba(6, 182, 212, 0.4);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --success: #10b981;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        body {
            background-color: var(--bg);
            background-image: 
                radial-gradient(circle at 20% 20%, rgba(139, 92, 246, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 80% 80%, rgba(6, 182, 212, 0.12) 0%, transparent 45%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 20px;
        }

        .container {
            max-width: 860px;
            width: 100%;
        }

        header {
            text-align: center;
            margin-bottom: 35px;
        }

        .badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(139, 92, 246, 0.15);
            border: 1px solid rgba(139, 92, 246, 0.3);
            color: #c4b5fd;
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 0.82rem;
            font-weight: 600;
            margin-bottom: 16px;
            letter-spacing: 0.5px;
        }

        .badge span {
            width: 8px;
            height: 8px;
            background: #10b981;
            border-radius: 50%;
            box-shadow: 0 0 10px #10b981;
        }

        h1 {
            font-size: 2.8rem;
            font-weight: 800;
            background: linear-gradient(135deg, #ffffff 30%, #c4b5fd 70%, #38bdf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 12px;
            letter-spacing: -0.5px;
        }

        p.subtitle {
            color: var(--text-muted);
            font-size: 1.05rem;
            max-width: 620px;
            margin: 0 auto;
        }

        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 32px;
            backdrop-filter: blur(20px);
            box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.5);
            margin-bottom: 25px;
            transition: all 0.3s ease;
        }

        .dropzone {
            border: 2px dashed rgba(139, 92, 246, 0.4);
            border-radius: 18px;
            padding: 45px 20px;
            text-align: center;
            cursor: pointer;
            background: rgba(139, 92, 246, 0.03);
            transition: all 0.3s ease;
            position: relative;
        }

        .dropzone:hover, .dropzone.dragover {
            border-color: var(--primary);
            background: rgba(139, 92, 246, 0.08);
            box-shadow: 0 0 30px var(--primary-glow);
            transform: translateY(-2px);
        }

        .drop-icon {
            font-size: 48px;
            margin-bottom: 14px;
            display: inline-block;
            filter: drop-shadow(0 0 15px var(--primary-glow));
        }

        .drop-title {
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 6px;
        }

        .drop-desc {
            font-size: 0.9rem;
            color: var(--text-muted);
        }

        input[type="file"] {
            display: none;
        }

        .file-info {
            display: none;
            margin-top: 15px;
            padding: 12px 18px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            align-items: center;
            justify-content: space-between;
        }

        .file-name {
            font-weight: 600;
            color: #38bdf8;
            font-size: 0.95rem;
        }

        /* Mode Selector */
        .mode-section {
            margin: 22px 0 15px;
        }

        .mode-label {
            font-size: 0.9rem;
            font-weight: 700;
            color: #c4b5fd;
            margin-bottom: 10px;
            display: block;
        }

        .mode-selector {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }

        .mode-card {
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: rgba(255, 255, 255, 0.02);
            padding: 16px;
            border-radius: 14px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .mode-card.active {
            border-color: var(--primary);
            background: rgba(139, 92, 246, 0.12);
            box-shadow: 0 0 20px rgba(139, 92, 246, 0.2);
        }

        .mode-card h4 {
            font-size: 0.95rem;
            font-weight: 700;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .mode-card p {
            font-size: 0.8rem;
            color: var(--text-muted);
            line-height: 1.4;
        }

        .btn-convert {
            width: 100%;
            background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
            color: white;
            border: none;
            padding: 18px;
            font-size: 1.1rem;
            font-weight: 700;
            border-radius: 16px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 10px 25px -5px var(--primary-glow);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-top: 20px;
        }

        .btn-convert:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 15px 30px -5px var(--primary-glow);
            filter: brightness(1.1);
        }

        .btn-convert:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        #progressCard {
            display: none;
            text-align: center;
            padding: 30px;
        }

        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid rgba(139, 92, 246, 0.2);
            border-top: 4px solid var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 16px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .status-msg {
            font-size: 1.1rem;
            font-weight: 700;
            color: #c4b5fd;
        }

        #resultsCard {
            display: none;
            border-color: rgba(16, 185, 129, 0.3);
            background: linear-gradient(180deg, rgba(16, 185, 129, 0.05) 0%, rgba(18, 24, 38, 0.8) 100%);
        }

        .results-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 20px;
        }

        .results-header h3 {
            font-size: 1.35rem;
            color: #34d399;
        }

        .action-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px;
            margin-top: 20px;
        }

        .btn-action {
            padding: 15px 20px;
            border-radius: 14px;
            font-weight: 700;
            font-size: 0.95rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.2s ease;
            text-decoration: none;
        }

        .btn-download-midi {
            background: #10b981;
            color: #022c22;
            border: none;
        }

        .btn-download-midi:hover {
            background: #34d399;
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.4);
        }

        .btn-play-live {
            background: rgba(6, 182, 212, 0.2);
            border: 1px solid var(--cyan);
            color: #38bdf8;
        }

        .btn-play-live:hover {
            background: rgba(6, 182, 212, 0.3);
            box-shadow: 0 0 20px var(--cyan-glow);
        }

        .btn-render-video {
            grid-column: span 2;
            background: linear-gradient(135deg, #f59e0b 0%, #ea580c 100%);
            color: white;
            border: none;
        }

        .btn-render-video:hover {
            filter: brightness(1.1);
            box-shadow: 0 0 25px rgba(245, 158, 11, 0.4);
        }

        .seemusic-tip {
            margin-top: 22px;
            padding: 16px 20px;
            background: rgba(255, 255, 255, 0.03);
            border-left: 3px solid #8b5cf6;
            border-radius: 0 12px 12px 0;
            font-size: 0.88rem;
            color: var(--text-muted);
            line-height: 1.5;
        }

        .seemusic-tip strong {
            color: #c4b5fd;
        }
    </style>
</head>
<body>

<div class="container">
    <header>
        <div class="badge">
            <span></span> TRANSCRIPCIÓN LOCAL
        </div>
        <h1>Audio to Piano MIDI Studio</h1>
        <p class="subtitle">Convierte grabaciones de piano a MIDI y explora reducciones aproximadas de canciones completas.</p>
    </header>

    <div class="card" id="uploadCard">
        <div class="dropzone" id="dropzone">
            <div class="drop-icon">🎹</div>
            <div class="drop-title">Arrastra tu canción aquí</div>
            <div class="drop-desc">O haz clic para seleccionar (.mp3, .wav, .flac, .m4a)</div>
            <input type="file" id="fileInput" accept=".mp3,.wav,.flac,.ogg,.m4a">
        </div>

        <div class="file-info" id="fileInfo">
            <span class="file-name" id="fileName">cancion.mp3</span>
            <span id="fileSize" style="color: var(--text-muted); font-size: 0.85rem;"></span>
        </div>

        <div class="mode-section">
            <label class="mode-label">MODO DE TRANSCRIPCIÓN</label>
            <div class="mode-selector">
                <div class="mode-card active" id="modeAuto" onclick="selectMode('auto')">
                    <h4>✨ Automático</h4>
                    <p>Analiza si hay voz o batería destacadas. Añade tiempo de separación y puede equivocarse; puedes elegir la fuente manualmente.</p>
                </div>
                <div class="mode-card" id="modeSolo" onclick="selectMode('piano_solo')">
                    <h4>🎹 Piano solo (Transkun)</h4>
                    <p>Recomendado para piano limpio; estima ataques, duración y velocidad de cada nota.</p>
                </div>
                <div class="mode-card" id="modeSoloPedal" onclick="selectMode('piano_solo_pedal')">
                    <h4>🎹 Piano solo (pedal)</h4>
                    <p>Modelo ByteDance/Kong, opción alternativa con detección explícita del pedal sostenido.</p>
                </div>
                <div class="mode-card" id="modeAccompaniment" onclick="selectMode('piano_with_accompaniment')">
                    <h4>🎼 Piano con acompañamiento</h4>
                    <p>Separa voz/batería y transcribe la mezcla armónica con el modelo de piano.</p>
                </div>
                <div class="mode-card" id="modeFullSong" onclick="selectMode('full_song')">
                    <h4>🎧 Canción completa → piano</h4>
                    <p>Extrae la melodía vocal y reconoce los acordes de la canción con un modelo entrenado. Crea un arreglo de dos manos.</p>
                </div>
            </div>
            <div id="arrangementOptions" style="display:none; margin-top:14px;">
                <label for="arrangementStyle" class="mode-label">ACOMPAÑAMIENTO</label>
                <select id="arrangementStyle" style="width:100%; padding:12px; border-radius:10px;">
                    <option value="pop">Pop (bajo + acordes alternados)</option>
                    <option value="ballad">Balada</option>
                    <option value="waltz">Vals</option>
                    <option value="arpeggio">Arpegios</option>
                    <option value="block">Acordes sostenidos</option>
                </select>
            </div>
        </div>

        <button class="btn-convert" id="btnConvert" disabled>
            ✨ Iniciar transcripción
        </button>
    </div>

    <!-- Progress Card -->
    <div class="card" id="progressCard">
        <div class="spinner"></div>
        <div class="status-msg" id="statusMsg">Analizando la fuente de audio...</div>
        <p id="statusSub" style="color: var(--text-muted); font-size: 0.85rem; margin-top: 8px;">
            El tiempo depende de la duración del archivo y del modo elegido.
        </p>
    </div>

    <!-- Results Card -->
    <div class="card" id="resultsCard">
        <div class="results-header">
            <div style="font-size: 32px;">🎉</div>
            <div>
                <h3>Transcripción lista</h3>
                <p id="notesSummary" style="color: var(--text-muted); font-size: 0.9rem;">
                    MIDI generado con el modo seleccionado.
                </p>
            </div>
        </div>

        <div class="action-grid">
            <a href="#" class="btn-action btn-download-midi" id="btnDownloadMidi" download>
                📥 Descargar Archivo MIDI (.mid)
            </a>
            <a href="#" class="btn-action btn-download-midi" id="btnDownloadChords" download style="display:none;">
                Descargar acordes detectados (.json)
            </a>
            <button class="btn-action btn-play-live" id="btnPlayLive">
                ▶️ Abrir Visualizador en Pantalla
            </button>
            <button class="btn-action btn-render-video" id="btnRenderVideo">
                🎥 Renderizar Video MP4 (60 FPS con Neón y Audio Sincronizado)
            </button>
        </div>

        <div id="videoRenderStatus" style="display: none; margin-top: 15px; text-align: center; color: #f59e0b; font-weight: 600; font-size: 0.92rem;">
            ⏳ Renderizando video y sincronizando pista de audio...
        </div>

        <div class="seemusic-tip">
            💡 Abre el MIDI en SeeMusic o Synthesia para revisarlo y personalizar su visualización.
        </div>
    </div>
</div>

<script>
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const btnConvert = document.getElementById('btnConvert');
    const uploadCard = document.getElementById('uploadCard');
    const progressCard = document.getElementById('progressCard');
    const resultsCard = document.getElementById('resultsCard');
    const statusMsg = document.getElementById('statusMsg');
    const statusSub = document.getElementById('statusSub');
    const btnDownloadMidi = document.getElementById('btnDownloadMidi');
    const btnDownloadChords = document.getElementById('btnDownloadChords');
    const btnPlayLive = document.getElementById('btnPlayLive');
    const btnRenderVideo = document.getElementById('btnRenderVideo');
    const videoRenderStatus = document.getElementById('videoRenderStatus');
    const notesSummary = document.getElementById('notesSummary');

    let selectedFile = null;
    let selectedMode = 'auto';
    let currentMidiFilename = null;
    let currentAudioFilename = null;

    function selectMode(mode) {
        selectedMode = mode;
        document.getElementById('modeAuto').classList.toggle('active', mode === 'auto');
        document.getElementById('modeSolo').classList.toggle('active', mode === 'piano_solo');
        document.getElementById('modeSoloPedal').classList.toggle('active', mode === 'piano_solo_pedal');
        document.getElementById('modeAccompaniment').classList.toggle('active', mode === 'piano_with_accompaniment');
        document.getElementById('modeFullSong').classList.toggle('active', mode === 'full_song');
        document.getElementById('arrangementOptions').style.display = mode === 'full_song' ? 'block' : 'none';
    }

    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleFileSelect(fileInput.files[0]);
        }
    });

    function handleFileSelect(file) {
        selectedFile = file;
        fileName.textContent = file.name;
        fileSize.textContent = (file.size / (1024 * 1024)).toFixed(2) + ' MB';
        fileInfo.style.display = 'flex';
        btnConvert.disabled = false;
        resultsCard.style.display = 'none';
    }

    btnConvert.addEventListener('click', async () => {
        if (!selectedFile) return;

        const formData = new FormData();
        formData.append('audio_file', selectedFile);
        formData.append('mode', selectedMode);
        formData.append('arrangement_style', document.getElementById('arrangementStyle').value);

        uploadCard.style.opacity = '0.5';
        btnConvert.disabled = true;
        progressCard.style.display = 'block';
        resultsCard.style.display = 'none';

        if (selectedMode === 'auto' || selectedMode === 'full_song' || selectedMode === 'piano_with_accompaniment') {
            statusMsg.textContent = 'Analizando/separando fuentes de audio...';
            statusSub.textContent = selectedMode === 'full_song'
                ? 'Generando una reducción aproximada de la canción para piano...'
                : 'Si la grabación es piano solo, se usará el modelo especializado de piano.';
        } else {
            statusMsg.textContent = selectedMode === 'piano_solo_pedal'
                ? 'Analizando piano con predicción de pedal...'
                : 'Analizando piano con Transkun...';
            statusSub.textContent = selectedMode === 'piano_solo_pedal'
                ? 'Detectando notas, velocidades y pedal de sostenido...'
                : 'Detectando ataques, duraciones y velocidades de las notas...';
        }

        try {
            const response = await fetch('/api/transcribe', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Error en la transcripción');
            }

            const data = await response.json();
            currentMidiFilename = data.midi_filename;
            currentAudioFilename = data.audio_filename;
            notesSummary.textContent = selectedMode === 'full_song'
                ? 'Reducción aproximada desde la mezcla; revisa las notas contra el audio.'
                : selectedMode === 'piano_with_accompaniment'
                    ? 'Transcripción de la mezcla armónica con el modelo de piano.'
                    : selectedMode === 'piano_solo_pedal'
                        ? 'Transcripción con el modelo ByteDance/Kong y predicción explícita del pedal.'
                    : selectedMode === 'auto'
                        ? 'El modo automático eligió la ruta según la presencia de voz y batería.'
                        : 'Transcripción de piano con Transkun: ataques, duración y velocidad estimados.';

            // Update UI
            progressCard.style.display = 'none';
            resultsCard.style.display = 'block';
            uploadCard.style.opacity = '1';
            btnConvert.disabled = false;

            btnDownloadMidi.href = `/download/midi/${encodeURIComponent(currentMidiFilename)}`;
            btnDownloadMidi.setAttribute('download', currentMidiFilename);
            btnDownloadChords.style.display = data.chords_filename ? '' : 'none';
            if (data.chords_filename) {
                btnDownloadChords.href = `/download/chords/${encodeURIComponent(data.chords_filename)}`;
                btnDownloadChords.setAttribute('download', data.chords_filename);
            }

        } catch (error) {
            alert('Error: ' + error.message);
            progressCard.style.display = 'none';
            uploadCard.style.opacity = '1';
            btnConvert.disabled = false;
        }
    });

    btnPlayLive.addEventListener('click', async () => {
        if (!currentMidiFilename) return;
        try {
            const res = await fetch('/api/play-live', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ midi_filename: currentMidiFilename })
            });
            const data = await res.json();
            if (data.status !== 'started') {
                alert('No se pudo abrir el visualizador');
            }
        } catch (e) {
            alert('Error al abrir el visualizador: ' + e);
        }
    });

    btnRenderVideo.addEventListener('click', async () => {
        if (!currentMidiFilename) return;
        videoRenderStatus.style.display = 'block';
        videoRenderStatus.innerHTML = '⏳ Renderizando video a 60 FPS y sincronizando audio con FFmpeg...';
        btnRenderVideo.disabled = true;

        try {
            const res = await fetch('/api/render-video', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ 
                    midi_filename: currentMidiFilename,
                    audio_filename: currentAudioFilename
                })
            });
            const data = await res.json();
            if (data.video_filename) {
                videoRenderStatus.innerHTML = `✅ ¡Video listo con audio sincronizado! <a href="/download/video/${encodeURIComponent(data.video_filename)}" download style="color:#34d399; text-decoration:underline; font-weight:700;">Descargar ${data.video_filename}</a>`;
            } else {
                videoRenderStatus.textContent = 'Error al renderizar el video';
            }
        } catch (e) {
            videoRenderStatus.textContent = 'Error: ' + e;
        } finally {
            btnRenderVideo.disabled = false;
        }
    });
</script>

</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML_CONTENT

@app.post("/api/transcribe")
def transcribe_audio(
    audio_file: UploadFile = File(...),
    mode: str = Form("auto"),
    arrangement_style: str = Form("pop")
):
    global transcriber_instance
    if transcriber_instance is None:
        raise HTTPException(status_code=500, detail="El motor de transcripción aún se está inicializando.")

    allowed_modes = {"auto", "piano_solo", "piano_solo_pedal", "piano_with_accompaniment", "full_song"}
    if mode not in allowed_modes:
        raise HTTPException(status_code=400, detail="Modo de transcripción no válido")
    original_name = Path(audio_file.filename or "audio").name
    if arrangement_style not in {"block", "arpeggio", "pop", "ballad", "waltz"}:
        raise HTTPException(status_code=400, detail="Invalid accompaniment pattern")
    suffix = Path(original_name).suffix.lower()
    if suffix not in {".mp3", ".wav", ".flac", ".m4a", ".ogg"}:
        raise HTTPException(status_code=400, detail="Formato no admitido")
    import uuid
    file_token = uuid.uuid4().hex
    file_path = UPLOAD_DIR / f"{file_token}{suffix}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(audio_file.file, buffer)

    if file_path.stat().st_size > 500 * 1024 * 1024:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=413, detail="El audio supera el límite de 500 MB")

    final_midi = OUTPUT_DIR / f"{file_token}.mid"

    try:
        with TRANSCRIPTION_LOCK:
            transcriber_instance.transcribe(str(file_path), str(final_midi), mode=mode,
                                            arrangement_style=arrangement_style)
        return {
            "status": "success",
            "midi_filename": final_midi.name,
            "chords_filename": final_midi.with_suffix(".chords.json").name
                if final_midi.with_suffix(".chords.json").exists() else None,
            "audio_filename": file_path.name,
            "source_filename": original_name,
            "midi_path": str(final_midi.resolve())
        }
    except Exception as e:
        file_path.unlink(missing_ok=True)
        final_midi.unlink(missing_ok=True)
        final_midi.with_suffix(".chords.json").unlink(missing_ok=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/play-live")
def play_live(payload: dict):
    filename = Path(payload.get("midi_filename", "")).name
    midi_path = OUTPUT_DIR / filename
    if not midi_path.exists():
        raise HTTPException(status_code=404, detail="Archivo MIDI no encontrado")

    from src.visualizer_bridge import VisualizerBridge
    bridge = VisualizerBridge()
    bridge.play(str(midi_path))
    return {"status": "started"}

@app.post("/api/render-video")
def render_video(payload: dict):
    midi_filename = Path(payload.get("midi_filename", "")).name
    audio_filename = Path(payload.get("audio_filename", "")).name if payload.get("audio_filename") else None

    midi_path = OUTPUT_DIR / midi_filename
    if not midi_path.exists():
        raise HTTPException(status_code=404, detail="Archivo MIDI no encontrado")

    audio_path = None
    if audio_filename:
        possible_audio = UPLOAD_DIR / audio_filename
        if possible_audio.exists():
            audio_path = str(possible_audio)

    video_path = OUTPUT_DIR / f"{midi_path.stem}.mp4"
    from src.visualizer_bridge import VisualizerBridge
    bridge = VisualizerBridge()
    bridge.render_video(str(midi_path), str(video_path), audio_path=audio_path)

    return {
        "status": "success",
        "video_filename": video_path.name
    }

@app.get("/download/midi/{filename}")
async def download_midi(filename: str):
    filename = Path(filename).name
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, media_type="audio/midi", filename=filename)

@app.get("/download/chords/{filename}")
async def download_chords(filename: str):
    filename = Path(filename).name
    if not filename.endswith(".chords.json"):
        raise HTTPException(status_code=400, detail="Archivo de acordes no válido")
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, media_type="application/json", filename=filename)

@app.get("/download/video/{filename}")
async def download_video(filename: str):
    filename = Path(filename).name
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(path, media_type="video/mp4", filename=filename)

if __name__ == "__main__":
    import uvicorn
    print("\n[INFO] Servidor disponible en: http://localhost:8000\n")
    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=False)
