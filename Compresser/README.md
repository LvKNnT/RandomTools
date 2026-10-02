# Image & GIF Compressor

A small Python utility for compressing JPEG, PNG, WebP, and animated GIF files.
It includes a desktop interface and a command-line interface. Animated GIF timing,
looping, and transparency are preserved.

## Folders

- `input/`: place source images here.
- `output/`: compressed images can be written here.

The contents of both folders are ignored by Git. The placeholder files keep the
empty folders available after cloning the repository.

## Install

```powershell
conda run -n base python -m pip install -r requirements.txt
```

## Desktop interface

```powershell
conda run -n base python image_compressor.py
```

Add one or more images, adjust the settings, choose the `output` folder (or any
other folder), and click **Compress images**. Outputs are named `*_compressed` so
originals are not overwritten.

## Command line

```powershell
conda run -n base python image_compressor.py input\photo.jpg input\animation.gif -q 75 --max-width 1600 -o output
```

Options:

- `-q, --quality`: JPEG/WebP quality from 1 to 100 (default: 80).
- `--max-width`, `--max-height`: optional bounding dimensions; aspect ratio is preserved.
- `--gif-colors`: GIF palette size from 2 to 256 (default: 128). Fewer colors usually means a smaller file.
- `-o, --output-dir`: output folder; by default each result is saved beside its source.

PNG compression is lossless, so the quality option does not affect PNG files.
