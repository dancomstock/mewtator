import re
from typing import Optional, Tuple


def parse_requirement(req_string: str) -> Optional[Tuple[str, str, str]]:
    """
    Parse a requirement string like 'modname>=1.0.0' into (mod_name, operator, version).
    
    Args:
        req_string: String like 'modname>=1.0.0' or just 'modname'
        
    Returns:
        Tuple of (mod_name, operator, version) or (mod_name, '', '') if no version specified.
        Returns None if parsing failed.
    """
    if not req_string or not isinstance(req_string, str):
        return None
    
    # Match pattern: modname + optional (operator + version)
    # Operators: >=, <=, >, <, ==, !=
    pattern = r'^([a-zA-Z0-9_\-]+)\s*(>=|<=|>|<|==|!=)?\s*([0-9.]+)?$'
    match = re.match(pattern, req_string.strip())
    
    if not match:
        return None
    
    mod_name = match.group(1)
    operator = match.group(2) or ''
    version = match.group(3) or ''
    
    return (mod_name, operator, version)


def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two semantic version strings.
    
    Args:
        version1: First version string (e.g., '1.0.0')
        version2: Second version string (e.g., '1.2.0')
        
    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2
    """
    if not version1 or not version2:
        return 0
    
    # Split versions into parts and convert to integers
    try:
        parts1 = [int(p) for p in version1.split('.')]
        parts2 = [int(p) for p in version2.split('.')]
    except (ValueError, AttributeError):
        # If parsing fails, treat as equal
        return 0
    
    # Pad shorter version with zeros
    max_len = max(len(parts1), len(parts2))
    parts1.extend([0] * (max_len - len(parts1)))
    parts2.extend([0] * (max_len - len(parts2)))
    
    # Compare part by part
    for p1, p2 in zip(parts1, parts2):
        if p1 < p2:
            return -1
        elif p1 > p2:
            return 1
    
    return 0


def check_requirement(mod_version: str, operator: str, required_version: str) -> bool:
    """
    Check if a mod version satisfies a requirement.
    
    Args:
        mod_version: The version of the mod being checked
        operator: Comparison operator (>=, <=, >, <, ==, !=)
        required_version: The version to compare against
        
    Returns:
        True if requirement is satisfied, False otherwise.
        If no operator provided, returns True (no version constraint).
    """
    if not operator or not required_version:
        return True
    
    if not mod_version:
        return False
    
    cmp = compare_versions(mod_version, required_version)
    
    if operator == '>=':
        return cmp >= 0
    elif operator == '<=':
        return cmp <= 0
    elif operator == '>':
        return cmp > 0
    elif operator == '<':
        return cmp < 0
    elif operator == '==':
        return cmp == 0
    elif operator == '!=':
        return cmp != 0
    else:
        return True
