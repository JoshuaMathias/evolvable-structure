"""VALIDITY: returns each case's ``good_reference``. It must pass every case, or a check is too strict for the behaviour it
describes. Zero model calls; it is the metric's own offline check and never a rival."""


def build(meter):
    return lambda case: case["good_reference"]
