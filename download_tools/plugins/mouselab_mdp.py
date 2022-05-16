"""Processes data from mouselab-mdp plugin."""
import numpy as np


def get_subjects_with_complete_data(mouselab_data, number_of_trials_per_block):
    """
    Output list of subjects with complete data (defined by number of trials in each block).

    :param mouselab_data: mouselab dataframe, with columns 'block', 'pid' and 'internal_node_id'
    :param number_of_trials_per_block: dictionary of {block_name : number of trials}
    :return: list of subject IDs for those with complete data
    """  # noqa: E501
    complete_subjects_by_block = {}
    # for each block type
    for block, num_trials in number_of_trials_per_block.items():
        # subjects who have completed block
        curr_complete = (
            mouselab_data[mouselab_data["block"] == block]
            .groupby("pid")
            .count()["score"]
            == num_trials
        )
        curr_complete = curr_complete[curr_complete].index.to_list()
        complete_subjects_by_block[block] = curr_complete

    # get intersection, across all blocks
    complete_subjects_overall = set.intersection(
        *[set(values) for values in complete_subjects_by_block.values()]
    )
    return list(complete_subjects_overall)


def fix_trial_id(mouselab_data, reward_json, states_rewards="state_rewards"):
    """
    Fix trial ID, given original reward file.

    :param mouselab_data: mouselab dataframe with state_rewards column
    :param reward_json: json output of original file
    :param state_rewards: fields with states rewards
    :return: modified mouselab dataframe with trial_id column
    """
    data = {}

    # create mapping of ground truth rewards to trial index
    for reward in reward_json:
        string_reward = [f"{entry:.2f}" for entry in reward["stateRewards"]]
        data["".join(string_reward)] = reward["trial_id"]

    # first node is treated as "" in human data, but 0 in json reward data
    mouselab_data["trial_id"] = mouselab_data[states_rewards].apply(
        lambda state_rewards: data[
            "".join([f"{entry:.2f}" for entry in [0] + state_rewards[1:]])
        ]
    )
    return mouselab_data


def preprocess_mouselab_data(raw_mouselab, number_of_trials_per_block, ground_truths):
    """
    Preprocess mouselab data.

    :param raw_mouselab: raw mouselab df
    :param number_of_trials_per_block: dictionary of {block_name : number of trials} or {run :  {block_name : number of trials} ...}
    :param ground_truths: json output of original file
    :return: dataframe for only those with complete data
    """  # noqa: E501
    raw_mouselab["state_rewards"] = raw_mouselab["state_rewards"].apply(eval)
    raw_mouselab["queries"] = raw_mouselab["queries"].apply(eval)
    raw_mouselab["rewards"] = raw_mouselab["rewards"].apply(eval)

    mouselab_data = fix_trial_id(raw_mouselab, ground_truths)

    if np.all([isinstance(v, dict) for v in number_of_trials_per_block.values()]):
        completed_subjects = []
        for k, v in number_of_trials_per_block.items():
            completed_subjects.extend(
                get_subjects_with_complete_data(
                    mouselab_data[mouselab_data["run"] == k], v
                )
            )
    else:
        completed_subjects = get_subjects_with_complete_data(
            mouselab_data, number_of_trials_per_block
        )

    # take only subset with complete data
    mouselab_data = mouselab_data[
        mouselab_data["pid"].isin(completed_subjects)
    ].reset_index(drop=True)

    # a subject quit early and then started again,
    # or finished and then tried to do the task again if this fails
    # (-> don't want to bonus them based on 50 vs 30 trials)
    assert (
        len(
            np.unique(
                mouselab_data.groupby(["pid", "trial_index"]).count()["trial_type"]
            )
        )
        == 1
    )
    return mouselab_data


def add_click_count_columns(processed_mouselab, click_type_dict):
    """
    Add click count columns to moueslab dataframe.

    :param processed_mouselab:
    :param click_type_dict:
    :return:
    """
    processed_mouselab["num_nodes"] = processed_mouselab["queries"].apply(
        lambda query: len(query["click"]["state"]["target"])
    )
    for click_type, clicks in click_type_dict.items():
        processed_mouselab[f"num_{click_type}"] = processed_mouselab["queries"].apply(
            lambda query: len(
                set(query["click"]["state"]["target"]).intersection(set(clicks))
            )
        )
    return processed_mouselab
