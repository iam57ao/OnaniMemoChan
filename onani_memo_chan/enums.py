from enum import StrEnum


class Step(StrEnum):
    RATING = "RATING"
    DURATION = "DURATION"
    VOLUME = "VOLUME"
    VISCOSITY = "VISCOSITY"


class Action(StrEnum):
    RATING = "r"
    DURATION = "d"
    VOLUME = "v"
    VISCOSITY = "c"
    UNDO = "u"


class DurationCode(StrEnum):
    LE5 = "LE5"
    LE10 = "LE10"
    LE30 = "LE30"
    LE60 = "LE60"
    GT60 = "GT60"


class VolumeCode(StrEnum):
    LOW = "LOW"
    MID = "MID"
    HIGH = "HIGH"


class ViscosityCode(StrEnum):
    V1 = "V1"
    V2 = "V2"
    V3 = "V3"
    V4 = "V4"
    V5 = "V5"
