import json
import timeit
from collections.abc import Callable
from typing import Any

from gyver.url import URL as GyverURL
from gyver.url import Fragment as GyverFragment
from gyver.url import Netloc as GyverNetloc
from gyver.url import Path as GyverPath
from gyver.url import Query as GyverQuery

from escudeiro.url import URL as EscudeiroURL
from escudeiro.url import Fragment as EscudeiroFragment
from escudeiro.url import Netloc as EscudeiroNetloc
from escudeiro.url import Path as EscudeiroPath
from escudeiro.url import Query as EscudeiroQuery

# Define complex components
complex_netloc = "us%26rname:pa%24sword@sub.example.com:8080"
complex_path = "/some/re%40l1y/complex/pat%23/../../with/../weird/./encoding/"
complex_query = (
    "param1=value1&param2=valu%262&param3=some%20value%20with%20spaces"
)
complex_fragment = "section%20name%20with%20encoding"


# Benchmark function
def benchmark(func: Callable[[], Any], iterations: int = 100000):
    return timeit.timeit(func, number=iterations) / iterations


results = {}

# Benchmark Netloc
results["netloc"] = {
    "gyver": benchmark(lambda: GyverNetloc(complex_netloc).encode()),
    "escudeiro": benchmark(lambda: EscudeiroNetloc(complex_netloc).encode()),
}
results["netloc"]["ratio"] = (
    results["netloc"]["gyver"] / results["netloc"]["escudeiro"]
)

# Benchmark Path (including normalize)
results["path"] = {
    "gyver": benchmark(lambda: GyverPath(complex_path).normalize().encode()),
    "escudeiro": benchmark(
        lambda: EscudeiroPath(complex_path).normalize().encode()
    ),
}
results["path"]["ratio"] = (
    results["path"]["gyver"] / results["path"]["escudeiro"]
)

# Benchmark Query
results["query"] = {
    "gyver": benchmark(lambda: GyverQuery(complex_query).encode()),
    "escudeiro": benchmark(lambda: EscudeiroQuery(complex_query).encode()),
}
results["query"]["ratio"] = (
    results["query"]["gyver"] / results["query"]["escudeiro"]
)

# Benchmark Fragment
results["fragment"] = {
    "gyver": benchmark(lambda: GyverFragment(complex_fragment).encode()),
    "escudeiro": benchmark(
        lambda: EscudeiroFragment(complex_fragment).encode()
    ),
}
results["fragment"]["ratio"] = (
    results["fragment"]["gyver"] / results["fragment"]["escudeiro"]
)

# Benchmark full URL initialization and encoding
results["url"] = {
    "gyver": benchmark(
        lambda: GyverURL(
            f"https://{complex_netloc}{complex_path}?{complex_query}#{complex_fragment}"
        ).encode()
    ),
    "escudeiro": benchmark(
        lambda: EscudeiroURL(
            f"https://{complex_netloc}{complex_path}?{complex_query}#{complex_fragment}"
        ).encode()
    ),
}
results["url"]["ratio"] = results["url"]["gyver"] / results["url"]["escudeiro"]

# Save results to JSON
with open("benchmark_results.json", "w") as f:
    json.dump(results, f, indent=4)
