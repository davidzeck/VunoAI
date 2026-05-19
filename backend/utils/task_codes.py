import random
import string
from datetime import datetime


def generate_task_code() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"VNH-{datetime.now().year}-{suffix}"
