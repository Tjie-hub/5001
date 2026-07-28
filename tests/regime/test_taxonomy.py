from research.regime import taxonomy as tx


def test_primary_regimes_are_the_three_class_set():
    assert tx.PRIMARY_REGIMES == ("BULL", "BEAR", "SIDEWAYS")


def test_declarable_axes_are_vol_and_liq_with_tier_labels():
    assert tx.DECLARABLE_AXES == ("vol", "liq")
    assert tx.AXIS_TIERS["vol"] == ("HIGH_VOL", "LOW_VOL")
    assert tx.AXIS_TIERS["liq"] == ("HIGH_LIQ", "LOW_LIQ")


def test_subcell_label_composes_regime_and_tier():
    assert tx.subcell_label("BULL", "HIGH_VOL") == "BULL::HIGH_VOL"


def test_regime_is_primary_vol_is_declarable():
    assert tx.is_primary("BULL") is True
    assert tx.is_primary("HIGH_VOL") is False
    assert tx.is_declarable_axis("vol") is True
    assert tx.is_declarable_axis("regime") is False
