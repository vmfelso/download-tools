"""Code to download from database, given URI."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine


def load_database_uris(path="."):
    """
    Load file with database URIs.

    :param path: path where file is kept
    :return: nothing, loads contents of file into environment variables
    """
    env_path = Path(path).joinpath(".database_uris")

    load_dotenv(dotenv_path=env_path)


def get_hit_ids(hit_id_file_path):
    """
    Read in a text file containing a list of HIT IDs.

    :param hit_id_file_path: path to text file
    :return: (hits, exp_name), a list of hits and the experiment name
    """
    hits = open(hit_id_file_path, "rb").read().decode()
    list_of_hits = hits.replace(" ", "").replace("\n", ",").split(",")

    # if empty entry somehow made it into list of hit ids, remove it
    if "" in list_of_hits:
        list_of_hits.remove("")

    exp_name = Path(hit_id_file_path).stem
    return list_of_hits, exp_name


def get_sql_query_for_hits(hit_list):
    """
    Create a sql query for a list of hits.

    :param hit_list: list of hits as strings
    :return: query_string, an sql query, as a string
    """
    query_string = "SELECT * FROM participants WHERE ("
    for hit_idx, hit in enumerate(hit_list):
        query_string += "(participants.hitid = '{}')".format(hit)
        if hit_idx < len(hit_list) - 1:
            query_string += " or "
        else:
            query_string += ") ORDER BY Status DESC, Cond ASC, Beginexp DESC"
    return query_string


def run_sql_query(sql_query, database_uri):
    """
    Run a SQL query on a given database database.

    :param sql_query: a sql query as a string
    :param database_uri: a database uri as a string
    :return: all_data, a list of the raw data from the sql query,with a dictionary for each participant
    """  # noqa: E501
    db = create_engine(database_uri)
    results = db.execute(sql_query)
    query_data = [entry for entry in results]

    return query_data


def download_from_database(hit_id_file_path, database_uri_keys=None):
    """
    Download experiment off of database.

    :param hit_id_file_path: path to text file containing a list of all HIT IDs
    :param database_uri_keys: uri key, or list of uri keys
    :return: participant_dicts, a list containing a dictionary for each participant
    """
    # get database uri
    assert database_uri_keys is not None
    if not isinstance(database_uri_keys, list):
        database_uri_keys = [database_uri_keys]

    all_participant_dicts = []
    for database_uri_key in database_uri_keys:
        database_uri = os.environ[database_uri_key]

        # get list of HITs and experiment name
        hits, exp_name = get_hit_ids(hit_id_file_path)

        # get sql query and run it
        sql_query = get_sql_query_for_hits(hits)
        curr_participant_dicts = run_sql_query(sql_query, database_uri)

        # data string is None is participant didn't do experiment
        # (or for some reason data didn't get saved)
        all_participant_dicts.extend(
            [
                participant_dict
                for participant_dict in curr_participant_dicts
                if participant_dict["datastring"] is not None
            ]
        )

    return all_participant_dicts
