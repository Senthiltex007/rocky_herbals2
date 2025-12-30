# herbalapp/utils/auto_id.py

from herbalapp.models import Member

DEFAULT_PREFIX = "rocky"

def generate_auto_id(prefix: str = DEFAULT_PREFIX) -> str:
    """
    Generate sequential auto_id with configurable prefix.
    Example: rocky004, rocky005...
    """
    last = Member.objects.order_by("-id").first()

    if last and last.auto_id and last.auto_id.startswith(prefix):
        # ✅ slice after prefix instead of replace
        num = int(last.auto_id[len(prefix):])
    else:
        num = 0

    # ✅ enforce minimum reset start at 4
    if num < 3:
        num = 3

    return f"{prefix}{num+1:03d}"

