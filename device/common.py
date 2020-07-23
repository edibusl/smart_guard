from dataclasses import dataclass
from datetime import datetime as dt
from typing import List, Optional

from numpy import ndarray


@dataclass
class FrameObject:
    x: int
    y: int
    w: int
    h: int
    area: int


@dataclass
class MonitoredFrame:
    time: dt
    frame: ndarray
    objects: List[FrameObject]
    faces: List[FrameObject]
    score: Optional[float]
