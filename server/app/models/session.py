import enum


class SessionStatus(str, enum.Enum):
    CONFIGURING = "configuring"
    READY = "ready"
    ACTIVE = "active"
    PRESENTING = "presenting"
    Q_AND_A = "q_and_a"
    ENDING = "ending"
    COMPLETE = "complete"
    FAILED = "failed"
