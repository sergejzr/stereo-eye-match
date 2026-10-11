from __future__ import annotations

import cv2
import numpy as np


def paired_correction(left: np.ndarray, right: np.ndarray, size: int = 160, gamma: float = 2.2) -> np.ndarray:
    """Estimate [exposure, red, green, blue] correction for right -> left."""
    l = cv2.GaussianBlur(cv2.resize(left, (size, size), interpolation=cv2.INTER_AREA), (0, 0), 1.5)
    r = cv2.GaussianBlur(cv2.resize(right, (size, size), interpolation=cv2.INTER_AREA), (0, 0), 1.5)
    l = np.clip(l[..., ::-1].astype(np.float32) / 255.0, 0, 1) ** gamma
    r = np.clip(r[..., ::-1].astype(np.float32) / 255.0, 0, 1) ** gamma
    ly = 0.2126 * l[..., 0] + 0.7152 * l[..., 1] + 0.0722 * l[..., 2]
    ry = 0.2126 * r[..., 0] + 0.7152 * r[..., 1] + 0.0722 * r[..., 2]
    h, w = ly.shape
    mask = np.ones_like(ly, dtype=bool)
    mask[: max(2, h // 25)] = False
    mask[-max(2, h // 25):] = False
    mask[:, : max(2, w // 50)] = False
    mask[:, -max(2, w // 50):] = False
    mask &= (ly > 0.025) & (ly < 0.96) & (ry > 0.025) & (ry < 0.96)
    if int(mask.sum()) < 100:
        mask[:] = True
    exposure = float(np.median(ly[mask] / np.maximum(ry[mask], 1e-5)))
    direct = np.array([
        np.median(l[..., c][mask] / np.maximum(r[..., c][mask], 1e-5))
        for c in range(3)
    ], dtype=np.float32)
    exposure = np.clip(exposure, 0.65, 1.55)
    chroma = np.clip(direct / exposure, 0.65, 1.45)
    return np.array([exposure, *chroma], dtype=np.float32)


def apply_correction(image: np.ndarray, params: np.ndarray, gamma: float = 2.2) -> np.ndarray:
    """Apply correction with small LUTs to avoid full-resolution float images."""
    x = np.arange(256, dtype=np.float32) / 255.0
    linear = np.clip(x, 0, 1) ** gamma
    gains = params[0] * params[1:]
    lut_rgb = np.clip((linear[:, None] * gains[None, :]) ** (1.0 / gamma) * 255 + 0.5, 0, 255).astype(np.uint8)
    out = np.empty_like(image)
    out[..., 0] = cv2.LUT(image[..., 0], lut_rgb[:, 2])
    out[..., 1] = cv2.LUT(image[..., 1], lut_rgb[:, 1])
    out[..., 2] = cv2.LUT(image[..., 2], lut_rgb[:, 0])
    return out
