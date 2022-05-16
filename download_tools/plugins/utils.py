"""Utilities for plugins."""
import numpy as np


def add_keys_to_df(df, column_of_interest, missing_key_value=np.nan):
    """
    Transform dictionary column to columns.

    :param df: any dataframe
    :param column_of_interest: a column with dictionary values in it
    :param missing_key_value: key to use, if any values are missing
    :return: transformed dataframe
    """
    unique_keys = set(
        np.concatenate(
            df[column_of_interest].apply(lambda response: list(response.keys())).values
        )
    )

    if any(col in list(df) for col in unique_keys):
        raise ValueError("At least one of unique IDs is in dataframe already")

    for key in unique_keys:
        df[key] = df[column_of_interest].apply(
            lambda responses: responses[key] if key in responses else missing_key_value
        )
    return df


def get_demo_string(ages, gender_counts, gender_values):
    """
    Ouput string for experiment demographics.

    :param ages: array of ages
    :param gender_counts: array of gender counts
    :param gender_values: array of gender values
    :return: string
    """
    age_string = "; median age {:.0f}, age range {:.0f}-{:.0f}".format(
        int(np.median(ages)), min(ages), max(ages)
    )

    gender_string = ""
    for gender in zip(gender_counts, gender_values):
        gender_string += "{} {}s, ".format(*gender)

    return gender_string[:-2] + age_string
