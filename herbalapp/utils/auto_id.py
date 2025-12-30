# herbalapp/utils/member_id.py

from herbalapp.models import Member

DEFAULT_PREFIX = "rocky"

def generate_member_id(prefix: str = DEFAULT_PREFIX) -> str:
    """
    Generate sequential member_id with configurable prefix.
    Example: rocky004, rocky005...
    """
    last = Member.objects.order_by("-id").first()

    if last and last.member_id and last.member_id.startswith(prefix):
        # ✅ slice after prefix instead of replace
        num = int(last.member_id[len(prefix):])
    else:
        num = 0

    # ✅ enforce minimum reset start at 4
    if num < 3:
        num = 3

    return f"{prefix}{num+1:03d}"

