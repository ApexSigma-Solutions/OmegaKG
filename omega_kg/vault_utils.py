# omega_kg/vault_utils.py

import logging
import frontmatter
from pathlib import Path
from typing import Dict, Any, Union

logger = logging.getLogger(__name__)


class VaultUtilsError(Exception):
    """Exception raised when vault utility operations fail."""
    pass


class VaultUtils:
    """Utility class for Obsidian vault operations."""
    
    def __init__(self, vault_path: Union[str, Path]):
        """
        Initialize VaultUtils with the path to the Obsidian vault.
        
        Args:
            vault_path (Union[str, Path]): Path to the Obsidian vault directory
        """
        self.vault_path = Path(vault_path).resolve()
        if not self.vault_path.exists():
            raise VaultUtilsError(f"Vault path does not exist: {self.vault_path}")
        if not self.vault_path.is_dir():
            raise VaultUtilsError(f"Vault path is not a directory: {self.vault_path}")
    
    def resolve_path(self, note_path: Union[str, Path]) -> Path:
        """
        Resolve a note path relative to the vault.
        
        Args:
            note_path (Union[str, Path]): Path to the note file, can be relative or absolute
            
        Returns:
            Path: Resolved absolute path to the note file
            
        Raises:
            VaultUtilsError: If the resolved path is outside the vault
        """
        note_path = Path(note_path)
        
        # If it's already absolute, check if it's within the vault
        if note_path.is_absolute():
            resolved_path = note_path.resolve()
        else:
            # Resolve relative to vault
            resolved_path = (self.vault_path / note_path).resolve()
        
        # Ensure the path is within the vault
        try:
            resolved_path.relative_to(self.vault_path)
        except ValueError:
            raise VaultUtilsError(f"Note path is outside vault: {resolved_path}")
        
        return resolved_path
    
    def read_note(self, note_path: Union[str, Path]) -> tuple[Dict[str, Any], str]:
        """
        Read note file once and return metadata and content.
        
        Opens the file only once using frontmatter.load() and returns both
        the metadata (frontmatter) and content as a tuple.
        
        Args:
            note_path (Union[str, Path]): Path to the note file, can be relative or absolute
            
        Returns:
            tuple[Dict[str, Any], str]: Tuple of (metadata, content)
            
        Raises:
            VaultUtilsError: If file cannot be read or parsed
            FileNotFoundError: If the file does not exist
        """
        try:
            resolved_path = self.resolve_path(note_path)
            
            if not resolved_path.exists():
                raise FileNotFoundError(f"Note file does not exist: {resolved_path}")
            
            if not resolved_path.is_file():
                raise VaultUtilsError(f"Path is not a file: {resolved_path}")
            
            with open(resolved_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                
            logger.debug(f"Successfully read note: {resolved_path}")
            return post.metadata, post.content
            
        except FileNotFoundError:
            # Re-raise FileNotFoundError as-is
            raise
        except (OSError, IOError) as e:
            raise VaultUtilsError(f"Failed to read note file {note_path}: {e}")
        except Exception as e:
            raise VaultUtilsError(f"Unexpected error reading note {note_path}: {e}")