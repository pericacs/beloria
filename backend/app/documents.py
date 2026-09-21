import re

def normalize_document(value: str | None) -> str | None:
    return re.sub(r"[.\-/\s]", "", value.upper()) if value else None

def valid_cpf(value: str) -> bool:
    if not re.fullmatch(r"\d{11}", value) or len(set(value)) == 1:
        return False
    for size in (9, 10):
        digit = (sum(int(value[i]) * (size + 1 - i) for i in range(size)) * 10) % 11
        if int(value[size]) != (0 if digit == 10 else digit):
            return False
    return True

def valid_cnpj(value: str) -> bool:
    if not re.fullmatch(r"[A-Z0-9]{12}\d{2}", value) or len(set(value)) == 1:
        return False
    numbers = [ord(c) - 48 for c in value]
    for size, weights in ((12, [5,4,3,2,9,8,7,6,5,4,3,2]), (13, [6,5,4,3,2,9,8,7,6,5,4,3,2])):
        remainder = sum(n*w for n,w in zip(numbers[:size], weights)) % 11
        if numbers[size] != (0 if remainder < 2 else 11-remainder):
            return False
    return True
