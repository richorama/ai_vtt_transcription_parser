# VTT Transcript Cleaner

Parses VTT (WebVTT) transcript files, groups statements by speaker, and uses AI to remove filler words and improve readability.

## Features

- **VTT Parsing**: Extracts speaker names, timestamps, and text from VTT files
- **Speaker Grouping**: Combines consecutive statements from the same speaker
- **Smart Chunking**: Splits large transcripts into chunks that fit LLM context windows
- **AI Cleaning**: Uses Azure OpenAI API to remove filler words ("um", "uh", "like", etc.)
- **Markdown Export**: Exports grouped transcript with timestamps

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
# Parse VTT and export raw transcript
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
from vtt_parser import VTTParser, TranscriptGrouper, TranscriptChunker
from clean_transcript import TranscriptCleaner

# Parse and group
parser = VTTParser('example.vtt')
segments = parser.parse()
grouper = TranscriptGrouper(segments)
statements = grouper.group_by_speaker()

# Create chunks
chunker = TranscriptChunker(statements, max_tokens=2000)
chunks = chunker.create_chunks()

# Clean with LLM
cleaner = TranscriptCleaner()
for chunk in chunks:
    cleaned_texts = cleaner.clean_chunk(chunk)
    # Process cleaned_texts as needed
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
- `transcript_cleaned.md`: Cleaned transcript grouped by speaker with timestamps

## Example Output

```markdown
## Grant Smith

**01:30:05.625**  
Where we're seeing power apps already in use, replacing that form with an 
interactive front end that captures all the same information is definitely 
what we'd be looking to do.
```

## Architecture

- **VTTParser**: Parses WebVTT format into structured segments
- **TranscriptGrouper**: Groups consecutive segments by speaker
- **TranscriptChunker**: Splits transcript for LLM context limits
- **TranscriptCleaner**: Uses Azure OpenAI API to clean text
- **MarkdownExporter**: Exports to markdown with optional strikethrough

## Notes

- Token estimation uses ~4 characters per token (rough approximation)
- Preserves original timestamps and speaker names
- Uses Azure OpenAI Service
- Cleaned output shows only the final cleaned text (no strikethrough diff)

## License

MIT
