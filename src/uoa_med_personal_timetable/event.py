import sqlite3

import pandera as pa


class Event(pa.DataFrameModel):
    date: str
    st: str = pa.Field(description="Start Time")
    et: str = pa.Field(description="End Time")
    venue: str
    module: str
    session: str
    title: str
    staff: str
    groupid: str


def get_event_categories(event: sqlite3.Row) -> list[str] | None:
    event_id: str = event[Event.groupid]
    if not event_id:
        return None
    return [event_id]


def get_event_description(event: sqlite3.Row) -> str:
    title = get_event_title()

    if event[Event.staff]:
        description = f"{title} Staff: {event[Event.staff]}"
    else:
        description = title

    return description


def get_event_title(event: sqlite3.Row) -> str:
    if event[Event.title]:
        return event[Event.title]
    else:
        return f"{event[Event.session]}({event[Event.module]})"
