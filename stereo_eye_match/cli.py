from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

import cv2
import numpy as np

from .matching import apply_correction, paired_correction


def fit(args: argparse.Namespace) -> None:
    all_params: list[np.ndarray] = []
    videos: dict[str, dict] = {}
    for source in args.inputs:
        cap = cv2.VideoCapture(str(source))
        if not cap.isOpened():
            raise SystemExit(f"Could not open input: {source}")
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0; frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if width != 2 * height:
            raise SystemExit(f"Only side-by-side 2:1 input is supported currently: {source}")
        step = max(1, int(round(fps * args.sample_seconds)))
        samples: list[tuple[int, np.ndarray]] = []; i = 0
        while True:
            ok, frame = cap.read()
            if not ok: break
            if i % step == 0:
                half = width // 2
                p = paired_correction(frame[:, :half], frame[:, half:], args.sample_size, args.gamma)
                samples.append((i, p)); all_params.append(p)
            i += 1
        cap.release()
        if not samples: raise SystemExit(f"No samples found: {source}")
        videos[source.stem] = {"source_name": source.name, "fps": fps, "frame_count": frame_count,
                               "keyframes": [[int(n), *[float(x) for x in p]] for n, p in samples]}
        print(f"fit {source.name}: {len(samples)} samples from {i} frames", flush=True)
    global_params = np.median(np.asarray(all_params), axis=0).astype(np.float32)
    for info in videos.values():
        for keyframe in info["keyframes"]:
            p = np.asarray(keyframe[1:], dtype=np.float32)
            keyframe[1:] = [float(x) for x in p / np.maximum(global_params, 1e-6)]
    model = {"version": 1, "layout": "sbs", "reference_eye": "left", "gamma": args.gamma,
             "sample_size": args.sample_size, "sample_seconds": args.sample_seconds,
             "global_params": [float(x) for x in global_params], "videos": videos}
    args.model.parent.mkdir(parents=True, exist_ok=True)
    args.model.write_text(json.dumps(model, indent=2), encoding="utf-8")
    print(f"wrote model: {args.model}")


def interpolate(keyframes: list[list[float]], frame: int, global_params: np.ndarray) -> np.ndarray:
    if not keyframes: return global_params.copy()
    k = np.asarray(keyframes, dtype=np.float32); frames = k[:, 0]; values = k[:, 1:]
    if frame <= frames[0]: residual = values[0]
    elif frame >= frames[-1]: residual = values[-1]
    else:
        j = int(np.searchsorted(frames, frame)); t = (frame - frames[j - 1]) / max(1.0, frames[j] - frames[j - 1])
        residual = (1 - t) * values[j - 1] + t * values[j]
    return global_params * residual


def apply(args: argparse.Namespace) -> None:
    model = json.loads(args.model.read_text(encoding="utf-8")); gamma = float(model.get("gamma", 2.2))
    global_params = np.asarray(model["global_params"], dtype=np.float32)
    info = model.get("videos", {}).get(args.input.stem); keyframes = info["keyframes"] if info else []
    cap = cv2.VideoCapture(str(args.input))
    if not cap.isOpened(): raise SystemExit(f"Could not open input: {args.input}")
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    if width != 2 * height: raise SystemExit("Input must be side-by-side 2:1")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.parent / f".{args.output.stem}.{os.getpid()}.tmp.mp4"
    try:
        command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                   "-s", f"{width}x{height}", "-r", f"{fps:.9f}", "-i", "-", "-an", "-c:v", "libx265",
                   "-preset", args.preset, "-crf", str(args.crf), "-pix_fmt", "yuv420p10le", "-tag:v", "hvc1", str(temp)]
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE); i = 0
        try:
            while True:
                ok, frame = cap.read()
                if not ok or (args.limit_frames and i >= args.limit_frames): break
                params = interpolate(keyframes, i, global_params); half = width // 2
                right = apply_correction(frame[:, half:], params, gamma)
                encoder.stdin.write(np.concatenate((frame[:, :half], right), axis=1).tobytes()); i += 1
                if i % 30 == 0: print(f"applied {i} frames", flush=True)
        finally:
            cap.release(); encoder.stdin.close()
        if encoder.wait() != 0: raise SystemExit("ffmpeg encoding failed")
        if args.no_audio: temp.replace(args.output)
        else:
            mux = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(temp), "-i", str(args.input),
                   "-map", "0:v:0", "-map", "1:a?", "-c", "copy", "-shortest", str(args.output)]
            if subprocess.run(mux).returncode != 0: raise SystemExit("ffmpeg audio mux failed")
    finally: temp.unlink(missing_ok=True)
    print(f"wrote {i} frames: {args.output}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="stereo-eye-match")
    sub = parser.add_subparsers(dest="command", required=True)
    fit_parser = sub.add_parser("fit", help="fit a shared model from multiple videos")
    fit_parser.add_argument("inputs", nargs="+", type=Path); fit_parser.add_argument("--model", required=True, type=Path)
    fit_parser.add_argument("--sample-seconds", type=float, default=2.0); fit_parser.add_argument("--sample-size", type=int, default=160)
    fit_parser.add_argument("--gamma", type=float, default=2.2); fit_parser.set_defaults(func=fit)
    apply_parser = sub.add_parser("apply", help="apply a fitted model")
    apply_parser.add_argument("input", type=Path); apply_parser.add_argument("output", type=Path); apply_parser.add_argument("--model", required=True, type=Path)
    apply_parser.add_argument("--preset", default="medium"); apply_parser.add_argument("--crf", type=int, default=18)
    apply_parser.add_argument("--limit-frames", type=int, default=0); apply_parser.add_argument("--no-audio", action="store_true"); apply_parser.set_defaults(func=apply)
    args = parser.parse_args(); args.func(args)
