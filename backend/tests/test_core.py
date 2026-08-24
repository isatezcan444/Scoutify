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
