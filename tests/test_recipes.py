from coffee_sdk.models import Drink, MachineStatus
from coffee_sdk.recipes import Strength, decode_profile_blob

BASELINE_BLOB = "HgIAjAIAPAIAPAK+HgKWHgLcFAIAPAIAHgIKKAJuPAI8PAI8HgIAHgIAlgIAAACgjAIA"


def test_decodes_all_17_records():
    recipes = decode_profile_blob(BASELINE_BLOB)
    assert len(recipes) == 17


def test_latte_macchiato_matches_known_app_values():
    recipes = decode_profile_blob(BASELINE_BLOB)
    lm = recipes[Drink.LATTE_MACCHIATO]
    assert lm.water_ml == 30
    assert lm.milk_ml == 220
    assert lm.total_ml == 250
    assert lm.needs_milk is True
    assert lm.strength == Strength.STANDARD
    assert lm.high_temperature is False


def test_flat_white_matches_known_app_values():
    recipes = decode_profile_blob(BASELINE_BLOB)
    fw = recipes[Drink.FLAT_WHITE]
    assert fw.water_ml == 60
    assert fw.milk_ml == 60
    assert fw.total_ml == 120
    assert fw.needs_milk is True


def test_espresso_does_not_need_milk():
    recipes = decode_profile_blob(BASELINE_BLOB)
    assert recipes[Drink.ESPRESSO].needs_milk is False


def test_machine_status_wires_recipes_from_active_profile():
    status = MachineStatus.from_dp_status(
        [
            {"code": "last_profile", "value": "orange"},
            {"code": "profileorange", "value": BASELINE_BLOB},
        ]
    )
    assert len(status.recipes) == 17
    assert status.recipe_for(Drink.LATTE_MACCHIATO).milk_ml == 220


def test_no_recipes_when_no_active_profile():
    status = MachineStatus.from_dp_status([{"code": "switch", "value": True}])
    assert status.recipes == {}
    assert status.recipe_for(Drink.ESPRESSO) is None


def test_no_recipes_when_profile_blob_missing_for_active_profile():
    status = MachineStatus.from_dp_status([{"code": "last_profile", "value": "violet"}])
    assert status.recipes == {}
