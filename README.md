<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0F2027,50:203A43,100:2C5364&height=200&section=header&text=Veylance%20ID&fontSize=60&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc=Local,%20Offline%20AI-Powered%20Facial%20Identity%20Verification&descAlignY=55&descSize=18" width="100%"/>

<a href="https://github.com/opencv/opencv_zoo"><img src="https://readme-typing-svg.demolab.com/?font=Fira+Code&weight=500&size=20&pause=1000&color=2C5364&center=true&vCenter=true&width=650&lines=100%25+Offline+%E2%80%94+No+Cloud%2C+No+Telemetry;YuNet+Detection+%2B+SFace+Recognition;Head-Turn+Liveness+Challenge;Windows+Hello+Face+Alternative+for+RGB+Webcams" alt="Typing SVG" /></a>

<br/>

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PySide6](https://img.shields.io/badge/GUI-PySide6-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![OpenCV](https://img.shields.io/badge/CV-OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![SQLite](https://img.shields.io/badge/DB-SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Windows](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)

![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-success?style=for-the-badge)
![Offline](https://img.shields.io/badge/Cloud%20Calls-Zero-critical?style=for-the-badge)
![PRs](https://img.shields.io/badge/PRs-Welcome-brightgreen?style=for-the-badge)

</div>

---

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

<div align="center">
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:2C5364,50:203A43,100:0F2027&height=100&section=footer" width="100%"/>
</div>
