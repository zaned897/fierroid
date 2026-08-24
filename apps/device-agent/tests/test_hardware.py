from fierro_device.hardware import MockHardware


def test_mock_hardware_emits_stable_pair():
    hw = MockHardware(interval_s=0)
    sample = hw.read()
    assert sample.tag_id is not None
    assert sample.weight_kg is not None
    assert sample.stable is True
