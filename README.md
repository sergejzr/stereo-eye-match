# Stereo Eye Match

Two-pass color and exposure matching for synchronized stereo, VR and 360-degree video.

Stereo Eye Match fits a shared left/right camera model from multiple clips and
applies that model with smooth per-video adaptation. It is designed for footage
where the two eyes have different exposure, white balance or color response.

Current release: `0.1.0` (alpha)

## Supported input

The first release supports synchronized side-by-side (SBS) video, especially
equirectangular 360-degree footage. A `7680x3840` file is interpreted as two
`3840x3840` eye images. The left eye is the reference and the right eye is
corrected. FFmpeg must be installed and available on `PATH`.

## Install

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## Fit one shared model from several videos

```powershell
stereo-eye-match fit `
  D:\vrtest\dark.mp4 `
  D:\vrtest\light.mp4 `
  D:\vrtest\lightok.mp4 `
  --model .\models\camera_model.json
```

The fit pass samples frames and stores both a shared camera correction and
smooth per-video residuals. It does not modify the input videos.

## Apply a model

```powershell
stereo-eye-match apply `
  D:\vrtest\light.mp4 `
  .\outputs\light_matched.mp4 `
  --model .\models\camera_model.json `
  --preset medium `
  --crf 18
```

For a quick test, add `--limit-frames 60 --preset ultrafast`.

## Limitations

This tool cannot recover clipped highlights or detail that was never recorded.
It is not a substitute for synchronization, geometric stereo calibration,
rolling-shutter correction, denoising or creative color grading. Large
parallax, severe vignetting or changing camera modes may require a more
advanced spatial model.

## License

Apache License 2.0. See [LICENSE](LICENSE).
