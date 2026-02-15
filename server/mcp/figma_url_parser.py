import re
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Tuple

class FigmaUrlParser:
    """Parse Figma share links to extract file key and node/component ID"""
    
    @staticmethod
    def parse_url(figma_url: str) -> Dict[str, Optional[str]]:
        """
        Parse a Figma URL to extract file key and node/component ID
        
        Supports formats:
        - https://www.figma.com/file/xxx/name?node-id=123-456
        - https://www.figma.com/design/xxx/name?node-id=123-456
        - https://www.figma.com/file/xxx/name?node-id=123%3A456
        - https://www.figma.com/design/xxx/name?node-id=123%3A456
        - https://www.figma.com/file/xxx/name (no node)
        - https://www.figma.com/design/xxx/name (no node)
        """
        
        result = {
            "file_key": None,
            "node_id": None,
            "component_id": None,
            "is_valid": False
        }
        
        try:
            # Parse the URL
            parsed = urlparse(figma_url)
            
            # Extract file key from path
            path_parts = parsed.path.split('/')
            
            # Find the part that looks like a file key (usually after /file/ or /design/)
            for i, part in enumerate(path_parts):
                if part in ['file', 'design'] and i + 1 < len(path_parts):
                    # The next part is the file key
                    file_key_part = path_parts[i + 1]
                    # Remove any query parameters that might be attached
                    result["file_key"] = file_key_part.split('?')[0]
                    break
            
            # If no file key found with that method, try regex
            if not result["file_key"]:
                # Pattern for Figma file keys (usually alphanumeric, 12-22 chars)
                file_key_match = re.search(r'/(?:file|design)/([a-zA-Z0-9]+)', figma_url)
                if file_key_match:
                    result["file_key"] = file_key_match.group(1)
            
            # Extract node/component ID from query parameters
            query_params = parse_qs(parsed.query)
            
            if 'node-id' in query_params:
                node_id_raw = query_params['node-id'][0]
                # Replace %3A with : if URL encoded
                node_id_raw = node_id_raw.replace('%3A', ':')
                # Replace hyphen with colon if needed
                if '-' in node_id_raw and ':' not in node_id_raw:
                    node_id_raw = node_id_raw.replace('-', ':')
                
                result["node_id"] = node_id_raw
                result["component_id"] = node_id_raw  # For compatibility
            
            # Also check for node-id in the fragment (some Figma links use #)
            if not result["node_id"] and '#' in figma_url:
                fragment_match = re.search(r'node-id=([^&]+)', figma_url)
                if fragment_match:
                    node_id_raw = fragment_match.group(1).replace('%3A', ':')
                    if '-' in node_id_raw and ':' not in node_id_raw:
                        node_id_raw = node_id_raw.replace('-', ':')
                    result["node_id"] = node_id_raw
                    result["component_id"] = node_id_raw
            
            result["is_valid"] = result["file_key"] is not None
            
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    @staticmethod
    def extract_from_share_link(share_link: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Convenience method to extract file key and component ID
        Returns (file_key, component_id)
        """
        parsed = FigmaUrlParser.parse_url(share_link)
        return parsed.get("file_key"), parsed.get("component_id")
    
    @staticmethod
    def format_for_api(file_key: str, component_id: Optional[str] = None) -> str:
        """Format back to a share link (for display)"""
        base = f"https://www.figma.com/design/{file_key}/"
        if component_id:
            # Convert : back to - for URL
            url_component = component_id.replace(':', '-')
            return f"{base}?node-id={url_component}"
        return base