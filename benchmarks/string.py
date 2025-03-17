import random
import string
import timeit
from collections.abc import Callable
from typing import Any

import gyver.misc.strings as gyver
from escudeiro_pyrs import strings as escudeiro


def generate_random_string(length: int = 50) -> str:
    return "".join(
        random.choices(string.ascii_letters + string.digits + "-_ ", k=length)
    )


def benchmark(func: Callable[..., Any], *args: Any, **kwargs: Any) -> float:
    return timeit.timeit(lambda: func(*args, **kwargs), number=100000)


test_cases = {
    "replace_all": (generate_random_string(), {"a": "@", "e": "3"}),
    "to_snake": (generate_random_string(),),
    "to_camel": (generate_random_string(),),
    "to_pascal": (generate_random_string(),),
    "to_kebab": (generate_random_string(), True),
    "comma_separator": ("hello, world, 'this, is', a test",),
    "sentence": (generate_random_string(),),
    "exclamation": (generate_random_string(),),
    "question": (generate_random_string(),),
}

results = {}

for func_name, args in test_cases.items():
    gyver_func = getattr(gyver, func_name)
    escudeiro_func = getattr(escudeiro, func_name)

    gyver_time = benchmark(gyver_func, *args)
    escudeiro_time = benchmark(escudeiro_func, *args)
    ratio = gyver_time / escudeiro_time if gyver_time else float("inf")

    results[func_name] = {
        "gyver": gyver_time,
        "escudeiro": escudeiro_time,
        "ratio": ratio,
    }

# Save results
with open("benchmark_results.txt", "w") as f:
    for func, times in results.items():
        f.write(f"{func}: {times}\n")

print("Benchmarking complete. Results saved to benchmark_results.txt.")
