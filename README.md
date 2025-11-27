# VTT Transcript Cleaner

Parses VTT (WebVTT) transcript files, groups statements by speaker, and uses AI to remove filler words and improve readability.

## Features

- **VTT Parsing**: Extracts speaker names, timestamps, and text from VTT files
- **Speaker Grouping**: Combines consecutive statements from the same speaker
- **Smart Chunking**: Splits large transcripts into chunks that fit LLM context windows
- **AI Cleaning**: Uses Azure OpenAI API to remove filler words ("um", "uh", "like", etc.)
- **Markdown Export**: Exports with strikethrough to show what was removed

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file with your Azure OpenAI credentials
cp .env.example .env
# Then edit .env and add your Azure OpenAI configuration
```

## Usage

### Basic Usage

```bash
# Parse and export raw transcript
python vtt_parser.py

# Clean transcript with AI
python clean_transcript.py
```

### Python API

```python
from vtt_parser import VTTParser, TranscriptGrouper, MarkdownExporter

# Parse VTT file
parser = VTTParser('example.vtt')
segments = parser.parse()

# Group by speaker
grouper = TranscriptGrouper(segments, max_gap_seconds=5.0)
statements = grouper.group_by_speaker()

# Export to markdown
MarkdownExporter.export_raw(statements, 'output.md')
```

### With LLM Cleaning

```python
from vtt_parser import VTTParser, TranscriptGrouper
from clean_transcript import TranscriptCleaner

# Parse and group
parser = VTTParser('example.vtt')
segments = parser.parse()
grouper = TranscriptGrouper(segments)
statements = grouper.group_by_speaker()

# Clean with LLM
cleaner = TranscriptCleaner()
cleaned = [cleaner.clean_statement(s) for s in statements]

# Export with strikethrough diff
MarkdownExporter.export_with_strikethrough(
    statements, 
    cleaned, 
    'cleaned.md'
)
```

## Configuration

### Grouping Parameters

```python
# Maximum gap between segments to group as one statement
grouper = TranscriptGrouper(segments, max_gap_seconds=5.0)
```

### Chunking Parameters

```python
# Maximum tokens per chunk for LLM processing
chunker = TranscriptChunker(statements, max_tokens=6000)
```

### Azure OpenAI Configuration

```python
# Use different deployment
cleaner = TranscriptCleaner(
    deployment="your-gpt-4-deployment",
    endpoint="https://your-resource.openai.azure.com/",
    api_key="your-key"
)
```

## Output Files

- `transcript_raw.md`: Raw transcript grouped by speaker with timestamps
- `transcript_cleaned.md`: Cleaned transcript with ~~strikethrough~~ showing removed words

## Example Output

```markdown
## 1. Grant Smith

**Time:** 01:30:05.625

So ~~I think~~ ~~absolutely~~ where we're seeing power apps already in use, replacing 
that form with an interactive front end that captures all the same information 
~~you know~~ is definitely what we'd be looking to do.
```

## Architecture

- **VTTParser**: Parses WebVTT format into structured segments
- **TranscriptGrouper**: Groups consecutive segments by speaker
- **TranscriptChunker**: Splits transcript for LLM context limits
- **TranscriptCleaner**: Uses Azure OpenAI API to clean text
- **MarkdownExporter**: Exports to markdown with optional strikethrough

## Notes

- Token estimation uses ~4 characters per token (rough approximation)
- Strikethrough diff is word-level (not character-level)
- Preserves original timestamps and speaker names
- Uses Azure OpenAI Service

## License

MIT
