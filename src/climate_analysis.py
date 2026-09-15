import pandas as pd


def compare_monthly_temperature(
    first_df: pd.DataFrame,
    second_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compara climatologias mensais de temperatura
    entre duas regiões.

    Os nomes das regiões são obtidos automaticamente
    da coluna 'municipality'.

    A diferença é calculada como:

        segunda região - primeira região

    Returns
    -------
    pandas.DataFrame
        Tabela mensal contendo:
        - mês;
        - nomes das regiões;
        - temperatura da primeira região;
        - temperatura da segunda região;
        - diferença entre elas.
    """

    first_regions = (
        first_df["municipality"]
        .dropna()
        .unique()
    )

    second_regions = (
        second_df["municipality"]
        .dropna()
        .unique()
    )

    if len(first_regions) != 1:
        raise ValueError(
            "first_df deve conter exatamente uma região."
        )

    if len(second_regions) != 1:
        raise ValueError(
            "second_df deve conter exatamente uma região."
        )

    first_name = first_regions[0]
    second_name = second_regions[0]

    first = (
        first_df[
            ["month", "mean_celsius"]
        ]
        .rename(
            columns={
                "mean_celsius": "first_mean_celsius"
            }
        )
    )

    second = (
        second_df[
            ["month", "mean_celsius"]
        ]
        .rename(
            columns={
                "mean_celsius": "second_mean_celsius"
            }
        )
    )

    comparison = first.merge(
        second,
        on="month",
        how="inner",
    )

    comparison["first_region"] = first_name
    comparison["second_region"] = second_name

    comparison["difference_celsius"] = (
        comparison["second_mean_celsius"]
        - comparison["first_mean_celsius"]
    )

    comparison = comparison[
        [
            "month",
            "first_region",
            "second_region",
            "first_mean_celsius",
            "second_mean_celsius",
            "difference_celsius",
        ]
    ]

    return comparison