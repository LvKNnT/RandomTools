"""Compress static images and animated GIFs.

Run without arguments to open the desktop interface, or pass input files to use
the command line. Pillow is the only third-party dependency.
"""

from __future__ import annotations

import argparse
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image, ImageSequence


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@dataclass(frozen=True)
class CompressionOptions:
    quality: int = 80
    max_width: int | None = None
    max_height: int | None = None
    gif_colors: int = 128


def _validate_options(options: CompressionOptions) -> None:
    if not 1 <= options.quality <= 100:
        raise ValueError("Quality must be between 1 and 100.")
    if not 2 <= options.gif_colors <= 256:
        raise ValueError("GIF colors must be between 2 and 256.")
    if options.max_width is not None and options.max_width < 1:
        raise ValueError("Maximum width must be positive.")
    if options.max_height is not None and options.max_height < 1:
        raise ValueError("Maximum height must be positive.")


def _new_size(size: tuple[int, int], options: CompressionOptions) -> tuple[int, int]:
    width, height = size
    width_limit = options.max_width or width
    height_limit = options.max_height or height
    scale = min(width_limit / width, height_limit / height, 1.0)
    return max(1, round(width * scale)), max(1, round(height * scale))


def _flatten_alpha(image: Image.Image, background: str = "white") -> Image.Image:
    """Convert transparency to a solid background for JPEG output."""
    rgba = image.convert("RGBA")
    base = Image.new("RGBA", rgba.size, background)
    base.alpha_composite(rgba)
    return base.convert("RGB")


def _quantize_gif_frame(image: Image.Image, colors: int) -> Image.Image:
    """Quantize RGBA while reserving palette index 255 for transparency.

    Pillow's direct RGBA quantization can discard the GIF transparency index.
    Reserving it explicitly keeps fully transparent pixels transparent after the
    image is saved and reopened.
    """
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    visible_colors = max(1, min(colors - 1, 255))
    rgb = Image.new("RGB", rgba.size, (0, 0, 0))
    rgb.paste(rgba.convert("RGB"), mask=alpha)
    palette_frame = rgb.quantize(
        colors=visible_colors,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.FLOYDSTEINBERG,
    )

    transparent_mask = alpha.point(lambda value: 255 if value < 128 else 0)
    if transparent_mask.getbbox() is not None:
        palette = palette_frame.getpalette() or []
        palette.extend([0] * (768 - len(palette)))
        palette[255 * 3 : 255 * 3 + 3] = [0, 0, 0]
        palette_frame.putpalette(palette)
        palette_frame.paste(255, mask=transparent_mask)
        palette_frame.info["transparency"] = 255
    return palette_frame


def _compress_gif(source: Path, destination: Path, options: CompressionOptions) -> None:
    with Image.open(source) as image:
        frames: list[Image.Image] = []
        durations: list[int] = []
        disposals: list[int] = []
        target_size = _new_size(image.size, options)

        for frame in ImageSequence.Iterator(image):
            rgba = frame.convert("RGBA")
            if rgba.size != target_size:
                rgba = rgba.resize(target_size, Image.Resampling.LANCZOS)

            palette_frame = _quantize_gif_frame(rgba, options.gif_colors)
            frames.append(palette_frame)
            durations.append(int(frame.info.get("duration", image.info.get("duration", 100))))
            disposals.append(int(getattr(frame, "disposal_method", 2)))

        if not frames:
            raise ValueError(f"No frames found in {source}")

        save_options = {
            "save_all": len(frames) > 1,
            "append_images": frames[1:],
            # Palette optimization can renumber the reserved transparency index.
            "optimize": False,
            "duration": durations if len(frames) > 1 else durations[0],
            "loop": int(image.info.get("loop", 0)),
            "disposal": disposals if len(frames) > 1 else disposals[0],
            "transparency": 255,
        }
        frames[0].save(destination, format="GIF", **save_options)


def _compress_static(source: Path, destination: Path, options: CompressionOptions) -> None:
    with Image.open(source) as image:
        target_size = _new_size(image.size, options)
        if image.size != target_size:
            image = image.resize(target_size, Image.Resampling.LANCZOS)

        extension = destination.suffix.lower()
        if extension in {".jpg", ".jpeg"}:
            output = _flatten_alpha(image)
            output.save(
                destination,
                format="JPEG",
                quality=options.quality,
                optimize=True,
                progressive=True,
                subsampling="4:2:0",
            )
        elif extension == ".png":
            image.save(destination, format="PNG", optimize=True, compress_level=9)
        elif extension == ".webp":
            image.save(
                destination,
                format="WEBP",
                quality=options.quality,
                method=6,
                lossless=options.quality == 100,
            )
        else:
            raise ValueError(f"Unsupported output format: {destination.suffix}")


def compressed_path(source: Path, output_dir: Path | None = None) -> Path:
    directory = output_dir or source.parent
    return directory / f"{source.stem}_compressed{source.suffix.lower()}"


def compress_image(
    source: str | Path,
    destination: str | Path | None = None,
    options: CompressionOptions | None = None,
) -> Path:
    """Compress one image and return the output path."""
    source = Path(source).expanduser().resolve()
    options = options or CompressionOptions()
    _validate_options(options)

    if not source.is_file():
        raise FileNotFoundError(f"Input file does not exist: {source}")
    if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported input format: {source.suffix}")

    destination = (
        Path(destination).expanduser().resolve()
        if destination
        else compressed_path(source)
    )
    if destination == source:
        raise ValueError("Output path must be different from the input path.")
    destination.parent.mkdir(parents=True, exist_ok=True)

    if source.suffix.lower() == ".gif":
        if destination.suffix.lower() != ".gif":
            raise ValueError("Animated GIF output must use the .gif extension.")
        _compress_gif(source, destination, options)
    else:
        _compress_static(source, destination, options)
    return destination


def _human_size(byte_count: int) -> str:
    value = float(byte_count)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def _parse_optional_int(value: str) -> int | None:
    value = value.strip()
    return int(value) if value else None


def launch_gui() -> None:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title("Image & GIF Compressor")
    root.geometry("720x500")
    root.minsize(620, 420)

    files: list[Path] = []
    output_var = tk.StringVar()
    quality_var = tk.IntVar(value=80)
    width_var = tk.StringVar()
    height_var = tk.StringVar()
    colors_var = tk.IntVar(value=128)
    status_var = tk.StringVar(value="Add images to begin.")

    outer = ttk.Frame(root, padding=16)
    outer.pack(fill="both", expand=True)
    outer.columnconfigure(0, weight=1)
    outer.rowconfigure(1, weight=1)

    ttk.Label(outer, text="Image & GIF Compressor", font=("Segoe UI", 16, "bold")).grid(
        row=0, column=0, sticky="w", pady=(0, 10)
    )

    list_frame = ttk.Frame(outer)
    list_frame.grid(row=1, column=0, sticky="nsew")
    list_frame.columnconfigure(0, weight=1)
    list_frame.rowconfigure(0, weight=1)
    file_list = tk.Listbox(list_frame, selectmode="extended")
    file_list.grid(row=0, column=0, sticky="nsew")
    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=file_list.yview)
    scrollbar.grid(row=0, column=1, sticky="ns")
    file_list.configure(yscrollcommand=scrollbar.set)

    buttons = ttk.Frame(outer)
    buttons.grid(row=2, column=0, sticky="ew", pady=(8, 12))

    def add_files() -> None:
        selected = filedialog.askopenfilenames(
            title="Choose images",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.gif"), ("All files", "*.*")],
        )
        for name in selected:
            path = Path(name)
            if path not in files and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(path)
                file_list.insert("end", str(path))
        status_var.set(f"{len(files)} image(s) selected.")

    def remove_selected() -> None:
        for index in reversed(file_list.curselection()):
            del files[index]
            file_list.delete(index)
        status_var.set(f"{len(files)} image(s) selected.")

    ttk.Button(buttons, text="Add images", command=add_files).pack(side="left")
    ttk.Button(buttons, text="Remove selected", command=remove_selected).pack(side="left", padx=8)

    settings = ttk.LabelFrame(outer, text="Settings", padding=10)
    settings.grid(row=3, column=0, sticky="ew")
    for column in range(4):
        settings.columnconfigure(column, weight=1)

    ttk.Label(settings, text="Quality (1–100)").grid(row=0, column=0, sticky="w")
    ttk.Spinbox(settings, from_=1, to=100, textvariable=quality_var, width=8).grid(
        row=1, column=0, sticky="ew", padx=(0, 8)
    )
    ttk.Label(settings, text="Max width (optional)").grid(row=0, column=1, sticky="w")
    ttk.Entry(settings, textvariable=width_var).grid(row=1, column=1, sticky="ew", padx=(0, 8))
    ttk.Label(settings, text="Max height (optional)").grid(row=0, column=2, sticky="w")
    ttk.Entry(settings, textvariable=height_var).grid(row=1, column=2, sticky="ew", padx=(0, 8))
    ttk.Label(settings, text="GIF colors (2–256)").grid(row=0, column=3, sticky="w")
    ttk.Spinbox(settings, from_=2, to=256, textvariable=colors_var, width=8).grid(
        row=1, column=3, sticky="ew"
    )

    output_frame = ttk.Frame(outer)
    output_frame.grid(row=4, column=0, sticky="ew", pady=10)
    output_frame.columnconfigure(1, weight=1)
    ttk.Label(output_frame, text="Output folder:").grid(row=0, column=0, padx=(0, 8))
    ttk.Entry(output_frame, textvariable=output_var).grid(row=0, column=1, sticky="ew")

    def choose_output() -> None:
        selected = filedialog.askdirectory(title="Choose output folder")
        if selected:
            output_var.set(selected)

    ttk.Button(output_frame, text="Browse", command=choose_output).grid(row=0, column=2, padx=(8, 0))

    progress = ttk.Progressbar(outer, mode="determinate")
    progress.grid(row=5, column=0, sticky="ew")
    ttk.Label(outer, textvariable=status_var).grid(row=6, column=0, sticky="w", pady=(6, 0))

    def set_controls_enabled(enabled: bool) -> None:
        compress_button.configure(state="normal" if enabled else "disabled")

    def compress_all() -> None:
        if not files:
            messagebox.showwarning("No images", "Add at least one image first.")
            return
        try:
            options = CompressionOptions(
                quality=quality_var.get(),
                max_width=_parse_optional_int(width_var.get()),
                max_height=_parse_optional_int(height_var.get()),
                gif_colors=colors_var.get(),
            )
            _validate_options(options)
        except (ValueError, tk.TclError) as exc:
            messagebox.showerror("Invalid settings", str(exc))
            return

        output_dir = Path(output_var.get()).expanduser() if output_var.get().strip() else None
        work = list(files)
        progress.configure(maximum=len(work), value=0)
        set_controls_enabled(False)

        def worker() -> None:
            successes = 0
            failures: list[str] = []
            total_before = 0
            total_after = 0
            for index, source in enumerate(work, start=1):
                try:
                    destination = compressed_path(source, output_dir)
                    total_before += source.stat().st_size
                    compress_image(source, destination, options)
                    total_after += destination.stat().st_size
                    successes += 1
                except Exception as exc:  # report per-file errors without stopping the batch
                    failures.append(f"{source.name}: {exc}")
                root.after(0, lambda i=index: progress.configure(value=i))

            def finish() -> None:
                set_controls_enabled(True)
                saved = max(0, total_before - total_after)
                status_var.set(
                    f"Finished: {successes}/{len(work)} compressed; saved {_human_size(saved)}."
                )
                if failures:
                    messagebox.showwarning("Some files failed", "\n".join(failures[:10]))
                else:
                    messagebox.showinfo("Complete", status_var.get())

            root.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    compress_button = ttk.Button(outer, text="Compress images", command=compress_all)
    compress_button.grid(row=7, column=0, sticky="ew", pady=(12, 0))
    root.mainloop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compress static images and animated GIFs.")
    parser.add_argument("inputs", nargs="*", type=Path, help="Image files to compress")
    parser.add_argument("-o", "--output-dir", type=Path, help="Output directory")
    parser.add_argument("-q", "--quality", type=int, default=80, help="JPEG/WebP quality (1-100)")
    parser.add_argument("--max-width", type=int, help="Resize to at most this width")
    parser.add_argument("--max-height", type=int, help="Resize to at most this height")
    parser.add_argument("--gif-colors", type=int, default=128, help="GIF palette colors (2-256)")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.inputs:
        launch_gui()
        return 0

    options = CompressionOptions(args.quality, args.max_width, args.max_height, args.gif_colors)
    try:
        _validate_options(options)
        for source in args.inputs:
            destination = compressed_path(source, args.output_dir)
            before = source.stat().st_size
            compress_image(source, destination, options)
            after = destination.stat().st_size
            reduction = (1 - after / before) * 100 if before else 0
            print(
                f"{source.name} -> {destination} "
                f"({_human_size(before)} to {_human_size(after)}, {reduction:.1f}% smaller)"
            )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
