import time
import secrets
import re
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

def get_client_ip(request):
    """
    Extract the client's real IP address from the request.
    Handles reverse proxies like Cloudflare, Render, Gunicorn, Nginx.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # First non-empty IP in the chain is the originating client
        parts = [p.strip() for p in x_forwarded_for.split(',') if p.strip()]
        if parts:
            return parts[0]
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


class SecurityRateLimiter:
    """
    Production-ready sliding-window rate limiter and lockout manager.
    Works with Django's configured cache backend.
    """

    @classmethod
    def check_rate_limit(cls, key: str, max_requests: int, window_seconds: int):
        """
        Check if the action identified by `key` exceeds `max_requests` in `window_seconds`.
        Returns (is_limited: bool, retry_after_seconds: int).
        """
        now = int(time.time())
        cache_key = f"rl:{key}"
        timestamps = cache.get(cache_key, [])
        valid_timestamps = [t for t in timestamps if now - t < window_seconds]

        if len(valid_timestamps) >= max_requests:
            oldest = valid_timestamps[0]
            retry_after = max(1, window_seconds - (now - oldest))
            return True, retry_after

        valid_timestamps.append(now)
        cache.set(cache_key, valid_timestamps, timeout=window_seconds + 15)
        return False, 0

    @classmethod
    def record_failure(cls, key: str, max_failures: int = 10, lockout_seconds: int = 60):
        """
        Record a failed attempt. If failures reach `max_failures`, activate lockout.
        Returns (is_now_locked: bool, failures_count: int, lockout_remaining: int).
        """
        lock_key = f"lockout:{key}"
        now = int(time.time())
        lock_until = cache.get(lock_key, 0)
        if lock_until > now:
            return True, max_failures, lock_until - now

        fail_key = f"fails:{key}"
        timestamps = cache.get(fail_key, [])
        valid = [t for t in timestamps if now - t < lockout_seconds]
        valid.append(now)
        cache.set(fail_key, valid, timeout=lockout_seconds + 15)

        if len(valid) >= max_failures:
            cache.set(lock_key, now + lockout_seconds, timeout=lockout_seconds)
            return True, len(valid), lockout_seconds

        return False, len(valid), 0

    @classmethod
    def is_locked(cls, key: str):
        """
        Check if `key` is currently locked out.
        Returns (is_locked: bool, remaining_seconds: int).
        """
        lock_key = f"lockout:{key}"
        lock_until = cache.get(lock_key, 0)
        now = int(time.time())
        if lock_until > now:
            return True, lock_until - now
        return False, 0

    @classmethod
    def clear_failures(cls, key: str):
        """Reset failures and lockouts for key (e.g. on successful login)."""
        cache.delete(f"fails:{key}")
        cache.delete(f"lockout:{key}")

    @classmethod
    def secure_compare(cls, val_a: str, val_b: str) -> bool:
        """Constant-time string comparison to prevent timing attacks."""
        if val_a is None or val_b is None:
            return False
        return secrets.compare_digest(str(val_a).strip(), str(val_b).strip())


def validate_registration_inputs(data):
    """
    Standard server-side validation for student registration inputs.
    Returns (is_valid: bool, error_message: str | None).
    """
    rollno = data.get('rollno', '').strip()
    name = data.get('name', '').strip()
    fname = data.get('fname', '').strip()
    mname = data.get('mname', '').strip()
    gender = data.get('gender', '').strip()
    contactno = data.get('contactno', '').strip()
    emailaddress = data.get('emailaddress', '').strip()
    password = data.get('password', '')
    confirmpassword = data.get('confirmpassword', '')
    program = data.get('program', '').strip()
    branch = data.get('branch', '').strip()
    year = data.get('year', '').strip()

    if not rollno:
        return False, "Please enter your Roll No."
    if len(rollno) > 20:
        return False, "Roll number is too long (maximum 20 characters)."

    if not name:
        return False, "Please enter your name."
    if not fname:
        return False, "Please enter father name."
    if not mname:
        return False, "Please enter mother name."

    if not gender:
        return False, "Please select gender."

    if not contactno:
        return False, "Please enter contact number."
    if not contactno.isdigit() or len(contactno) != 10:
        return False, "Contact number must be exactly 10 digits."

    try:
        validate_email(emailaddress)
    except ValidationError:
        return False, "Please enter a valid email address."

    if not password:
        return False, "Please enter your password."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if password != confirmpassword:
        return False, "Password and Confirm Password do not match."

    if not program or not branch or not year:
        return False, "Please select Program, Branch, and Year."

    return True, None

