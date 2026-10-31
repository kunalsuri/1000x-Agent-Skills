---
name: note-taker
description: Turn a rough meeting transcript into dated Markdown notes with decisions and action items. Use when the user pastes a transcript and asks for notes, minutes, or a summary of decisions.
version: 1.0.0
allowed-tools: [view_file]
---

# Note Taker

Turn a transcript into dated Markdown notes.

## Usage

```bash
python scripts/format_notes.py transcript.txt
```

The script reads the transcript, groups it into `Decisions` and `Actions`,
and prints Markdown. It writes nothing and reaches nothing outside the file
it was given.
