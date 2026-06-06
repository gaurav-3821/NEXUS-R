import re
import logging
from ..widget_provider import WidgetProvider, WidgetResult

logger = logging.getLogger("nexus-r.calculator_widget")

NUM = r"-?(?:\d+\.?\d*|\.\d+)"
CALC_PATTERN = re.compile(
    rf"({NUM}\s*[\+\-\*/\^\%]\s*{NUM})"
    rf"(\s*[\+\-\*/\^\%]\s*{NUM})*"
)

PHONE_LIKE = re.compile(r"\b\d{3}-\d{4}\b")

class CalculatorWidget(WidgetProvider):
    def __init__(self, calculator):
        self._calculator = calculator

    async def should_run(self, context) -> bool:
        query = getattr(context, "raw_input", "") or ""
        m = CALC_PATTERN.search(query)
        if not m:
            return False
        expr = m.group(0)
        # Reject phone-number-like patterns (e.g. "555-1234")
        if PHONE_LIKE.search(expr):
            return False
        return True

    async def execute(self, context) -> WidgetResult | None:
        query = getattr(context, "raw_input", "") or ""
        match = CALC_PATTERN.search(query)
        if not match:
            return None

        expression = match.group(0).strip()
        if PHONE_LIKE.search(expression):
            return None
        try:
            result = self._calculator.evaluate(expression)
            if result is None:
                return None
            return WidgetResult(
                widget_type="calculator",
                data={"expression": expression, "result": str(result)},
                title=f"Calculation: {expression}",
                priority=7,
            )
        except Exception as e:
            logger.warning(f"Calculator failed: {e}")
        return None
