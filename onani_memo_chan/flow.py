from collections.abc import Callable
from dataclasses import dataclass

from .enums import Action, DurationCode, Step, ViscosityCode, VolumeCode
from .session import Session


@dataclass(frozen=True)
class StepTransition:
    session: Session
    next_step: Step | None


ActionHandler = Callable[[Session, str], StepTransition]


def _handle_rating(session: Session, value: str) -> StepTransition:
    rating = int(value)
    if rating < 1 or rating > 5:
        raise ValueError("rating out of range")
    session.rating = rating
    session.step = Step.DURATION
    return StepTransition(session=session, next_step=Step.DURATION)


def _handle_duration(session: Session, value: str) -> StepTransition:
    session.duration_code = DurationCode(value)
    session.step = Step.VOLUME
    return StepTransition(session=session, next_step=Step.VOLUME)


def _handle_volume(session: Session, value: str) -> StepTransition:
    session.volume_code = VolumeCode(value)
    session.step = Step.VISCOSITY
    return StepTransition(session=session, next_step=Step.VISCOSITY)


def _handle_viscosity(session: Session, value: str) -> StepTransition:
    session.viscosity_code = ViscosityCode(value)
    return StepTransition(session=session, next_step=None)


ACTION_HANDLERS: dict[Action, ActionHandler] = {
    Action.RATING: _handle_rating,
    Action.DURATION: _handle_duration,
    Action.VOLUME: _handle_volume,
    Action.VISCOSITY: _handle_viscosity,
}


def apply_action(session: Session, action: Action, value: str) -> StepTransition:
    handler = ACTION_HANDLERS[action]
    return handler(session, value)
