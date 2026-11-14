from src.leaked_key_drill import WorkOrder


def test_cutover_requires_technician_follow_up():
    ready = WorkOrder("WO-1042", "pump-panel.jpg", "dispatched", "Inspect the seal.")
    waiting = WorkOrder("WO-1043", "pump-panel.jpg", "dispatched", "")

    assert ready.ready_for_cutover() is True
    assert waiting.ready_for_cutover() is False
