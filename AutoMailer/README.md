# AutoMailer

AutoMailer creates personalized **Gmail drafts** from an HTML template and a CSV file. It attaches to an existing Microsoft Edge session through the browser's remote-debugging interface, fills each draft in the Gmail web interface, and leaves every message in Drafts for review.

> AutoMailer does not click **Send**. Review the generated drafts before sending them manually.

## Features

- Creates one Gmail draft per non-empty `Email` row in a CSV file.
- Replaces `{{Column Name}}` placeholders in an HTML template with values from the matching CSV columns.
- Preserves rich HTML formatting by copying the rendered message to the clipboard and pasting it into Gmail.
- Validates the CSV headers before creating any drafts.
- Reports missing required columns and warns about unused columns.
- Supports UTF-8 CSV files, including files exported by spreadsheet applications with a UTF-8 BOM.

## Requirements

- Windows
- Python 3.9 or later
- Microsoft Edge
- A Gmail account accessible in Edge
- Selenium 4

Install the Python dependency:

```powershell
python -m pip install --upgrade selenium
```

Recent Selenium releases can usually obtain a compatible Edge WebDriver through Selenium Manager. If driver discovery fails, install a Microsoft Edge WebDriver version compatible with your Edge version and add it to `PATH`.

## Input files

AutoMailer uses two input files. Their paths are configured near the top of `send_mail.py`:

```python
SUBJECT = "Your email subject"
HTML_TEMPLATE_PATH = "message.html"
CSV_DATA_PATH = "recipients.csv"
```

Relative paths are resolved from the directory where you run the script. The simplest setup is to keep the script, HTML template, and CSV file in the same directory.

### HTML template

Add placeholders using double braces. Placeholder names are case-sensitive and must exactly match CSV headers.

```html
<p>Hello {{Name}},</p>
<p>Your registration for <strong>{{Event}}</strong> has been confirmed.</p>
<p>Your role is: {{Role}}</p>
```

### CSV data

The CSV must contain an `Email` column plus a column for every placeholder in the HTML template.

```csv
Email,Name,Event,Role
alex@example.com,Alex,Community Day,Volunteer
sam@example.com,Sam,Community Day,Coordinator
```

For the example above, the required headers are `Email`, `Name`, `Event`, and `Role`. Extra CSV columns are allowed and are reported as ignored. Rows with an empty `Email` value are skipped.

## Usage

1. Update `SUBJECT`, `HTML_TEMPLATE_PATH`, and `CSV_DATA_PATH` in `send_mail.py`.
2. Close any Edge instance that is already using the debug profile you plan to use.
3. Press <kbd>Win</kbd>+<kbd>R</kbd> and launch Edge with remote debugging enabled:

   ```text
   msedge.exe --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\AutoMailer\EdgeProfile"
   ```

4. In that Edge window, open Gmail, sign in, select the correct account or delegated mailbox, and leave the Gmail tab active.
5. From the AutoMailer directory, run:

   ```powershell
   python .\send_mail.py
   ```

6. Check the validation report in the terminal. Draft creation begins only if all required columns are present.
7. Review the resulting messages in Gmail's **Drafts** folder before sending them.

Start with a CSV containing one test recipient. Running the script again creates another set of drafts; it does not detect or remove duplicates.

## How it works

For each eligible CSV row, AutoMailer:

1. Opens a new Gmail compose window.
2. Enters the address from the `Email` column.
3. Enters the configured subject.
4. Replaces template placeholders with values from that row.
5. Copies the personalized HTML to the browser clipboard and pastes it into the message body.
6. Presses <kbd>Esc</kbd> so Gmail saves and closes the draft.

If automation fails while processing a row, the script reports the error and stops. Previously created drafts remain in Gmail.

## Troubleshooting

### `Failed to connect`

- Confirm Edge was started with `--remote-debugging-port=9222`.
- Confirm no other process is using port `9222`.
- Use the dedicated debug profile from the launch command, not a normal Edge profile that is already open.
- Confirm Selenium or `msedgedriver` is compatible with the installed Edge version.

### A required column is missing

Every `{{placeholder}}` in the HTML must have an exact, case-sensitive CSV header. The CSV must also contain a header named exactly `Email`. Check for leading or trailing spaces in both places.

### Clipboard access is blocked

Keep the Gmail tab active and allow clipboard access if Edge asks. Browser or organization policies can prevent the Clipboard API from writing rich HTML.

### Gmail fields are not filled correctly

The automation depends on Gmail's current web interface, focus order, and CSS selectors. UI changes, pop-ups, an inactive Gmail tab, or a slow connection can interrupt it. Dismiss pop-ups, keep Gmail visible, and retry with a one-row test CSV.

### Formatting looks wrong

Open the HTML template directly in a browser to verify it first. Gmail may remove unsupported CSS, scripts, external resources, or unsafe markup.

## Security notes

- A browser remote-debugging port allows local software to control that browser session. Use a dedicated Edge profile and close the debug browser when finished.
- Treat recipient CSV files and generated drafts as sensitive data.
- Do not place passwords, session cookies, or API keys in the script, template, or repository.
- Verify the active Gmail account and every recipient before sending.

## Limitations

- Gmail only; the script is coupled to the Gmail web interface.
- Microsoft Edge only.
- Creates drafts sequentially and has no resume or deduplication support.
- Does not validate email address syntax.
- Stops at the first browser-automation error.
- Gmail UI changes may require selector or keyboard-navigation updates.

## License

No license is currently included. Unless the repository owner adds one, the code is not automatically granted for redistribution or modification by others.
