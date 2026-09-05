import pytest
from backend.app.services.spintax_service import SpintaxService
from backend.app.services.phone_service import PhoneService

def test_spintax_service_permutations():
    template = "{Merhaba|Selam} {name}, {harika|mükemmel} bir gün dilerim!"
    perms = SpintaxService.calculate_permutations(template)
    assert perms == 4 # 2 * 2 = 4

    # Test rendering
    sample_lead = {"name": "Ahmet Bey"}
    rendered = SpintaxService.render_template(template, sample_lead)
    assert "Ahmet Bey" in rendered
    assert ("Merhaba" in rendered or "Selam" in rendered)
    assert ("harika" in rendered or "mükemmel" in rendered)

def test_phone_service_turkish_numbers():
    # Standard 0532 format
    p1 = PhoneService.normalize_to_e164("0532 123 45 67")
    assert p1 is not None
    assert p1["e164"] == "+905321234567"
    assert p1["is_mobile"] is True
    assert p1["is_whatsapp_eligible"] is True

    # 10 digits without leading zero
    p2 = PhoneService.normalize_to_e164("5449876543")
    assert p2 is not None
    assert p2["e164"] == "+905449876543"
    assert p2["is_mobile"] is True

    # With country code +90
    p3 = PhoneService.normalize_to_e164("+90 533 111 22 33")
    assert p3 is not None
    assert p3["e164"] == "+905331112233"
    assert p3["is_mobile"] is True


def test_phone_service_strict_rejects_unverifiable():
    # Fail-closed: digit strings libphonenumber rejects are NOT targeting
    # numbers (no best-effort e164, no wa_jid fabrication).
    assert PhoneService.normalize_to_e164("12345") is None
    assert PhoneService.normalize_to_e164("+90555999999999999") is None
    assert PhoneService.normalize_to_e164("not a phone") is None
    assert PhoneService.normalize_to_e164("") is None
    assert PhoneService.normalize_to_e164(None) is None  # type: ignore[arg-type]
    # Random 555-block numbers are not valid TR mobiles
    assert PhoneService.normalize_to_e164("+9055518034063") is None


def test_canonical_display_tr_numbering_plan():
    from backend.app.services.phone_service import PhoneService as P
    # Plausible -> canonical +90 form (display only, not validity)
    assert P.canonical_display("05853684214") == "+905853684214"
    assert P.canonical_display("02164565533") == "+902164565533"
    assert P.canonical_display("+905324128241") == "+905324128241"
    assert P.canonical_display("905321112233") == "+905321112233"
    assert P.canonical_display("08503451212") == "+908503451212"
    assert P.canonical_display("0532 123 45 67") == "+905321234567"
    # Implausible -> None (never displayed as callable)
    assert P.canonical_display("04069752897") is None   # invalid area 406
    assert P.canonical_display("12345") is None
    assert P.canonical_display("+90555999999999999") is None
    assert P.canonical_display("+491511234567") is None  # foreign
    assert P.canonical_display("") is None
    assert P.canonical_display(None) is None
    assert P.canonical_display("not a phone") is None
