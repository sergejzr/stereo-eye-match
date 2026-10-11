# Repository Guidelines

## Project Structure & Module Organization

This repository contains a small Python CLI for matching color and exposure
between synchronized stereo-video eyes.

- `stereo_eye_match/`: installable package and CLI implementation.
- `stereo_eye_match/matching.py`: paired-pixel statistics and correction logic.
- `stereo_eye_match/cli.py`: `fit` and `apply` commands, model serialization, and FFmpeg I/O.
- `examples/`: usage notes and future small, non-copyrighted examples.
- `README.md`: user-facing installation and workflow documentation.
- `pyproject.toml`: package metadata and console-script entry point.

Keep source media, fitted models, and rendered outputs outside the repository.
Large video files must never be committed.

## Build, Test, and Development Commands

Create an isolated environment and install the package editable:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Run the CLI locally:

```powershell
python -m stereo_eye_match --help
stereo-eye-match fit input1.mp4 input2.mp4 --model models\camera.json
stereo-eye-match apply input.mp4 outputs\matched.mp4 --model models\camera.json
```

FFmpeg must be installed and available on `PATH`.

## Coding Style & Naming Conventions

Use Python 3.10+, four-space indentation, type hints for public functions,
and concise docstrings. Use `snake_case` for functions and variables,
`PascalCase` only for classes, and lowercase module names. Prefer NumPy/OpenCV
operations over unnecessary per-pixel Python loops. Keep CLI behavior stable
and update `README.md` when options change.

## Testing Guidelines

The project currently uses compile checks and CLI smoke tests. Run:

```powershell
python -m compileall stereo_eye_match
python -m stereo_eye_match --help
```

Future tests should use `pytest`, live under `tests/`, and use small synthetic
SBS clips rather than committed camera footage. Name tests `test_*.py`.

## Commit & Pull Request Guidelines

Use short imperative commit subjects, preferably Conventional Commit style,
for example `feat: add top-bottom layout support` or `fix: smooth model gains`.
Pull requests should explain the algorithmic change, include test commands and
results, document CLI changes, and avoid uploading source videos or generated
renders. Include before/after samples only when legally redistributable.

## Security & Configuration Tips

Do not commit credentials, private media, camera metadata containing personal
information, or generated models derived from sensitive footage. Validate
input dimensions before processing and keep FFmpeg output paths explicit.
