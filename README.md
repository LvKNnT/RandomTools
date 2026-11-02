# Random Tools

A collection of small, focused utilities for everyday automation and file processing. Each tool lives in its own directory, keeps its dependencies local, and includes a dedicated README with complete setup and usage instructions.

## Tools

| Tool | What it does | Interface |
| --- | --- | --- |
| [AutoMailer](./AutoMailer/) | Creates personalized Gmail drafts from an HTML template and CSV data through Edge on Windows or Chrome on macOS. | Browser automation |
| [Image & GIF Compressor](./Compresser/) | Compresses and optionally resizes JPEG, PNG, WebP, and animated GIF files while preserving GIF animation and transparency. | Desktop GUI and CLI |

## Requirements

- Python 3.10 or later
- `pip` or Conda for dependency installation
- Tool-specific dependencies described in each tool's README

AutoMailer additionally requires access to Gmail plus Microsoft Edge on Windows or Google Chrome on macOS. The image compressor uses Tkinter for its desktop interface; Tkinter is included with many standard Python installations.

## Quick start

Clone the repository and move into the tool you want to use. Dependencies are installed per tool rather than from a repository-wide requirements file.

### AutoMailer

```powershell
cd AutoMailer
python -m pip install --upgrade selenium
python .\send_mail.py
```

On macOS, run the Chrome version instead:

```bash
cd AutoMailer
python3 -m pip install --upgrade selenium
python3 ./send_mail_macos.py
```

Before running either version, configure the subject and input paths in the platform script, start its browser with remote debugging enabled, and open Gmail. See the [AutoMailer guide](./AutoMailer/README.md) for the required HTML template and CSV formats, Windows and macOS browser setup, safety notes, and troubleshooting.

AutoMailer creates drafts only; it does not send them. Always test with one recipient and review every generated draft.

### Image & GIF Compressor

```powershell
cd Compresser
python -m pip install -r requirements.txt
python .\image_compressor.py
```

Running the script without arguments opens the desktop interface. To use the CLI instead:

```powershell
python .\image_compressor.py .\input\photo.jpg -q 75 --max-width 1600 -o .\output
```

See the [compressor guide](./Compresser/README.md) for all supported formats and command-line options.

## Repository layout

```text
RandomTools/
├── AutoMailer/
│   ├── README.md
│   ├── send_mail.py
│   └── send_mail_macos.py
├── Compresser/
│   ├── input/
│   ├── output/
│   ├── README.md
│   ├── image_compressor.py
│   ├── requirements.txt
│   └── test_image_compressor.py
└── README.md
```

The compressor's `input/` and `output/` contents are ignored by Git so local images and generated files are not accidentally committed.

## Development

Install the compressor dependency before running the current automated test suite:

```powershell
python -m pip install -r .\Compresser\requirements.txt
python -m unittest discover -s .\Compresser -p "test_*.py"
```

When adding another utility:

1. Place it in a self-contained directory.
2. Add a tool-level `README.md` with installation, usage, inputs, outputs, and limitations.
3. Keep generated files, credentials, personal data, and local caches out of Git.
4. Add the tool to the table and repository layout in this README.
5. Include automated tests where practical.

## Safety and privacy

- Inspect a tool and its configuration before running it on important data.
- Test destructive or bulk operations on sample files first.
- Do not commit credentials, browser profiles, recipient lists, or other sensitive data.
- Review generated output before distributing or sending it.

## License

No repository-wide license is currently included. Unless the repository owner adds one, the code is not automatically granted for redistribution or modification by others.
