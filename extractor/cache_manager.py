"""
Caching and optimization utilities for the PDF extractor.
"""

import hashlib
import logging
import time
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import json
import pickle

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    data: Any
    timestamp: float
    access_count: int
    file_hash: str
    file_size: int

class CacheManager:
    """Advanced caching manager for PDF extraction results."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl  # Time to live in seconds
        self.cache: Dict[str, CacheEntry] = {}
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
        
        logger.debug(f"🗄️ Cache manager initialized: max_size={max_size}, ttl={ttl}s")
    
    def get_file_hash(self, file_path: Path) -> str:
        """Generate hash for file for caching."""
        try:
            stat = file_path.stat()
            # Use file size, modification time, and name for hash
            content = f"{file_path.name}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(content.encode()).hexdigest()
        except Exception as e:
            logger.debug(f"❌ Error generating hash for {file_path}: {e}")
            return hashlib.md5(str(file_path).encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        if key not in self.cache:
            self.stats['misses'] += 1
            return None
        
        entry = self.cache[key]
        
        # Check TTL
        if time.time() - entry.timestamp > self.ttl:
            del self.cache[key]
            self.stats['misses'] += 1
            self.stats['size'] -= 1
            return None
        
        # Update access count
        entry.access_count += 1
        self.stats['hits'] += 1
        
        return entry.data
    
    def set(self, key: str, data: Any, file_path: Path = None) -> None:
        """Set item in cache."""
        # Evict if necessary
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        # Create cache entry
        file_hash = ""
        file_size = 0
        
        if file_path:
            file_hash = self.get_file_hash(file_path)
            try:
                file_size = file_path.stat().st_size
            except:
                pass
        
        entry = CacheEntry(
            data=data,
            timestamp=time.time(),
            access_count=1,
            file_hash=file_hash,
            file_size=file_size
        )
        
        self.cache[key] = entry
        self.stats['size'] += 1
    
    def _evict_lru(self) -> None:
        """Evict least recently used items."""
        if not self.cache:
            return
        
        # Find least recently used (oldest timestamp + lowest access count)
        lru_key = min(self.cache.keys(), 
                     key=lambda k: (self.cache[k].timestamp, self.cache[k].access_count))
        
        del self.cache[lru_key]
        self.stats['evictions'] += 1
        self.stats['size'] -= 1
        
        logger.debug(f"🗑️ Evicted cache entry: {lru_key}")
    
    def cleanup_expired(self) -> int:
        """Clean up expired entries."""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if current_time - entry.timestamp > self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
            self.stats['size'] -= 1
        
        if expired_keys:
            logger.debug(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = self.stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            'cache_hits': self.stats['hits'],
            'cache_misses': self.stats['misses'],
            'cache_hit_rate': hit_rate,
            'cache_evictions': self.stats['evictions'],
            'cache_size': self.stats['size'],
            'cache_max_size': self.max_size
        }
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size': 0
        }
        logger.debug("🗑️ Cache cleared")
    
    def save_to_disk(self, cache_file: Path) -> bool:
        """Save cache to disk."""
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(self.cache, f)
            logger.debug(f"💾 Cache saved to {cache_file}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save cache: {e}")
            return False
    
    def load_from_disk(self, cache_file: Path) -> bool:
        """Load cache from disk."""
        try:
            if not cache_file.exists():
                return False
            
            with open(cache_file, 'rb') as f:
                self.cache = pickle.load(f)
            
            # Update stats
            self.stats['size'] = len(self.cache)
            
            # Clean up expired entries
            self.cleanup_expired()
            
            logger.debug(f"📂 Cache loaded from {cache_file}: {len(self.cache)} entries")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to load cache: {e}")
            return False
