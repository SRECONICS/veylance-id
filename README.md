# Veylance ID

**Local, offline AI-powered facial identity verification and presence security for Windows.**

Veylance ID turns a regular RGB webcam into a Windows Hello Face–style security layer for laptops that don't have IR camera hardware. Everything — face detection, recognition, liveness checking, and decision-making — runs **100% locally**. No cloud calls, no external face recognition APIs, no telemetry.

> Veylance ID **locks** your Windows session automatically; it does not and cannot bypass Windows sign-in. Your Windows PIN/password/Hello remains the actual authentication boundary — Veylance just decides *when* to trigger the OS lock.

## What it does

```
RGB Webcam → Face Detection → Alignment → Embedding
                                              │
                          ┌───────────────────┴───────────────────┐
                          │                                       │
                  Identity Matching                        Liveness Check
                          │                                       │
                          └───────────────────┬───────────────────┘
                                    Authentication Decision
                                       VERIFIED / DENIED
                                              │
                                    Presence Monitoring
                                     Walk-Away Auto-Lock
```

- **Face detection & alignment** — OpenCV's YuNet (ONNX), giving a bounding box plus 5-point landmarks
- **Face recognition** — OpenCV's SFace (ONNX), 128-d embeddings compared by cosine similarity against enrolled identities
- **Liveness detection** — an active head-turn challenge (a static photo can't pass it)
- **Enrollment** — captures 10 samples per identity, guided through center/left/right head poses, rejecting blurry/dark/overexposed frames
- **Local database** — SQLite, storing enrolled identities, authentication history, and settings
- **Authentication History** — every VERIFIED/DENIED/UNKNOWN event logged, with an intruder snapshot attached to denials
- **PIN-gated enrollment** — enrolling a new identity (including the very first one) requires a security PIN, so nobody can add themselves as an authorized user without your say-so
- **Walk-away auto-lock** — once verified, Veylance keeps watching; if you leave and don't come back within a configurable timeout, it locks Windows
- **System tray** — runs in the background; closing or minimizing the window doesn't stop protection
- **Fully configurable** — recognition sensitivity, liveness on/off, absence timeout, and more, all in Settings

## Tech stack

| Component | Technology |
|---|---|
| Language | Python 3.11 |
| GUI | PySide6 (Qt) |
| Computer vision | OpenCV (YuNet + SFace, ONNX models) |
| Storage | SQLite |
| Windows integration | `ctypes` → `user32.LockWorkStation` |
| Packaging | PyInstaller |

## Setup

```powershell
git clone <this-repo>
cd "Veylance ID"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Download the two face models (not committed to the repo — see `.gitignore`):

```powershell
Invoke-WebRequest -Uri "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" -OutFile "models\face_detection_yunet_2023mar.onnx"
Invoke-WebRequest -Uri "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx" -OutFile "models\face_recognition_sface_2021dec.onnx"
```

Run it:

```powershell
python main.py
```

On first launch, go to **Enroll Identity** and enroll yourself — you'll be asked to set a security PIN first, since PIN protection gates every enrollment from that point on.

## Packaging

```powershell
pyinstaller veylance.spec
```

Produces `dist\VeylanceID.exe` — a single-file, windowed executable with both models bundled in. Application data (database, enrolled faces, snapshots) is stored separately at `%LOCALAPPDATA%\VeylanceID`, so it persists across runs and updates.

## Project structure

```
Veylance ID/
├── main.py                 # App entry point, Dashboard, camera loop, orchestration
├── paths.py                # Dev vs. packaged path resolution
├── veylance.spec           # PyInstaller build config
│
├── vision/
│   ├── detector.py         # YuNet face detection
│   ├── embeddings.py       # SFace embedding extraction
│   ├── recognizer.py       # Identity matching (cosine similarity)
│   ├── liveness.py         # Head-turn liveness challenge
│   ├── presence.py         # Walk-away absence tracking
│   ├── pose.py             # Head-pose classification (enrollment)
│   └── quality.py          # Blur/brightness capture gating
│
├── ui/
│   ├── enrollment.py       # Enroll Identity page
│   ├── identities.py       # Enrolled Identities page
│   ├── history.py          # Authentication History page
│   ├── settings.py         # Settings page
│   └── pin_dialog.py       # PIN entry/setup dialogs
│
├── database/
│   └── database.py         # SQLite layer — users, auth_logs, settings, PIN
│
└── models/                 # ONNX models (gitignored — see Setup)
```

## Known limitations

These are documented rather than hidden — this is a personal-project security layer, not a certified biometric system:

- **Liveness** is a single head-turn heuristic, not a trained anti-spoofing model. It defeats printed photos; it would not reliably defeat a video replay of the enrolled user.
- **Recognition threshold** (default cosine similarity 0.363) is OpenCV Zoo's published benchmark figure, not something calibrated against this specific camera/lighting — tune it in Settings if you see false accepts/rejects.
- **Single camera, single active user** at a time — multi-face handling only identifies the primary detected face per frame.
- Locking Windows is a convenience layer on top of, not a replacement for, Windows authentication.

## License

MIT — see [LICENSE](LICENSE).
