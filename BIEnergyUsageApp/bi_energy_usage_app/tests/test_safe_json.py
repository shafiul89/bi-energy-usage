from decimal import Decimal
import bi_energy_usage_app.utilities.safe_json as safe_json


def test_is_safe_json():
    assert safe_json.is_safe_json(5)
    assert not safe_json.is_safe_json(Decimal('5'))
