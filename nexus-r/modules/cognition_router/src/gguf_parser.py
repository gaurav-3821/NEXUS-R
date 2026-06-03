import logging
from typing import Any
import os
from pathlib import Path

logger = logging.getLogger("nexus-r.gguf_parser")

try:
    from gguf import GGUFReader
    HAVE_GGUF = True
except ImportError:
    HAVE_GGUF = False

def extract_gguf_metadata(filepath: str | Path) -> dict[str, Any]:
    if not HAVE_GGUF:
        logger.warning("gguf python package is not installed. Returning basic metadata.")
        return {"error": "gguf package missing"}
        
    try:
        if not os.path.exists(filepath):
            return {"error": "File not found"}
            
        reader = GGUFReader(filepath)
        
        # Helper to extract a value from the KV cache safely
        def get_kv(key: str) -> Any:
            try:
                field = reader.get_field(key)
                if field and len(field.parts) > 0:
                    val = field.parts[-1]
                    if isinstance(val, (list, tuple)) and len(val) > 0:
                        return val[0]
                    return val
            except Exception:
                pass
            return None

        # Extract basic architectural parameters
        arch = get_kv("general.architecture") or "unknown"
        
        # Parameter count
        param_count = get_kv("general.parameter_count")
        
        # Context length
        context_len = get_kv(f"{arch}.context_length") or get_kv("general.context_length")
        
        # Quantization (usually in the filename or we can infer it, but gguf doesn't always have it easily accessible in KV, 
        # however general.file_type gives a hint, but we might rely on filename for accuracy).
        file_type = get_kv("general.file_type")
        
        # Calculate recommended RAM (rough estimate: size of file + 20% for context and overhead)
        file_size_bytes = os.path.getsize(filepath)
        recommended_ram_bytes = file_size_bytes * 1.2
        
        # Format recommended RAM in GB
        ram_gb = round(recommended_ram_bytes / (1024**3), 1)
        if ram_gb < 1:
            ram_gb = 1
            
        return {
            "architecture": str(arch),
            "parameters": param_count,
            "context_length": context_len,
            "file_type": file_type,
            "recommended_ram_gb": ram_gb,
            "recommended_vram_gb": max(1, ram_gb - 2) # just a heuristic
        }
        
    except Exception as e:
        logger.error(f"Error parsing GGUF metadata for {filepath}: {e}")
        return {"error": str(e)}
