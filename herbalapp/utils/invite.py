import hashlib
import secrets
import string
from datetime import timedelta

from django.utils import timezone
from django.db import transaction

from herbalapp.models import InviteCode


ALPHABET = string.ascii_letters + string.digits  # a-zA-Z0-9


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _gen_code(length: int = 8) -> str:
    # 3-char OTP like LrV, njc, fxG...
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def create_invite_code(
    created_by=None,
    expires_in_minutes: int = 24 * 60,
    max_uses: int = 1,
    bind_to_phone: str = "",
    bind_to_sponsor_auto_id: str = "",
) -> str:
    """
    Creates invite code and returns the PLAIN OTP (8 chars).
    Admin list 'plain_hint' will equal OTP.
    """
    code = _gen_code(8)
    now = timezone.now()

    InviteCode.objects.create(
        code_hash=_hash_code(code),
        plain_hint=code,  # ✅ now hint == real OTP
        created_by=created_by,
        created_at=now,
        expires_at=now + timedelta(minutes=expires_in_minutes),
        used_count=0,
        max_uses=max_uses,
        is_active=True,
        bind_to_phone=(bind_to_phone or "").strip(),
        bind_to_sponsor_auto_id=(bind_to_sponsor_auto_id or "").strip(),
    )
    return code


@transaction.atomic
def validate_and_consume_invite(code: str, phone: str = "", sponsor_auto_id: str = "") -> tuple[bool, str]:
    code = (code or "").strip()
    if not code:
        return False, "OTP required"

    code_hash = _hash_code(code)

    inv = (
        InviteCode.objects.select_for_update()
        .filter(code_hash=code_hash)
        .first()
    )
    if not inv:
        return False, "Invalid OTP/Code"

    if not inv.is_active:
        return False, "OTP inactive"

    if inv.expires_at and timezone.now() > inv.expires_at:
        return False, "OTP expired"

    if inv.used_count >= inv.max_uses:
        inv.is_active = False
        inv.save(update_fields=["is_active"])
        return False, "OTP already used"

    # Optional bindings
    phone = (phone or "").strip()
    sponsor_auto_id = (sponsor_auto_id or "").strip()

    if inv.bind_to_phone and inv.bind_to_phone != phone:
        return False, "OTP not valid for this phone"

    if inv.bind_to_sponsor_auto_id and inv.bind_to_sponsor_auto_id != sponsor_auto_id:
        return False, "OTP not valid for this sponsor"

    inv.used_count += 1
    if inv.used_count >= inv.max_uses:
        inv.is_active = False
        inv.save(update_fields=["used_count", "is_active"])
    else:
        inv.save(update_fields=["used_count"])

    return True, "OK"

