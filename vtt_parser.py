"""
VTT Transcript Parser and Cleaner

Parses VTT files, groups statements by speaker, and prepares them for LLM-based cleanup.
"""

import re
from dataclasses import dataclass
from typing import List, Dict
from pathlib import Path


@dataclass
class TranscriptSegment:
    """Represents a single VTT segment"""
    id: str
    start_time: str
    end_time: str
    speaker: str
    text: str


@dataclass
class SpeakerStatement:
    """Represents a grouped statement by a speaker"""
    speaker: str
    start_time: str
    end_time: str
    segments: List[TranscriptSegment]
    
    @property
    def full_text(self) -> str:
        """Combined text from all segments"""
        return " ".join(seg.text for seg in self.segments)


class VTTParser:
    """Parser for WebVTT files"""
    
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.segments: List[TranscriptSegment] = []
        
    def parse(self) -> List[TranscriptSegment]:
        """Parse VTT file into segments"""
        with open(self.filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Skip the WEBVTT header
        lines = content.split('\n')
        i = 0
        while i < len(lines) and not lines[i].strip().startswith('WEBVTT'):
            i += 1
        i += 1  # Skip WEBVTT line
        
        # Skip empty line after WEBVTT
        while i < len(lines) and not lines[i].strip():
            i += 1
        
        current_id = None
        current_timestamp = None
        current_text = []
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Empty line indicates end of segment
            if not line:
                if current_id and current_timestamp and current_text:
                    self._add_segment(current_id, current_timestamp, current_text)
                    current_id = None
                    current_timestamp = None
                    current_text = []
                i += 1
                continue
            
            # Check if it's a timestamp line
            if '-->' in line:
                current_timestamp = line
                i += 1
                # Collect all text lines until empty line
                while i < len(lines) and lines[i].strip():
                    current_text.append(lines[i].strip())
                    i += 1
                continue
            
            # Otherwise, it's an ID
            current_id = line
            i += 1
        
        # Don't forget the last segment
        if current_id and current_timestamp and current_text:
            self._add_segment(current_id, current_timestamp, current_text)
        
        return self.segments
    
    def _add_segment(self, segment_id: str, timestamp: str, text_lines: List[str]):
        """Add a parsed segment to the list"""
        # Parse timestamp
        match = re.match(r'(\d+:\d+:\d+\.\d+)\s*-->\s*(\d+:\d+:\d+\.\d+)', timestamp)
        if not match:
            return
        
        start_time, end_time = match.groups()
        
        # Parse speaker and text from lines
        full_text = ' '.join(text_lines)
        
        # Extract speaker from <v Speaker Name> tag
        speaker_match = re.search(r'<v\s+([^>]+)>', full_text)
        if speaker_match:
            speaker = speaker_match.group(1).strip()
            # Remove all speaker tags and extract just the text
            text = re.sub(r'<v\s+[^>]+>', '', full_text)
            text = re.sub(r'</v>', '', text)
            text = text.strip()
        else:
            speaker = "Unknown"
            text = full_text
        
        segment = TranscriptSegment(
            id=segment_id,
            start_time=start_time,
            end_time=end_time,
            speaker=speaker,
            text=text
        )
        self.segments.append(segment)


class TranscriptGrouper:
    """Groups transcript segments by speaker"""
    
    def __init__(self, segments: List[TranscriptSegment], max_gap_seconds: float = 5.0):
        self.segments = segments
        self.max_gap_seconds = max_gap_seconds
        
    def group_by_speaker(self) -> List[SpeakerStatement]:
        """Group consecutive segments by the same speaker"""
        if not self.segments:
            return []
        
        statements = []
        current_statement = [self.segments[0]]
        current_speaker = self.segments[0].speaker
        
        for segment in self.segments[1:]:
            # Check if same speaker and within time gap
            if segment.speaker == current_speaker:
                prev_end = self._time_to_seconds(current_statement[-1].end_time)
                curr_start = self._time_to_seconds(segment.start_time)
                
                if curr_start - prev_end <= self.max_gap_seconds:
                    current_statement.append(segment)
                    continue
            
            # Different speaker or gap too large - save current statement
            statement = SpeakerStatement(
                speaker=current_speaker,
                start_time=current_statement[0].start_time,
                end_time=current_statement[-1].end_time,
                segments=current_statement
            )
            statements.append(statement)
            
            # Start new statement
            current_speaker = segment.speaker
            current_statement = [segment]
        
        # Don't forget the last statement
        if current_statement:
            statement = SpeakerStatement(
                speaker=current_speaker,
                start_time=current_statement[0].start_time,
                end_time=current_statement[-1].end_time,
                segments=current_statement
            )
            statements.append(statement)
        
        return statements
    
    @staticmethod
    def _time_to_seconds(timestamp: str) -> float:
        """Convert timestamp (HH:MM:SS.mmm) to seconds"""
        parts = timestamp.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds


class TranscriptChunker:
    """Chunks grouped statements for LLM processing"""
    
    def __init__(self, statements: List[SpeakerStatement], max_tokens: int = 8000):
        self.statements = statements
        self.max_tokens = max_tokens
        
    def create_chunks(self) -> List[List[SpeakerStatement]]:
        """Create chunks of statements that fit within token limit"""
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for statement in self.statements:
            # Rough token estimate: ~4 chars per token
            statement_tokens = len(statement.full_text) // 4
            
            if current_tokens + statement_tokens > self.max_tokens and current_chunk:
                # Save current chunk and start new one
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = 0
            
            current_chunk.append(statement)
            current_tokens += statement_tokens
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks


class MarkdownExporter:
    """Exports transcript to markdown format"""
    
    @staticmethod
    def export_raw(statements: List[SpeakerStatement], output_path: str):
        """Export raw grouped statements to markdown"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Meeting Transcript\n\n")
            f.write("*Grouped by speaker with timestamps*\n\n")
            
            prev_speaker = None
            for statement in statements:
                # Add speaker header only when speaker changes
                if statement.speaker != prev_speaker:
                    if prev_speaker is not None:
                        f.write("\n")  # Extra line between different speakers
                    f.write(f"## {statement.speaker}\n\n")
                    prev_speaker = statement.speaker
                
                # Write timestamp and text
                f.write(f"**{statement.start_time}**  \n")
                f.write(f"{statement.full_text}\n\n")



def main():
    """Example usage"""
    # Parse VTT file
    parser = VTTParser('example.vtt')
    segments = parser.parse()
    print(f"Parsed {len(segments)} segments")
    
    # Group by speaker
    grouper = TranscriptGrouper(segments, max_gap_seconds=5.0)
    statements = grouper.group_by_speaker()
    print(f"Grouped into {len(statements)} statements")
    
    # Create chunks for LLM processing
    chunker = TranscriptChunker(statements, max_tokens=8000)
    chunks = chunker.create_chunks()
    print(f"Created {len(chunks)} chunks for LLM processing")
    
    # Export raw markdown
    MarkdownExporter.export_raw(statements, 'transcript_raw.md')
    print("Exported raw transcript to transcript_raw.md")
    
    # Print first few statements as preview
    print("\n--- Preview of first 3 statements ---\n")
    for statement in statements[:3]:
        print(f"{statement.speaker} ({statement.start_time}):")
        print(f"{statement.full_text[:200]}...")
        print()


if __name__ == '__main__':
    main()
