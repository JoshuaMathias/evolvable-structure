"""VALIDITY: returns each case's ``bad_reference``. It must fail every case, or a check cannot tell naive behaviour from
acting by the principles. Zero model calls; it is the metric's own offline check and never a rival."""


def build(meter):
    return lambda case: case["bad_reference"]
