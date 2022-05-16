"""Processes data from survey-html-form plugin."""
import numpy as np
import pandas as pd

from download_tools.plugins.survey_multi_choice import explode_questionnaire_df
from download_tools.plugins.utils import get_demo_string


def process_html_demographics(raw_demographics):
    """
    Process demographics so that there's a row for each participant with columns for each demographic question.

    :param raw_demographics: raw demographics file
    :return: processed demographics
    """  # noqa: E501
    # eval field we need
    raw_demographics["responses"] = raw_demographics["responses"].apply(eval)
    # explode dataframe
    exploded_demo = explode_questionnaire_df(raw_demographics)

    # pivot demographics
    demographics = exploded_demo.pivot_table(
        values="responses",
        index="pid",
        columns="question_id",
        aggfunc=lambda x: " ".join(x),
    )

    # add dummy variables for gender
    gender_dummies = pd.get_dummies(demographics["gender"])
    demographics = demographics.join(gender_dummies)

    gender_values, gender_counts = np.unique(
        demographics["gender"],
        return_counts=True,
    )

    demo_string = get_demo_string(
        demographics["age"].apply(lambda age: float(age)), gender_counts, gender_values
    )

    return demographics, demo_string
