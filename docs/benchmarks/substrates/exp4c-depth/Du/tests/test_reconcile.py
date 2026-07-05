from ledger.reconcile import Entry, settle


def test_sums_a_plain_batch():
    assert settle([Entry("a", 100), Entry("b", 50), Entry("c", 25)]) == 175


def test_empty_batch_is_zero():
    assert settle([]) == 0


def test_single_entry():
    assert settle([Entry("solo", 42)]) == 42
