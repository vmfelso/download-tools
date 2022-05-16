"""Test labeler."""
import secrets
from pathlib import Path

import dill as pickle
import pytest

from download_tools.labeler import Labeler


class LabelerTestClass:
    """
    Test class for labeler.

    :param num_workers: number of fake worker ids for test.
    """

    def __init__(self, num_workers):
        """Create object of class LabelerTestClass for num_workers."""
        self.num_workers = num_workers
        self.file_name = f"data/labeler_files/test_case_{self.num_workers}.pickle"
        self.worker_ids = None
        self.remaining_workers = None
        self.construct_test_case()

    @staticmethod
    def set_up_worker_ids(num_workers=20):
        """
        Generate random fake worker ids for testing purposes.

        :param num_workers: number of fake workers to generate
        :return: list of fake worker ids, as strings
        """
        worker_ids = [secrets.token_hex(11).upper() for _ in range(num_workers)]
        return worker_ids

    @staticmethod
    def split_and_save_workers(worker_ids):  # noqa: E501
        """
        Split a list of worker ids, half are inputted to a Labeler object and half remain in a list.

        :param worker_ids: list of fake worker ids, as strings
        :return: the labeler object which the first half of IDs were fed into AND the remaining IDs as a list
        """  # noqa: #501
        num_workers = len(worker_ids)
        # second half of workers for later
        remaining_workers = worker_ids[num_workers // 2 :]

        # label first half of workers
        labeler = Labeler()
        for worker_id in worker_ids[: (num_workers // 2)]:
            labeler(worker_id)

        return labeler, remaining_workers

    def construct_test_case(self):
        """
        Construct test case file.

        :return: nothing, saves new pickle file
        """
        # make directory
        Path("data/labeler_files").mkdir(exist_ok=True, parents=True)

        file_name = Path(self.file_name)

        self.worker_ids = self.set_up_worker_ids(self.num_workers)
        labeler, self.remaining_workers = self.split_and_save_workers(self.worker_ids)

        # save labels
        with open(file_name, "wb") as f:
            pickle.dump(labeler.labels, f)

    def clean_up_test_case(self):
        """
        Remove files saved to data/labeler_files/ by construct_test_cases().

        :return: nothing
        """
        Path(self.file_name).unlink()


@pytest.fixture(params=[5, 10, 20, 40])
def test_case(request):
    """
    Constructs test cases.

    :param request: see parametrization
    :return: nothing
    """
    curr_labeler = LabelerTestClass(num_workers=request.param)
    yield curr_labeler
    curr_labeler.clean_up_test_case()


def test_keys_already_added(test_case):
    """Test whether keys added in constructing test cases exist."""
    # workers in file should be the only ones not 'remaining'
    workers_in_file = set(test_case.worker_ids) - set(test_case.remaining_workers)

    # load saved labels and create Labeler object with them
    with open(test_case.file_name, "rb") as f:
        saved_labels = pickle.load(f)
    labeler = Labeler(already_labeled=saved_labels)

    # worker ids already in labeler
    labeler_keys = set(labeler.labels.keys())

    # labeler keys and workers in file should contain the same ids
    assert labeler_keys == workers_in_file

    # the two should also be the same length
    assert len(labeler_keys) == len(workers_in_file)


def test_adding_to_existing(test_case):
    """Test whether adding to a Labeler object with existing labels works."""
    # load saved labels and create Labeler object with them
    with open(test_case.file_name, "rb") as f:
        saved_labels = pickle.load(f)
    labeler = Labeler(already_labeled=saved_labels)

    # add each worker id to the Labeler (some should already be in it)
    for worker_id in test_case.worker_ids:
        labeler(worker_id)

    # worker ids already in labeler
    labeler_keys = set(labeler.labels.keys())

    # labeler keys and worker_ids should contain the same ids
    assert labeler_keys == set(test_case.worker_ids)

    # labeler keys and worker_ids should have the same length
    assert len(labeler_keys) == len(test_case.worker_ids)
