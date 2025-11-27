"""
LLM-based Transcript Cleaner

Uses Azure OpenAI API to clean up transcript text by removing filler words.
"""

import os
from typing import List
from pathlib import Path
from dotenv import load_dotenv
from vtt_parser import (
    VTTParser, 
    TranscriptGrouper, 
    TranscriptChunker, 
    MarkdownExporter,
    SpeakerStatement
)

# Load environment variables from .env file
load_dotenv()

from openai import AzureOpenAI


def load_prompt(filename: str) -> str:
    """Load prompt from markdown file"""
    prompt_path = Path(__file__).parent / "prompts" / filename
    with open(prompt_path, 'r', encoding='utf-8') as f:
        content = f.read()
        # Remove markdown header if present
        lines = content.strip().split('\n')
        if lines[0].startswith('#'):
            return '\n'.join(lines[2:]).strip()  # Skip header and empty line
        return content.strip()


class TranscriptCleaner:
    """Cleans transcript using LLM"""
    
    def __init__(self, 
                 api_key: str = None, 
                 endpoint: str = None,
                 deployment: str = None,
                 api_version: str = None):
        """
        Initialize cleaner with Azure OpenAI API
        
        Args:
            api_key: Azure OpenAI API key (or set AZURE_OPENAI_API_KEY env var)
            endpoint: Azure OpenAI endpoint (or set AZURE_OPENAI_ENDPOINT env var)
            deployment: Azure OpenAI deployment name (or set AZURE_OPENAI_DEPLOYMENT env var)
            api_version: Azure OpenAI API version (or set AZURE_OPENAI_API_VERSION env var)
        """
        self.api_key = api_key or os.getenv('AZURE_OPENAI_API_KEY')
        self.endpoint = endpoint or os.getenv('AZURE_OPENAI_ENDPOINT')
        self.deployment = deployment or os.getenv('AZURE_OPENAI_DEPLOYMENT')
        self.api_version = api_version or os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
        
        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.endpoint
        )
    

    
    def clean_chunk(self, statements: List[SpeakerStatement]) -> List[str]:
        """Clean a chunk of statements"""
        # Build combined text with markers
        combined_text = ""
        for i, statement in enumerate(statements):
            combined_text += f"\n\n[STATEMENT {i}]\n"
            combined_text += f"Speaker: {statement.speaker}\n"
            combined_text += statement.full_text
        
        # Load prompts from markdown files
        system_prompt = load_prompt("system_prompt.md")
        cleaning_instructions = load_prompt("cleaning_instructions.md")
        
        # Single API call for entire chunk
        prompt = f"{cleaning_instructions}\n\n{combined_text}"
        
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse response back into individual statements
        result_text = response.choices[0].message.content.strip()
        cleaned = []
        
        # Split by statement markers
        import re
        parts = re.split(r'\[STATEMENT \d+\]', result_text)
        
        for i, part in enumerate(parts[1:], 0):  # Skip first empty part
            # Remove "Speaker: Name" line if present
            lines = part.strip().split('\n')
            text_lines = [line for line in lines if not line.startswith('Speaker:')]
            cleaned_text = '\n'.join(text_lines).strip()
            cleaned.append(cleaned_text)
        
        # Ensure we have the right number of results
        while len(cleaned) < len(statements):
            cleaned.append(statements[len(cleaned)].full_text)
        
        return cleaned[:len(statements)]



def main():
    """Main execution"""
    print("=== VTT Transcript Cleaner ===\n")
    
    # Step 1: Parse VTT file
    print("Step 1: Parsing VTT file...")
    parser = VTTParser('example.vtt')
    segments = parser.parse()
    print(f"✓ Parsed {len(segments)} segments\n")
    
    # Step 2: Group by speaker
    print("Step 2: Grouping by speaker...")
    grouper = TranscriptGrouper(segments, max_gap_seconds=5.0)
    statements = grouper.group_by_speaker()
    print(f"✓ Grouped into {len(statements)} statements\n")
    
    # Step 3: Create chunks
    print("Step 3: Creating chunks for LLM processing...")
    chunker = TranscriptChunker(statements, max_tokens=2000)
    chunks = chunker.create_chunks()
    print(f"✓ Created {len(chunks)} chunks\n")
    
    # Step 4: Export raw transcript
    print("Step 4: Exporting raw transcript...")
    MarkdownExporter.export_raw(statements, 'transcript_raw.md')
    print("✓ Exported to transcript_raw.md\n")
    
    # Step 5: Clean with LLM (when API is set up)
    print("Step 5: Cleaning transcript with LLM...")
    
    # Check for required Azure OpenAI configuration
    required_vars = {
        'AZURE_OPENAI_API_KEY': os.getenv('AZURE_OPENAI_API_KEY'),
        'AZURE_OPENAI_ENDPOINT': os.getenv('AZURE_OPENAI_ENDPOINT'),
        'AZURE_OPENAI_DEPLOYMENT': os.getenv('AZURE_OPENAI_DEPLOYMENT')
    }
    
    missing_vars = [key for key, value in required_vars.items() if not value]
    
    if missing_vars:
        print(f"⚠️  Missing Azure OpenAI configuration: {', '.join(missing_vars)}")
        print("⚠️  To enable:")
        print("   1. Install: pip install -r requirements.txt")
        print("   2. Create .env file from .env.example")
        print("   3. Add your Azure OpenAI credentials to .env")
        print("   4. Uncomment API code in clean_transcript.py")
    else:
        print("✓ Azure OpenAI configuration found")
        
    cleaner = TranscriptCleaner()
    
    # Step 6: Export progressively
    print("\nStep 6: Processing and exporting cleaned transcript...")
    output_path = 'transcript_cleaned.md'
    
    # Write header
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("# Cleaned Meeting Transcript\n\n")
    
    # Process and write each chunk progressively
    processed_count = 0
    for i, chunk in enumerate(chunks, 1):
        print(f"   Processing chunk {i}/{len(chunks)}...")
        cleaned_chunk = cleaner.clean_chunk(chunk)
        
        # Write this chunk's results immediately
        with open(output_path, 'a', encoding='utf-8') as f:
            prev_speaker = None
            for statement, cleaned in zip(chunk, cleaned_chunk):
                # Skip empty cleaned statements
                if not cleaned.strip():
                    continue
                
                # Add speaker header only when speaker changes
                if statement.speaker != prev_speaker:
                    if prev_speaker is not None:
                        f.write("\n")  # Extra line between different speakers
                    f.write(f"## {statement.speaker}\n\n")
                    prev_speaker = statement.speaker
                
                # Write cleaned text directly
                f.write(f"**{statement.start_time}**  \n")
                f.write(f"{cleaned}\n\n")
        
        processed_count += len(chunk)
        print(f"   ✓ Processed {processed_count}/{len(statements)} statements")
    
    print(f"\n✓ Exported to transcript_cleaned.md")
    
    print("\n=== Statistics ===")
    print(f"Total speakers: {len(set(s.speaker for s in statements))}")
    print(f"Total statements: {len(statements)}")
    print(f"Average statement length: {sum(len(s.full_text) for s in statements) // len(statements)} chars")
    
    # Show unique speakers
    speakers = sorted(set(s.speaker for s in statements))
    print(f"\nSpeakers in transcript:")
    for speaker in speakers:
        count = sum(1 for s in statements if s.speaker == speaker)
        print(f"  - {speaker}: {count} statements")


if __name__ == '__main__':
    main()
