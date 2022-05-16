"""This code contains functions used to save the participant_dicts \
downloaded from the database as pandas data frames / csvs."""
import json
import re
from pathlib import Path

import dill as pickle
import numpy as np
import pandas as pd

from download_tools.labeler import Labeler


def to_snake_case(name):
    """
    Make fields snake case and match his files naming scheme.

    Taken from (presumably) Fred Callaway's fetch_data.py.
    """  # noqa: #501
    name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    name = re.sub(r"[.:/]", "_", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def get_general_participant_data(participant_dicts, labeler):
    """
    Save general participant data as a dataframe.

    :param participant_dicts: list of participant dicts from database
    :param labeler: our participant Labeler
    :return: dataframe of non-PII fields (first level of database)
    """
    general_info = pd.DataFrame(
        participant_dicts, columns=list(participant_dicts[0].keys())
    )

    # relabel pid to remove PII
    general_info["pid"] = general_info["workerid"].apply(
        lambda workerid: labeler(workerid)
    )

    # delete potential PII
    del general_info["uniqueid"]
    del general_info["assignmentid"]
    del general_info["workerid"]
    del general_info["hitid"]
    del general_info["ipaddress"]
    del general_info["datastring"]

    return general_info


def get_question_data(participant_dicts, labeler):
    """
    Save participant question data as a dataframe.

    :param participant_dicts: list of participant dicts from database
    :param labeler: our participant Labeler
    :return: dataframe of data in "questiondata" field of database
    """
    question_data_dicts = []
    for participant_dict in participant_dicts:
        # get question data for participant
        question_data_dict = json.loads(participant_dict["datastring"])["questiondata"]
        # add pid
        question_data_dict["pid"] = labeler(participant_dict["workerid"])
        # params, if it exists is a dictionary itself
        # with mouselab data is itself a dict
        if "params" in question_data_dict:
            question_data_dict.update(question_data_dict["params"])
            del question_data_dict["params"]
        question_data_dicts.append(question_data_dict)
    question_data = pd.DataFrame(question_data_dicts)
    return question_data


def get_event_data(participant_dicts, labeler):
    """
    Save participant event data as a dataframe.

    :param participant_dicts: list of participant dicts from database
    :param labeler: our participant Labeler
    :return: dataframe of data in "eventdata" field of database
    """
    event_data_dicts = []
    for participant_dict in participant_dicts:
        user_event_datas = json.loads(participant_dict["datastring"])["eventdata"]

        # add pid to each user event data
        pid = labeler(participant_dict["workerid"])

        for event_idx, user_event_data in enumerate(user_event_datas):
            user_event_data.update({"pid": pid, "event_num": event_idx})

        # extend event dicts list
        event_data_dicts.extend(user_event_datas)

    event_data = pd.DataFrame(event_data_dicts)
    return event_data


def get_trial_data(participant_dicts, labeler):
    """
    Save participant trial data as a dataframe.

    :param participant_dicts: list of participant dicts from database
    :param labeler: our participant Labeler
    :return: dataframe of data in "trialdata" field of database
    """
    participant_dfs = []
    for participant_dict in participant_dicts:
        if participant_dict["datastring"]:
            participant_df = pd.DataFrame(
                [
                    trial["trialdata"]
                    for trial in json.loads(participant_dict["datastring"])["data"]
                ]
            )
            participant_df["pid"] = labeler(
                participant_dict["workerid"]
            )  # participant_idx

            # for bonusing
            participant_df["workerid"] = participant_dict["workerid"]
            participant_df["assignmentid"] = participant_dict["assignmentid"]
            participant_dfs.append(participant_df)
    trial_data = pd.concat(participant_dfs)
    return trial_data


def get_participant_bonus(
    trial_data, question_data, general_info, labeler, bonus_function=None
):
    """
    Pull out all bonus fields from trial, questoin and general data.

    :param trial_data: dataframe outputted by get_trial_data
    :param question_data: dataframe outputted by get_question_data
    :param general_info: dataframe outputted by get_general_participant_data
    :param labeler: our participant Labeler
    :param bonus_function: anonymous function that converts a score to a bonus (what we told the participants, in the experiment code)
    :return: a dataframe with workerid, assignmentid and all bonuses (fields are 0 if nan)
    """  # noqa: #501
    if bonus_function is None:
        bonus_function = lambda row: row["score"]  # noqa: E731

    bonus_df = (
        trial_data[trial_data["trial_type"] == "mouselab-mdp"]
        .groupby(["workerid", "assignmentid"])
        .sum()["score"]
        .reset_index(drop=False)
    )
    # add pid label so we can join two dataframes
    bonus_df["pid"] = bonus_df["workerid"].apply(lambda workerid: labeler(workerid))

    question_cols = [col for col in question_data.columns if "_bonus" in col] + ["pid"]

    bonus_df = bonus_df.merge(question_data[question_cols], how="left", on="pid")
    bonus_df = bonus_df.merge(
        general_info[["pid", "bonus", "cond"]], how="left", on="pid"
    )

    bonus_df["calculated_bonus"] = bonus_df.apply(
        lambda row: bonus_function(row), axis=1
    )

    del bonus_df["pid"]  # delete pid to make sure this doesn't expose a mapping
    # set display to 0 when missing
    bonus_df = bonus_df.fillna(0)
    return bonus_df


def save_participant_files(
    participant_dicts,
    exp_name,
    labeler="mturk_id_mapping.pickle",
    save_path=None,
    bonus_function=None,
):
    """
    Save all participant files from an experiment.

    :param participant_dicts: list of participant dicts, downloaded from database (with download_from_database.download_from_database)
    :param exp_name: name of experiment (to save data under)
    :param labeler: location of existing labeler dictionary
    :param save_path: location to save data
    :param bonus_function: anonymous function that converts a score to a bonus (what we told the participants, in the experiment code)default None e.g. for questionnaire study with same bonus for every participant not needed)
    :return: Nothing, but saves data in save_path under exp_name
    """  # noqa: E501
    # make directory
    if save_path is None:
        data_path = Path(f"data/human/{exp_name}")
    else:
        data_path = Path(f"{save_path}/{exp_name}")

    data_path.mkdir(exist_ok=True, parents=True)

    with open(labeler, "rb") as f:
        pid_labels = pickle.load(f)
    pid_labeler = Labeler(already_labeled=pid_labels)

    # get general pid info
    general_info = get_general_participant_data(participant_dicts, pid_labeler)
    question_data = get_question_data(participant_dicts, pid_labeler)
    event_data = get_event_data(participant_dicts, pid_labeler)

    # save general info dataframes
    general_info.to_csv(
        data_path.joinpath("{}.csv".format("general_info")), index=False
    )
    question_data.to_csv(
        data_path.joinpath("{}.csv".format("question_data")), index=False
    )
    event_data.to_csv(data_path.joinpath("{}.csv".format("event_data")), index=False)

    trial_data = get_trial_data(participant_dicts, pid_labeler)

    # we can close labeler now
    with open(labeler, "wb") as f:
        pickle.dump(pid_labeler.labels, f)

    # get participant bonus
    bonus_df = get_participant_bonus(
        trial_data,
        question_data,
        general_info,
        pid_labeler,
        bonus_function=bonus_function,
    )

    # save participant bonus
    bonus_df.to_csv(data_path.joinpath("{}.csv".format("bonuses")), index=False)

    # prepare trial data to be saved

    # delete  PII
    del trial_data["workerid"]
    del trial_data["assignmentid"]

    # delete confusing redundant columns
    del trial_data[
        "trial_index"
    ]  # remove experiment trial index in favor of mouselab one

    # columns to snake case for compatibility with other code in the lab
    trial_data.columns = [to_snake_case(col) for col in trial_data.columns]

    # save trialdata, saving a file for each jsPsych plugin type
    for trial_type in np.unique(trial_data["trial_type"]):
        trial_data[trial_data["trial_type"] == trial_type].to_csv(
            data_path.joinpath("{}.csv".format(trial_type)), index=False
        )
