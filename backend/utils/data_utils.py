import re 


def normalize_string(value: str, lowercase: bool = False) -> str:
    """
    Normalizes a string for comparison:
    - Removes all whitespace characters (spaces, tabs, newlines, etc.)
    - Optionally converts to lowercase

    Parameters:
        value (str): The string to normalize
        lowercase (bool): Whether to convert to lowercase (default: False)

    Returns:
        str: The normalized string
    """
    if not isinstance(value, str):
        value = str(value)

    # Remove all whitespace (space, newline, tab, etc.)
    normalized = re.sub(r'\s+', '', value)

    if lowercase:
        normalized = normalized.lower()

    return normalized


def strip_pem_headers(pem_str:str) -> str:
    """Strips the leading and trailing "----- * KEY -----" from the given key PEM string."""
    return normalize_string(re.sub(r'-----.*?-----', '', pem_str).strip())