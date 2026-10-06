import pytest

from appeal_agent.privacy import (
    EMAIL_TOKEN,
    NAME_TOKEN,
    PHONE_TOKEN,
    contains_personal_data,
    mask_personal_data,
)
from appeal_agent.urgency import is_urgent


@pytest.mark.parametrize(
    "phone", ["+7 701 234 56 78", "8(701)234-56-78", "+77012345678", "8 727 123 45 67"]
)
def test_phone_numbers_are_masked(phone: str) -> None:
    masked = mask_personal_data(f"Call me at {phone} please")
    assert phone not in masked
    assert PHONE_TOKEN in masked


def test_email_is_masked() -> None:
    assert mask_personal_data("write to aliya.n@mail.kz") == f"write to {EMAIL_TOKEN}"


def test_introduced_name_is_masked() -> None:
    masked = mask_personal_data("My name is Aliya Nurlanova, phone +7 701 234 56 78.")
    assert "Aliya" not in masked and "Nurlanova" not in masked
    assert NAME_TOKEN in masked and PHONE_TOKEN in masked


def test_house_numbers_and_bus_routes_are_kept() -> None:
    text = "At Abay Avenue 12 bus number 32 skipped our stop"
    assert mask_personal_data(text) == text
    assert not contains_personal_data(text)


def test_urgency_keywords() -> None:
    keywords = ["danger", "no water", "burst"]
    assert is_urgent("A pipe BURST near the school", keywords)
    assert is_urgent("There is no water since morning", keywords)
    assert not is_urgent("The bins are full", keywords)
    # Whole words only: "endangered" must not match "danger".
    assert not is_urgent("endangered trees in the park", keywords)
