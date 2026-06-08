from __future__ import annotations

from dataclasses import dataclass

__all__ = ["RouteDecision", "route_query"]

TRIVIAL = frozenset({
    "hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "bye",
    "yes", "no", "sure", "cool", "nice", "great", "awesome",
    "good morning", "good night", "how are you", "lol", "haha", "wow",
})

CODE_KEYWORDS = frozenset({
    "python", "javascript", "typescript", "code", "function", "error", "bug",
    "fix", "implement", "class", "variable", "loop", "array", "list", "dict",
    "string", "int", "float", "return", "print", "async", "await", "html",
    "css", "react", "api", "sql", "database", "git", "compile", "runtime",
    "syntax", "import", "module", "package", "npm", "pip", "docker",
    "debug", "trace", "exception", "stack",
    "analyze", "refactor", "optimize", "security", "vulnerability",
    "performance", "pipeline", "deploy", "test", "architecture",
    "automation", "monitoring", "integration", "endpoint", "middleware",
    "config", "schema", "query", "mutation", "subscription", "hook",
    "component", "state", "prop", "context", "reducer", "middleware",
})

MATH_KEYWORDS = frozenset({
    "calculate", "solve", "equation", "integral", "derivative", "sum",
    "average", "median", "probability", "statistics", "theorem", "proof",
    "formula", "algebra", "geometry", "calculus", "matrix", "vector",
    "arithmetic", "compute", "evaluate", "simplify", "differentiate",
})

CLOUD_KEYWORDS = frozenset({
    "analyze", "research", "forecast", "predict", "browse", "scrape",
    "multi-step", "browser", "navigate", "login", "authenticate",
    "csv", "financial", "security", "vulnerability",
    "audit", "compliance", "production", "deploy", "pipeline",
    "architecture", "scalable", "load test", "benchmark",
})


@dataclass
class RouteDecision:
    tier: str
    kind: str
    cost: float
    reason: str


def route_query(query: str, *, has_cloud: bool = False) -> RouteDecision:
    q = query.lower().strip()
    words = [w.strip(".,;:!?()[]{}\"'") for w in q.split()]
    word_set = {w for w in words if w}
    word_count = len(words)

    if word_count <= 3 and q.rstrip("!?.").strip() in TRIVIAL:
        return RouteDecision("T1", "local", 0.0, "Trivial greeting")

    has_code_blocks = "```" in q
    code_overlap = word_set & CODE_KEYWORDS
    is_code = has_code_blocks or len(code_overlap) >= 2

    math_overlap = word_set & MATH_KEYWORDS
    is_math = len(math_overlap) >= 1 and not is_code

    cloud_overlap = word_set & CLOUD_KEYWORDS
    cloud_count = len(cloud_overlap)
    is_long = word_count > 30
    needs_cloud = cloud_count >= 2 or (is_long and is_code) or (is_long and is_math) or word_count > 80

    if is_code:
        if needs_cloud and has_cloud:
            tier = "T4" if word_count > 50 or cloud_count >= 3 else "T3"
            cost = 0.10 if tier == "T4" else 0.02
            return RouteDecision(tier, "byok", cost, f"Code + cloud trigger")
        return RouteDecision("T2", "local", 0.002, f"Code keywords matched")

    if is_math:
        if needs_cloud and has_cloud:
            return RouteDecision("T4", "byok", 0.10, "Complex math")
        return RouteDecision("T2", "local", 0.002, "Math keywords")

    if needs_cloud and has_cloud and word_count > 15:
        return RouteDecision("T3", "byok", 0.02, "Cloud keywords")

    if word_count > 50:
        return RouteDecision("T1", "local", 0.001, "Long prompt")

    return RouteDecision("T1", "local", 0.001, "Default")
