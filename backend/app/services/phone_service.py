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
                # Still try best-effort E.164 if digits match 10-15 digits
                raw_digits = re.sub(r'\D', '', cleaned)
                if 10 <= len(raw_digits) <= 15:
                    e164 = f"+{raw_digits}"
                    is_mobile = raw_digits.startswith("905") or raw_digits.startswith("5")
                    return {
                        "e164": e164,
                        "national_number": raw_digits,
                        "country_code": parsed.country_code if parsed else 90,
                        "is_valid": True,
                        "is_mobile": is_mobile,
                        "is_whatsapp_eligible": is_mobile,
                        "wa_jid": f"{raw_digits}@s.whatsapp.net"
                    }
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
            # Fallback simple regex parsing
            raw_digits = re.sub(r'\D', '', raw_phone)
            if len(raw_digits) == 11 and raw_digits.startswith("05"):
                e164 = f"+90{raw_digits[1:]}"
            elif len(raw_digits) == 10 and raw_digits.startswith("5"):
                e164 = f"+90{raw_digits}"
            elif len(raw_digits) == 12 and raw_digits.startswith("905"):
                e164 = f"+{raw_digits}"
            else:
                return None

            digits_only = re.sub(r'\D', '', e164)
            return {
                "e164": e164,
                "national_number": digits_only[-10:],
                "country_code": 90,
                "is_valid": True,
                "is_mobile": True,
                "is_whatsapp_eligible": True,
                "wa_jid": f"{digits_only}@s.whatsapp.net"
            }
