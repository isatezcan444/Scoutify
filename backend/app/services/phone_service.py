import re
from typing import Optional, Dict, Any
import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberType

class PhoneService:
    """
    Phone number normalization, validation and WhatsApp JID formatting.
    Defaults to Turkey (TR) region if no international country code is specified.
    """

    DEFAULT_REGION = "TR"

    @staticmethod
    def mask_for_log(phone_e164: Optional[str]) -> str:
        """PII-safe phone rendering for logs: keeps routing prefix + last 2 digits."""
        if not phone_e164:
            return "—"
        visible = str(phone_e164)
        if len(visible) <= 6:
            return "****"
        return f"{visible[:4]}****{visible[-2:]}"

    @classmethod
    def clean_raw_number(cls, raw: str) -> str:
        """Removes all non-digit characters except leading plus."""
        if not raw:
            return ""
        raw = raw.strip()
        # Keep leading + if present
        has_plus = raw.startswith("+")
        digits = re.sub(r'\D', '', raw)
        return f"+{digits}" if has_plus else digits

    @classmethod
    def normalize_to_e164(cls, raw_phone: str, default_region: str = DEFAULT_REGION) -> Optional[Dict[str, Any]]:
        """
        Parses raw phone string and converts to E.164 (+905321234567).
        Returns a dict with metadata:
        {
            "e164": "+905321234567",
            "national_number": "5321234567",
            "country_code": 90,
            "is_valid": True,
            "is_mobile": True,
            "is_whatsapp_eligible": True,
            "wa_jid": "905321234567@s.whatsapp.net"
        }
        """
        if not raw_phone:
            return None

        cleaned = cls.clean_raw_number(raw_phone)
        if not cleaned:
            return None

        try:
            # If Turkish number starting with 05xx, 5xx, or 905xx
            if not cleaned.startswith("+"):
                if cleaned.startswith("00"):
                    cleaned = f"+{cleaned[2:]}"
                elif cleaned.startswith("0"):
                    cleaned = f"+90{cleaned[1:]}"
                elif cleaned.startswith("90") and len(cleaned) >= 12:
                    cleaned = f"+{cleaned}"
                elif len(cleaned) == 10 and cleaned.startswith("5"):
                    cleaned = f"+90{cleaned}"

            parsed = phonenumbers.parse(cleaned, default_region)
            is_valid = phonenumbers.is_valid_number(parsed)

            if not is_valid:
                # Fail-closed (No False Positives invariant): a digit string
                # that libphonenumber rejects is NOT a targeting number.
                # Callers keep the raw display text; phone_e164 stays None.
                return None

            e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            num_type = phonenumbers.number_type(parsed)
            
            # Mobile or Fixed Line / Mobile combo
            is_mobile = num_type in (
                PhoneNumberType.MOBILE,
                PhoneNumberType.FIXED_LINE_OR_MOBILE,
                PhoneNumberType.PERSONAL_NUMBER
            )
            
            # Additional TR specific check (5xx is always mobile in Turkey)
            national_str = str(parsed.national_number)
            if parsed.country_code == 90 and national_str.startswith("5"):
                is_mobile = True

            digits_only = re.sub(r'\D', '', e164)
            wa_jid = f"{digits_only}@s.whatsapp.net"

            return {
                "e164": e164,
                "national_number": national_str,
                "country_code": parsed.country_code,
                "is_valid": True,
                "is_mobile": is_mobile,
                "is_whatsapp_eligible": is_mobile,
                "wa_jid": wa_jid
            }

        except NumberParseException:
            # Fail-closed: unparseable input is not a targeting number.
            return None
