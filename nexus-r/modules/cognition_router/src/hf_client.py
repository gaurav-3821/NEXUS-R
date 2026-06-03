import httpx
import logging
from typing import Any

logger = logging.getLogger("nexus-r.hf_client")

class HuggingFaceClient:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.base_url = "https://huggingface.co/api/models"
    
    async def search_models(self, query: str = "", filter_tag: str = "", sort: str = "downloads", limit: int = 20) -> list[dict[str, Any]]:
        params = {
            "search": query,
            "sort": sort,
            "limit": limit,
            "full": "true"  # to get siblings
        }
        
        # If filtering for a specific type like gguf
        if filter_tag:
            params["filter"] = filter_tag
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.base_url, params=params)
                resp.raise_for_status()
                
                data = resp.json()
                
                results = []
                for item in data:
                    # Collect all gguf files if this is a gguf repo
                    ggufs = []
                    siblings = item.get("siblings", [])
                    for sib in siblings:
                        fname = sib.get("rfilename", "")
                        if fname.lower().endswith(".gguf"):
                            ggufs.append(fname)
                    
                    results.append({
                        "id": item.get("id"),
                        "author": item.get("author"),
                        "downloads": item.get("downloads", 0),
                        "likes": item.get("likes", 0),
                        "lastModified": item.get("lastModified"),
                        "tags": item.get("tags", []),
                        "pipeline_tag": item.get("pipeline_tag"),
                        "gguf_files": ggufs
                    })
                return results
                
        except Exception as e:
            logger.error(f"Failed to query HuggingFace API: {e}")
            return []
