"""Processes data from survey-text plugin."""
import numpy as np

from download_tools.plugins.survey_multi_choice import explode_questionnaire_df
from download_tools.plugins.utils import get_demo_string


def preprocess_survey_text(survey_text):
    """
    Process dataframe such that each question has its own row.

    :param survey_text: raw survey text dataframe
    :return: processed dataframe
    """  # noqa: E501
    survey_text["responses"] = survey_text["responses"].apply(eval)
    survey_text = explode_questionnaire_df(survey_text)
    return survey_text


def get_old_demographics(
    old_demographics_df,
    valid_ids=None,
    experiment_specific_gender=None,
    manual_age_mapping=None,
):
    """
    Get demographics for old experiments (when demographics were survey-text trials and participants had to enter age and gender as free response).

    :param old_demographics_df: dataframe containing demographics from survey-text jsPsych trials, already run through preprocess_survey_text
    :param valid_ids: if list provided, demographics will only be for these participant IDs
    :param experiment_specific_gender: dictionary mapping {participant response (str): gender (str)}
    :param manual_age_mapping: dictionary mapping {participant response (str) : age (str)} :return:
    """  # noqa: E501
    # if any supplemental dictionary is None, make them empty dictionary
    # (dictionaries are mutable and should not be default arguments)
    if experiment_specific_gender is None:
        experiment_specific_gender = {}
    if manual_age_mapping is None:
        manual_age_mapping = {}

    # subset data if valid ids are provided
    if valid_ids:
        relevant_demographics_df = old_demographics_df.loc[
            old_demographics_df["pid"].isin(valid_ids),
        ].copy()
    else:
        relevant_demographics_df = old_demographics_df

    # back in the day gender was a free text response, so here we categorize those
    female_responses = [
        "female",
        "f",
        "woman",
        "i was born and raised as a female.",
        "femal",
    ]
    male_responses = ["male", "m", "man"]
    nonbinary_responses = ["non-binary", "genderfluid"]
    invalid_responses = ["57"]
    gender_dict = {
        **{key: "female" for key in female_responses},
        **{key: "male" for key in male_responses},
        **{key: "nonbinary person" for key in nonbinary_responses},
        **{key: "invalid response" for key in invalid_responses},
        **experiment_specific_gender,
    }

    relevant_demographics_df.loc[
        relevant_demographics_df["question_id"] == "Q2", "responses"
    ] = relevant_demographics_df.loc[
        relevant_demographics_df["question_id"] == "Q2", "responses"
    ].apply(
        lambda entry: gender_dict[entry.lower().strip()]
    )
    gender_values, gender_counts = np.unique(
        relevant_demographics_df.loc[
            relevant_demographics_df["question_id"] == "Q2", "responses"
        ],
        return_counts=True,
    )

    # now we categorize ages, manually parsing some responses
    relevant_demographics_df.loc[
        relevant_demographics_df["question_id"] == "Q1", "responses"
    ] = relevant_demographics_df.loc[
        relevant_demographics_df["question_id"] == "Q1", "responses"
    ].apply(
        lambda entry: manual_age_mapping[entry]
        if entry in manual_age_mapping
        else entry
    )
    ages = relevant_demographics_df.loc[
        relevant_demographics_df["question_id"] == "Q1", "responses"
    ].apply(lambda entry: float(entry))

    demographics = relevant_demographics_df.pivot_table(
        values="responses",
        index="pid",
        columns="question_id",
        aggfunc=lambda x: " ".join(x),
    )
    demo_string = get_demo_string(ages, gender_counts, gender_values)

    return demographics, demo_string
