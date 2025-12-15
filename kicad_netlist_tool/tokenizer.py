"""Simple tokenizer for estimating token counts without API dependency."""

import re
from typing import Union
from pathlib import Path


class SimpleTokenizer:
    """
    Simple tokenizer that approximates OpenAI's tokenization.
    
    This provides a good estimate without requiring API calls or heavy dependencies.
    Based on the rough approximation that:
    - 1 token ≈ 4 characters for English text
    - 1 token ≈ ¾ words
    - Technical content (like KiCad files) tends to be more token-dense
    """
    
    @staticmethod
    def count_tokens(text: str) -> int:
        """
        Estimate token count for the given text.
        
        Uses a hybrid approach:
        1. Character-based estimation (more accurate for technical content)
        2. Word-based estimation for validation
        3. Adjustments for special tokens and technical formatting
        """
        if not text:
            return 0
            
        # Remove excessive whitespace but preserve structure
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Character-based estimation (primary method)
        # Technical files like KiCad tend to be more token-dense than natural language
        char_tokens = len(text) / 3.5  # Slightly more dense than typical 4 chars/token
        
        # Word-based estimation (for validation)
        words = text.split()
        word_tokens = len(words) * 1.3  # Technical terms tend to be tokenized into more pieces
        
        # Special token adjustments
        special_chars = len(re.findall(r'[(){}\[\]<>"\':;,.]', text))
        special_tokens = special_chars * 0.1  # Some punctuation creates additional tokens
        
        # Take the higher estimate (more conservative for technical content)
        estimated_tokens = int(max(char_tokens, word_tokens) + special_tokens)
        
        return estimated_tokens
    
    @staticmethod
    def count_file_tokens(file_path: Union[str, Path]) -> int:
        """Count tokens in a file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return SimpleTokenizer.count_tokens(content)
        except Exception:
            return 0
    
    @staticmethod
    def get_file_size(file_path: Union[str, Path]) -> int:
        """Get file size in bytes."""
        try:
            return Path(file_path).stat().st_size
        except Exception:
            return 0
    
    @staticmethod
    def format_number(num: int) -> str:
        """Format number with thousands separators."""
        return f"{num:,}"
    
    @staticmethod
    def calculate_reduction(before: int, after: int) -> float:
        """Calculate percentage reduction."""
        if before == 0:
            return 0.0
        return ((before - after) / before) * 100
    
    @staticmethod
    def format_reduction(reduction: float) -> str:
        """Format reduction percentage."""
        return f"{reduction:.1f}%"


class TokenStats:
    """Container for token statistics."""
    
    def __init__(self):
        self.original_tokens = 0
        self.original_size = 0
        self.compressed_tokens = 0
        self.compressed_size = 0
        self.file_count = 0
        self.component_count = 0
        self.net_count = 0
        self.connection_count = 0
        
    @property
    def token_reduction(self) -> float:
        """Calculate token reduction percentage."""
        return SimpleTokenizer.calculate_reduction(self.original_tokens, self.compressed_tokens)
    
    @property
    def size_reduction(self) -> float:
        """Calculate size reduction percentage."""
        return SimpleTokenizer.calculate_reduction(self.original_size, self.compressed_size)
    
    def update_from_files(self, original_files: list, compressed_file: Path, 
                         components: dict, nets: dict):
        """Update stats from file analysis."""
        # Count original files
        self.original_tokens = 0
        self.original_size = 0
        self.file_count = len(original_files)
        
        for file_path in original_files:
            self.original_tokens += SimpleTokenizer.count_file_tokens(file_path)
            self.original_size += SimpleTokenizer.get_file_size(file_path)
        
        # Count compressed file
        if compressed_file.exists():
            self.compressed_tokens = SimpleTokenizer.count_file_tokens(compressed_file)
            self.compressed_size = SimpleTokenizer.get_file_size(compressed_file)
        
        # Circuit stats
        self.component_count = len(components)
        self.net_count = len(nets)
        self.connection_count = sum(len(net.connections) if hasattr(net, 'connections') else 0 
                                  for net in nets.values())
    
    def format_summary(self) -> str:
        """Format a summary string."""
        return (f"Files: {self.file_count} | "
                f"Components: {self.component_count} | "
                f"Nets: {self.net_count} | "
                f"Connections: {self.connection_count}")
    
    def __str__(self) -> str:
        """String representation of stats."""
        return (f"TokenStats(files={self.file_count}, "
                f"tokens={self.original_tokens}→{self.compressed_tokens}, "
                f"reduction={self.token_reduction:.1f}%)")