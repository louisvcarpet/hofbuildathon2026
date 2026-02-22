from app.services.pdf_reader import parse_offer_text


def test_parse_offer_text_extracts_common_fields():
    text = """
    Role: Senior Software Engineer
    Level: Senior
    Location: NYC
    Base Salary: $210,000
    Bonus Target: 15%
    Equity Type: RSU
    Equity Amount: $120,000
    Vesting Schedule: 4y/1y cliff
    Start Date: 2026-03-01
    """

    parsed = parse_offer_text(text)

    assert parsed.role_title == "Senior Software Engineer"
    assert parsed.level == "Senior"
    assert parsed.location == "NYC"
    assert parsed.base_salary == 210000.0
    assert parsed.bonus_target == 15.0
    assert parsed.equity_type == "RSU"
    assert parsed.equity_amount == 120000.0
    assert parsed.vesting_schedule == "4y/1y cliff"
    assert parsed.start_date is not None
