# evernote-markdown

Evernote ENEX to Markdown converter.

## Usage

```
Usage: convert.py [OPTIONS] EMEX_FILE OUTPUT_PATH

  Evernote ENEX to Markdown converter.

Options:
  -v, --verbose  Increase log verbosity.
  --help         Show this message and exit.
```

Markdown files are stored in the output path and pictures are stored in `media` directory under the output path.

### Example

```bash
convert.py -v Index.enex Index
```
