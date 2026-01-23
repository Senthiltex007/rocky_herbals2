# herbalapp/utils/auto_id.py

DEFAULT_PREFIX = "rocky"

def generate_auto_id(prefix: str = DEFAULT_PREFIX) -> str:
    """
    Generate sequential auto_id with configurable prefix.
    Example: rocky001, rocky005...
    ✅ Circular import safe
    """
    # 🔹 Lazy import to avoid circular import
    from herbalapp.models import Member

    last = Member.objects.filter(auto_id__startswith=prefix).order_by("-auto_id").first()

    if last and last.auto_id:
        num = int(last.auto_id[len(prefix):])
    else:
        num = 0

    # ✅ enforce minimum reset start at 4
    if num < 3:
        num = 3

    return f"{prefix}{num+1:03d}"

