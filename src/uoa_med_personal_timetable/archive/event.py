from pydantic import BaseModel, Field


class Event(BaseModel):
    date: str
    st: str = Field(description="Start Time")
    et: str = Field(description="End Time")
    venue: str
    module: str
    session: str
    title: str
    staff: str
    groupid: str

    def get_event_categories(self) -> list[str] | None:
        event_id: str = self.groupid
        if not event_id:
            return None
        return [event_id]

    def get_event_description(self) -> str:
        title = self.get_event_title()

        if self.staff:
            description = f"{title} Staff: {self.staff}"
        else:
            description = title

        return description

    def get_event_title(self) -> str:
        if self.title:
            return self.title
        else:
            return f"{self.session}({self.module})"
