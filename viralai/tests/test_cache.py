from viralai.core.cache import clear_cache, scientific_cache


def setup_function() -> None:
    clear_cache()


def test_scientific_cache_returns_same_result_for_same_input():
    calls = {"count": 0}

    @scientific_cache
    def translate(sequence: str) -> str:
        calls["count"] += 1
        return sequence[::-1]

    first = translate("ACGT")
    second = translate("ACGT")

    assert first == second == "TGCA"
    assert calls["count"] == 1  # second call was served from cache


def test_scientific_cache_distinguishes_different_inputs():
    @scientific_cache
    def echo(x: int) -> int:
        return x * 2

    assert echo(2) == 4
    assert echo(3) == 6


def test_scientific_cache_distinguishes_kwargs():
    calls = {"count": 0}

    @scientific_cache
    def compute(a: int, b: int = 1) -> int:
        calls["count"] += 1
        return a + b

    compute(1, b=2)
    compute(1, b=3)
    assert calls["count"] == 2
