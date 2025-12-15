"""
Simple S-expression parser for KiCad files.
"""

from typing import Union, List

SExpr = Union[str, List['SExpr']]


def parse(text: str) -> SExpr:
    """Parse an S-expression string into a nested list structure."""
    tokens = tokenize(text)
    result, _ = parse_tokens(tokens, 0)
    return result


def tokenize(text: str) -> List[str]:
    """Tokenize S-expression text into a list of tokens."""
    tokens = []
    i = 0
    while i < len(text):
        c = text[i]

        # Skip whitespace
        if c in ' \t\n\r':
            i += 1
            continue

        # Parentheses
        if c == '(':
            tokens.append('(')
            i += 1
            continue
        if c == ')':
            tokens.append(')')
            i += 1
            continue

        # Quoted string
        if c == '"':
            j = i + 1
            while j < len(text):
                if text[j] == '\\' and j + 1 < len(text):
                    j += 2  # Skip escaped char
                elif text[j] == '"':
                    break
                else:
                    j += 1
            tokens.append(text[i:j+1])  # Include quotes
            i = j + 1
            continue

        # Atom (unquoted token)
        j = i
        while j < len(text) and text[j] not in ' \t\n\r()':
            j += 1
        tokens.append(text[i:j])
        i = j

    return tokens


def parse_tokens(tokens: List[str], pos: int) -> tuple[SExpr, int]:
    """Parse tokens starting at pos, return (result, new_pos)."""
    if pos >= len(tokens):
        raise ValueError("Unexpected end of input")

    token = tokens[pos]

    if token == '(':
        # Parse list
        result = []
        pos += 1
        while pos < len(tokens) and tokens[pos] != ')':
            item, pos = parse_tokens(tokens, pos)
            result.append(item)
        if pos >= len(tokens):
            raise ValueError("Missing closing parenthesis")
        return result, pos + 1  # Skip ')'

    elif token == ')':
        raise ValueError("Unexpected closing parenthesis")

    else:
        # Atom - strip quotes if present
        if token.startswith('"') and token.endswith('"'):
            # Unescape the string
            s = token[1:-1]
            s = s.replace('\\n', '\n').replace('\\r', '\r').replace('\\t', '\t')
            s = s.replace('\\"', '"').replace('\\\\', '\\')
            return s, pos + 1
        return token, pos + 1


def get(expr: SExpr, key: str) -> SExpr | None:
    """Get the first child list starting with key, or None."""
    if not isinstance(expr, list):
        return None
    for item in expr:
        if isinstance(item, list) and len(item) > 0 and item[0] == key:
            return item
    return None


def get_all(expr: SExpr, key: str) -> List[SExpr]:
    """Get all child lists starting with key."""
    if not isinstance(expr, list):
        return []
    return [item for item in expr
            if isinstance(item, list) and len(item) > 0 and item[0] == key]


def get_value(expr: SExpr, key: str) -> str | None:
    """Get the value of a (key value) pair."""
    child = get(expr, key)
    if child and len(child) > 1:
        return child[1] if isinstance(child[1], str) else None
    return None
