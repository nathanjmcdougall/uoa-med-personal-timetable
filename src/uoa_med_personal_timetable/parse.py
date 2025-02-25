def do_line(event_id: str, *, sga: str, hal: str, comlab: str) -> bool:
    if not event_id:
        # TODO I don't know why an event wouldn't have an EventID
        return True
    if event_id.startswith("SGA"):
        return is_matching_class_code(
            timetable_class_code=event_id.removeprefix("SGA")
            .replace("& SGA", " ")
            .strip(),
            person_class_code=sga,
            is_tbl=False,
        )
    if event_id.startswith("ComLab"):
        return is_matching_class_code(
            timetable_class_code=event_id.removeprefix("ComLab").strip(),
            person_class_code=comlab,
            is_tbl=False,
        )
    if event_id == "6B-15B":
        event_id = "Tbl " + event_id
    if event_id.startswith("Tbl"):
        return is_matching_class_code(
            timetable_class_code=event_id.removeprefix("Tbl")
            .replace("& Tbl", " ")
            .strip(),
            person_class_code=hal,
            is_tbl=True,
        )
    msg = f"Unknown group label {event_id}"
    raise NotImplementedError(msg)


def is_matching_class_code(
    *, timetable_class_code: str, person_class_code: str, is_tbl: bool
) -> bool:
    allowed_class_codes: set[str] = {}
    buildnum = ""
    groupcode = ""
    startrange = 0
    for c in timetable_class_code + " ":
        if c.isdigit():
            buildnum += c
        elif is_tbl and c in {"A", "B"}:
            groupcode = c
            c = " "
        elif buildnum:
            v = int(buildnum)
            if c == "-":
                startrange = v
                buildnum = ""
            elif startrange:
                if c != " ":
                    msg = f"Unexpected {c} during range"
                    raise ValueError(msg)
                for x in range(startrange, v + 1):
                    allowed_class_codes.add(str(x) + groupcode)
                startrange = 0
                buildnum = ""
            else:
                allowed_class_codes.add(str(v) + groupcode)
                buildnum = ""
                if c != " ":
                    msg = f"Unexpected {c} during spec"
                    raise ValueError(msg)
    return person_class_code in allowed_class_codes
