import pandas as pd
import pytest

from src.climate_analysis import (
    compare_monthly_temperature,
)


def create_monthly_region(
    municipality: str,
    temperatures: list[float],
) -> pd.DataFrame:
    """
    Cria uma climatologia mensal artificial
    para uma única região.
    """

    return pd.DataFrame(
        {
            "municipality": [municipality] * 12,
            "month": range(1, 13),
            "mean_celsius": temperatures,
        }
    )

def test_compare_monthly_temperature():
    """
    Verifica se duas regiões são comparadas corretamente.
    """

    first = create_monthly_region(
        municipality="Region A",
        temperatures=[10.0] * 12,
    )

    second = create_monthly_region(
        municipality="Region B",
        temperatures=[12.0] * 12,
    )

    result = compare_monthly_temperature(
        first_df=first,
        second_df=second,
    )

    assert len(result) == 12

    assert (
        result["first_region"]
        .eq("Region A")
        .all()
    )

    assert (
        result["second_region"]
        .eq("Region B")
        .all()
    )

    assert (
        result["difference_celsius"]
        .eq(2.0)
        .all()
    )

def test_compare_monthly_temperature_difference_direction():
    """
    Verifica se a diferença respeita a direção:

    segunda região - primeira região
    """

    first = create_monthly_region(
        municipality="Region A",
        temperatures=[15.0] * 12,
    )

    second = create_monthly_region(
        municipality="Region B",
        temperatures=[10.0] * 12,
    )

    result = compare_monthly_temperature(
        first_df=first,
        second_df=second,
    )

    assert (
        result["difference_celsius"]
        .eq(-5.0)
        .all()
    )

def test_compare_monthly_temperature_rejects_multiple_regions():
    """
    Cada DataFrame deve representar exatamente
    uma única região.
    """

    first = pd.DataFrame(
        {
            "municipality": [
                "Region A",
                "Region X",
            ],
            "month": [
                1,
                2,
            ],
            "mean_celsius": [
                10.0,
                11.0,
            ],
        }
    )

    second = create_monthly_region(
        municipality="Region B",
        temperatures=[12.0] * 12,
    )

    with pytest.raises(
        ValueError,
        match="first_df deve conter exatamente uma região",
    ):
        compare_monthly_temperature(
            first_df=first,
            second_df=second,
        )