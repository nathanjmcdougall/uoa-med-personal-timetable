from pydantic import BaseModel


class Person(BaseModel):
    first: str
    last: str
    sga: str
    hal: str
    comlab: str

    def get_full_name(self) -> str:
        first_name = str(self.first).strip("'")
        last_name = str(self.last).strip("'")
        return f"{first_name} {last_name}"

    def get_surname_initial(self) -> str:
        return str(self.last).strip("'")[0].upper()
