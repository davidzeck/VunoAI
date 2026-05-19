import json
import time
from typing import Callable, Type, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def parse_with_retry(
    call_fn: Callable[[], str],
    schema: Type[T],
    max_attempts: int = 3,
) -> T:
    last_error = None
    for attempt in range(max_attempts):
        try:
            raw  = call_fn()
            data = json.loads(raw)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError, Exception) as exc:
            last_error = exc
            if attempt < max_attempts - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"AI parse failed after {max_attempts} attempts: {last_error}")
