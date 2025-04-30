import re, pathlib

step_escape = re.compile(r'\\X2\\([0-9A-Fa-f]+)\\X0\\')

def _step_decode(match: re.Match) -> str:
    hex_run = match.group(1)
    return bytes.fromhex(hex_run).decode('utf-16-be')

# read with a single-byte encoding so the backslashes survive untouched
def step_decode(raw:bytes)->str:
    return step_escape.sub(_step_decode, raw)


