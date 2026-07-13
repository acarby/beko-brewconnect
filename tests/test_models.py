from coffee_sdk.models import Drink, FaultFlag, MachineStatus, WorkState


def test_parses_basic_status():
    status = MachineStatus.from_dp_status(
        [
            {"code": "switch", "value": True},
            {"code": "work_state", "value": "brewing"},
            {"code": "drink_set", "value": "Espresso"},
            {"code": "water_hardness", "value": 4},
        ]
    )
    assert status.power_on is True
    assert status.work_state == WorkState.BREWING
    assert status.drink_set == Drink.ESPRESSO
    assert status.water_hardness == 4


def test_fault_flags_and_convenience_properties():
    status = MachineStatus.from_dp_status(
        [
            {"code": "fault", "value": ["Water_empty", "Residual_full"]},
        ]
    )
    assert FaultFlag.WATER_EMPTY in status.faults
    assert status.water_empty is True
    assert status.grounds_full is True
    assert status.bean_container_empty is False
    assert status.needs_attention is True


def test_no_faults_means_ok():
    status = MachineStatus.from_dp_status([{"code": "fault", "value": []}])
    assert status.needs_attention is False
    assert status.water_empty is False


def test_unknown_dp_codes_are_ignored():
    status = MachineStatus.from_dp_status(
        [
            {"code": "switch", "value": True},
            {"code": "some_future_dp_we_dont_know_about", "value": 42},
        ]
    )
    assert status.power_on is True
