import re


def normalize_cnpj(value: str) -> str:
    return re.sub(r"\D", "", value)


def valid_cnpj(value: str) -> bool:
    digits = normalize_cnpj(value)

    if len(digits) != 14:
        return False

    if len(set(digits)) == 1:
        return False

    def check_digit(numbers: str, weights: list[int]) -> str:
        total = sum(
            int(number) * weight
            for number, weight in zip(numbers, weights)
        )
        remainder = total % 11
        return str(0 if remainder < 2 else 11 - remainder)

    first = check_digit(
        digits[:12],
        [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
    )

    second = check_digit(
        digits[:12] + first,
        [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
    )

    return digits[-2:] == first + second
