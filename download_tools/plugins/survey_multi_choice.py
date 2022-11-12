"""Processes data from survey-multi-choice plugin."""
import fnmatch

import numpy as np
import pandas as pd


def get_mouselab_quiz_name(row, node_id_to_name_mapping):
    """
    Get quiz node ID from internal_node_id.

    :param node_id_to_name_mapping: node id, e.g. {1.0-2.0-2.0:'mouselab-pre-test} or {1.0-2.*-2.*:'mouselab-pre-test} which counts 1.0-2.1-2.1 too
    :return: value, if supplied in dictionary, otherwise np.nan
    """  # noqa: E501
    for node_id, name in node_id_to_name_mapping.items():
        if fnmatch.fnmatch(row["internal_node_id"], node_id):
            return name
    return np.nan


def prepare_responses_for_explosion(row):
    """
    Prepare responses column's keys to be used as question_ids for dataframe explosion.

    :param row: dataframe row, with 'responses' column
    :return: list of question_ids
    """
    if isinstance(row["responses"], list):
        return row["responses"]
    elif isinstance(row["responses"], dict):
        if row["question_id"][0] in row["responses"]:
            # question ids match response ids
            return [row["responses"][question_id] for question_id in row["question_id"]]
        else:
            return [
                row["responses"][question_id]
                for question_id in sorted(row["responses"])
            ]
    else:
        # response ids left at Q0, Q1, ...
        return [
            row["responses"][f"Q{qidx}"]
            for qidx, question_id in enumerate(row["question_id"])
        ]


def fix_question_id_row(row):
    """
    Fix question ID for one row.

    :param row:
    :return:
    """
    if isinstance(row["question_id"], list):
        return row["question_id"]
    elif isinstance(row["responses"], dict):
        return list(row["responses"].keys())
    else:
        return [f"Q{qidx}" for qidx, _ in enumerate(row["responses"])]


def fix_question_id(df):
    """
    Fix question ID, connected to exploding surveys dataframes.

    :param df:
    :return:
    """
    if "question_id" not in df:
        df["question_id"] = np.nan

    df["question_id"] = df.apply(
        lambda row: fix_question_id_row(row),
        axis=1,
    )
    return df


def process_additional_column_to_explode(row, additional_column, default_val=np.nan):
    """
    Prepare additional column for dataframe explosion.

    :param row:
    :param additional_column:
    :param default_val:
    :return:
    """
    if isinstance(row[additional_column], list):
        return row[additional_column]
    elif isinstance(row[additional_column], dict):
        return [
            row[additional_column][question_id] for question_id in row["question_id"]
        ]
    else:
        return [default_val] * len(row["question_id"])


def explode_questionnaire_df(questionnaire_df, additional_columns={}):
    """
    Convert pandas dataframe with rows with multiple questionnaire items to rows with only one questionnaire item each.

    :param questionnaire_df: dataframe containing questionnaires (responses, question_id, etc)
    :param additional_columns: additional columns (e.g. reverse_coded) to explode
    :return: new dataframe with one questionnaire item in each row
    """  # noqa: E501
    questionnaire_df = fix_question_id(questionnaire_df)

    questionnaire_df["responses"] = questionnaire_df.apply(
        prepare_responses_for_explosion, axis=1
    )
    for additional_column, default_val in additional_columns.items():
        questionnaire_df[additional_column] = questionnaire_df.apply(
            lambda row: process_additional_column_to_explode(
                row, additional_column, default_val
            ),
            axis=1,
        )
    return questionnaire_df.explode(
        ["question_id", "responses"] + list(additional_columns.keys()),
        ignore_index=True,
    )


def get_reverse_score(scoring_sub_dictionary, resp):
    """
    Get reverse score.

    :param scoring_sub_dictionary: scoring dictionary, e.g. {"Not so much" : 1,...}
    :param resp: response given (key in dictionary)
    :return: reverse score (number)
    """
    response_values = scoring_sub_dictionary.values()
    reverse_subtract_from = max(response_values) + min(response_values)
    return reverse_subtract_from - scoring_sub_dictionary[resp]


def score_row(
    row,
    scoring_dictionary,
    open_ended=False,
    group_identifier="name",
    reverse_coded=False,
    default_open_ended=None,
    accuracy_string="correct"
):
    """
    Score survey row.

    :param row: pandas data frame row of questionnaire dataframe
    :param scoring_dictionary: many different formats will work
            e.g. {group:{question_id...}...} or  {question_id:....}
    :param open_ended: whether participants can respond in an open-ended fashion
            (when scoring by dictionary)
    :param group_identifier: group identifier to try to use with scoring_dictionary,
            e.g. "name" for questionnaire name
    :param reverse_coded: whether row is reverse coded (when scoring by dictionary)
    param default_open_ended: default score if open ended
    :param accuracy_string:
    :return: score (number)
    """
    if open_ended and not default_open_ended:
        default_open_ended = 0
        
    # if correct scoring is in jspsych data
    if not np.all(pd.isnull(row[accuracy_string])):
        if isinstance(row[accuracy_string], str):
            return int(row["responses"] == row[accuracy_string])
        elif isinstance(row[accuracy_string], bool):
            return int(row[accuracy_string])

    if row[group_identifier] in scoring_dictionary:
        # if scoring dictionary in format {"Quest":{quest.1:...}}
        scoring_sub_dictionary = scoring_dictionary[row[group_identifier]][
            row["question_id"]
        ]
    elif row["question_id"] in scoring_dictionary:
        # else in format {quest.1:...}
        scoring_sub_dictionary = scoring_dictionary[row["question_id"]]
    else:
        # no sub dictionary, return nan
        return np.nan

    if isinstance(scoring_sub_dictionary, dict):
        # if in format e.g. {'very much agree':4, 'agree':3 ...}
        if open_ended:
            # if respondents can answer things outside of the keys
            if row["responses"] not in scoring_sub_dictionary:
                return default_open_ended
        elif reverse_coded:
            # reverse coded row!
            return get_reverse_score(scoring_sub_dictionary, row["responses"])
        return scoring_sub_dictionary[row["responses"]]
    elif isinstance(scoring_sub_dictionary, list):
        # if in format ["Correct Answer 1", "Correct Answer 2"]
        return int(row["responses"] in scoring_sub_dictionary)
    else:
        # if in format "Correct Answer 1" or CorrectNumber
        return int(row["responses"] == scoring_sub_dictionary)


def get_quiz_passer_ids(
    survey_data, max_attempts=4, passing_score=4, identifying_columns=["pid", "run"]
):
    """
    Get IDs of participants who 'passed' quiz.

    :param survey_data: survey dataframe, or subset of dataframe with quiz questions already scored
    :param max_attempts: maximum number of attempts, either integer
                                        or dictionary of {quiz_name : integer}
    :param passing_score: score at which a participant "passed" the quiz, either float
                                        or dictionary of {quiz_name : float}
    :param identifying_columns: columns which form a unique id
    :return:
    """  # noqa: E501
    unique_quiz_names = np.unique(survey_data["name"])

    # if inputs are numbers, transform them to dictionaries
    if isinstance(max_attempts, int):
        max_attempts = {quiz_name: max_attempts for quiz_name in unique_quiz_names}
    if isinstance(passing_score, float) | isinstance(passing_score, int):
        passing_score = {quiz_name: passing_score for quiz_name in unique_quiz_names}

    # last attempts for each participant
    survey_data = survey_data.drop_duplicates(
        identifying_columns + ["question_id"], keep="last"
    )
    survey_data["attempt_num"] = survey_data["internal_node_id"].apply(
        lambda node_id: int(node_id.split(".")[-1]) + 1
    )

    # initiate passed ids dictionary
    passed_ids = {quiz_name: [] for quiz_name in unique_quiz_names}
    for quiz_name in unique_quiz_names:
        quiz_subset = survey_data[survey_data["name"] == quiz_name]

        passers = (
            quiz_subset.groupby(identifying_columns).sum()["score"]
            >= passing_score[quiz_name]
        )
        min_scorers = set(passers[passers].index)

        passers = (
            quiz_subset.groupby(identifying_columns).max()["attempt_num"]
            <= max_attempts[quiz_name]
        )
        min_takers = set(passers[passers].index)

        passed_ids[quiz_name] = list(min_scorers.intersection(min_takers))
    return passed_ids


def score_mouselab_questionnaires(
    mouselab_questionnaires, solutions_dict, group_identifier="name", accuracy_string="correct"
):
    """
    Score mouselab questionnaire, returning exploded, scored dataframe.

    :param mouselab_questionnaires: raw mouselab questionnaires dataframe
    :param solutions_dict: solutions to mouselab questionnaires, as dictionary
    :param group_identifier: identifier to use when interpreting solutions_dict (if used)
    :param accuracy_string:
    :return: exploded (one question per row), scored dataframe
    """  # noqa: E501
    # eval fields we need
    mouselab_questionnaires["responses"] = mouselab_questionnaires["responses"].apply(
        lambda entry: eval(entry) if not pd.isnull(entry) else entry
    )
    mouselab_questionnaires["correct"] = mouselab_questionnaires["correct"].apply(
        lambda entry: eval(entry) if not pd.isnull(entry) else entry
    )

    # reshape dataframe so each answer has its own row
    mouselab_questionnaires = explode_questionnaire_df(
        mouselab_questionnaires, additional_columns={accuracy_string: np.nan}
    )

    # score dataframe
    mouselab_questionnaires["score"] = mouselab_questionnaires.apply(
        lambda row: score_row(row, solutions_dict, group_identifier=group_identifier),
        axis=1,
    )

    # rename question ids for future pivoting
    mouselab_questionnaires["question_id"] = mouselab_questionnaires.apply(
        lambda row: row["name"] + "_" + row["question_id"], axis=1
    )

    return mouselab_questionnaires

def score_generic_questionnaires(questionnaires, solutions_dict, group_identifier, accuracy_string="correct", open_ended=None, reverse_coded=None, default_open_ended=None):
    """
    Score generic questionnaire dataframe, returning exploded, scored dataframe.

    :param raw_questionnaires: raw questionnaires dataframe
    :param solutions_dict: solutions to qestionnaires, as dictionary
    :param group_identifier: identifier to use when interpreting solutions_dict (if used)
    :param open_ended
    :param reverse_coded
    :param default_open_ended: TODO
    :return: exploded (one question per row), scored dataframe
    """  # noqa: E501
    # eval fields we need -- mandatory fields
    questionnaires["responses"] = questionnaires["responses"].apply(
        lambda entry: eval(entry) if not pd.isnull(entry) else entry
    )
    questionnaires["question_id"] = questionnaires["question_id"].apply(
        lambda entry: eval(entry) if not pd.isnull(entry) else entry
    )

    # eval possible additional fields
    additional_columns = {}
    for questionnaire_col in [accuracy_string, "questions"] +  ["reverse_coded", "open_ended"]:
        if questionnaire_col in questionnaires:
            questionnaires[questionnaire_col] = questionnaires[questionnaire_col].apply(
                lambda entry: eval(entry) if (isinstance(entry, str) and not pd.isnull(entry)) else entry
            )
        else:
            questionnaires[questionnaire_col] = np.nan
        if questionnaire_col == "reverse_coded":
            if reverse_coded is not None:
                additional_columns[questionnaire_col] = reverse_coded
            else:
                additional_columns[questionnaire_col] = False
        elif questionnaire_col == "open_ended":
            if open_ended is not None:
                additional_columns[questionnaire_col] = open_ended
            else:
                additional_columns[questionnaire_col] = False
        else:
            additional_columns[questionnaire_col] = np.nan

    # reshape dataframe so each answer has its own row
    exploded_questionnaires = explode_questionnaire_df(
        questionnaires, additional_columns=additional_columns
    )

    # score dataframe
    exploded_questionnaires["score"] = exploded_questionnaires.apply(lambda row: score_row(row, solutions_dict[row["run"]],
                                  group_identifier=group_identifier,
                                  reverse_coded=reverse_coded if reverse_coded else row["reverse_coded"],
                                  open_ended=open_ended if open_ended else row["open_ended"],
                                  default_open_ended=default_open_ended[row["name"]] if row["name"] in default_open_ended else None),
                                                                     axis=1)

    return exploded_questionnaires