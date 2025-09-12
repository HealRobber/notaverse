import enum

class SeriesStatus(str, enum.Enum):
    active = "active"
    paused = "paused"

class EpisodeStatus(str, enum.Enum):
    planned = "planned"
    posting = "posting"
    posted  = "posted"
    failed  = "failed"

class JobType(str, enum.Enum):
    PLAN_NEXT       = "PLAN_NEXT"
    WRITE_AND_POST  = "WRITE_AND_POST"

class JobStatus(str, enum.Enum):
    queued  = "queued"
    running = "running"
    done    = "done"
    failed  = "failed"
