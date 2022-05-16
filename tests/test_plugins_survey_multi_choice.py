"""Test functions for preprocessing survey-multi-choice data."""
from pathlib import Path

from download_tools.plugins.survey_multi_choice import (
    explode_questionnaire_df,
    fix_question_id,
    fix_question_id_row,
    get_mouselab_quiz_name,
    get_quiz_passer_ids,
    get_reverse_score,
    prepare_responses_for_explosion,
    process_additional_column_to_explode,
    score_mouselab_questionnaires,
)


def test_get_mouselab_quiz_name():
    raise NotImplementedError


def test_prepare_responses_for_explosion(test_case):
    example_participant_dicts, experiment_name, labeller_path = test_case
    raise NotImplementedError


def test_fix_question_id_row():
    raise NotImplementedError


def test_fix_question_id():
    raise NotImplementedError


def test_process_additional_column_to_explode():
    raise NotImplementedError


def test_explode_questionnaire_df():
    raise NotImplementedError


def test_get_reverse_score():
    raise NotImplementedError


def test_score_row():
    raise NotImplementedError


def test_get_quiz_passer_ids():
    raise NotImplementedError


def test_score_mouselab_questionnaires():
    raise NotImplementedError
