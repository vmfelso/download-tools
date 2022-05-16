"""Provides a way to anonymize data."""


class Labeler(object):
    """
    Assign unique integer labels.

    Labeler Class extended from Fred's code:
    https://github.com/fredcallaway/psirokuturk/blob/master/bin/fetch_data.py
    """

    def __init__(self, init=(), already_labeled=None):  # noqa D107
        # done to prevent mutable default argument
        if already_labeled is None:
            already_labeled = {}

        self.labels = already_labeled
        self.keys = sorted(already_labeled, key=already_labeled.get)
        for x in init:
            self.label(x)

    def label(self, x):  # noqa D107
        if x not in self.labels:
            self.labels[x] = len(self.labels)
            self.keys.append(x)
        return self.labels[x]

    def unlabel(self, label):  # noqa D107
        return self.keys[label]

    __call__ = label
