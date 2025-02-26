import datetime
import re
from pathlib import Path

import polars
import polars as pl
from ics import Calendar
from ics import Event as ICSEvent
from tqdm import tqdm

data_dir = Path(__file__).parent.parent.parent / ".data"

schema_by_csv_name = {
    r"2025Y3 Sem1 grps (auid).csv": {
        "AUID": polars.Utf8,
        "HAL": polars.Utf8,
        "CS": polars.Utf8,
        "BLS": polars.Utf8,
        "MH Option": polars.Utf8,
        "VExam Lab": polars.Utf8,
    },
    r"2025 Yr 2 Canvas grps 20250218B KS.csv": {
        "AUID": polars.Utf8,
        "SGA Groups": polars.Utf8,
        "Workshop HAL": polars.Utf8,
        "Nutrition Lab": polars.Utf8,
    },
}

output_dir = Path(__file__).parent.parent.parent / "docs"
dump_dir_by_csv_name = {
    r"2025Y3 Sem1 grps (auid).csv": output_dir / "2025" / "sem1" / "y3",
    r"2025 Yr 2 Canvas grps 20250218B KS.csv": output_dir / "2025" / "sem1" / "y2",
}

end_of_semester_date_by_csv_name = {
    r"2025Y3 Sem1 grps (auid).csv": pl.date(2025, 6, 24),
    r"2025 Yr 2 Canvas grps 20250218B KS.csv": pl.date(2025, 6, 25),
}
timetable_csv_by_csv_name = {
    r"2025Y3 Sem1 grps (auid).csv": r"MBCHB_3_timetable_250226.csv",
    r"2025 Yr 2 Canvas grps 20250218B KS.csv": r"MBCHB_2_timetable_250226.csv",
}

# Change this to re-run on different datasets
CSV_NAME = r"2025 Yr 2 Canvas grps 20250218B KS.csv"


person_df = (
    polars.read_csv(
        data_dir / CSV_NAME,
        schema=schema_by_csv_name[CSV_NAME],
    )
    .unpivot(index="AUID", value_name="Group ID")
    .drop_nulls(subset=["Group ID"])
)

event_df = polars.read_csv(
    data_dir / timetable_csv_by_csv_name[CSV_NAME],
    schema={
        "Date": polars.Utf8,  # e.g. 03 Mar 2025
        "Start Time": polars.Utf8,  # e.g. 9:00 AM
        "End Time": polars.Utf8,  # e.g. 1:00 PM
        "Venue": polars.Utf8,
        "Module": polars.Utf8,
        "Session": polars.Utf8,
        "Title": polars.Utf8,
        "Staff": polars.Utf8,
        "Group": polars.Utf8,
    },
).with_row_index(name="Event ID")

# Parse Date and Time columns
event_df = event_df.with_columns(
    [
        pl.col("Date").str.strptime(pl.Date, "%d %b %Y"),
        pl.col("Start Time").str.strptime(pl.Time, "%I:%M %p"),
        pl.col("End Time").str.strptime(pl.Time, "%I:%M %p"),
    ]
)

# Filter events to Semester 1 2025: up to 24th June 2025
event_df = event_df.filter(pl.col("Date") <= end_of_semester_date_by_csv_name[CSV_NAME])


class ParseError(Exception):
    pass


def is_group_match(group_id: str, group_str: str) -> bool:
    if not group_str:
        # Shared classes that are associated with all groups
        return True
    if group_str == "everyone":
        return True
    if group_id == group_str:
        return True

    group_category, group_id_nums = parse_group_id(group_id)
    (group_id_num,) = group_id_nums

    group_str_category, group_str_id_nums = parse_group_id(group_str)
    return (
        (group_category.upper() == group_str_category.upper())
        or (group_category == "CL" and group_str_category == "Nutrition")
    ) and (group_id_num.upper() in [i.upper() for i in group_str_id_nums])


def parse_group_id(group_id: str) -> tuple[str, list[str]]:
    # Handle a complicated case like
    # MH 5 & MH 10 & MH 12 - 13 & MH 16 - 17

    subgroup_ids = group_id.split(" & ")
    categories = []
    all_id_nums = []
    for subgroup_id in subgroup_ids:
        try:
            category, id_nums = parse_one_group_id(group_id=subgroup_id.strip())
        except ParseError:
            msg = f"Group id {group_id} is malformed"
            raise ParseError(msg)
        categories.append(category)
        all_id_nums.extend(id_nums)

    if len(set(categories)) != 1:
        msg = f"Group id {group_id} has multiple categories {categories}"
        raise NotImplementedError(msg)
    (category,) = set(categories)

    return category, all_id_nums


def parse_one_group_id(group_id: str) -> tuple[str, list[str]]:
    if " " in group_id:
        try:
            category, id_num = (
                group_id.replace(" - ", "-").removesuffix("y, z").strip().split(" ")
            )
        except ValueError as err:
            msg = f"Group id {group_id} is malformed: {err}"
            raise ParseError(msg)
        return category, parse_id_num(id_num)
    else:
        # e.g. BLS19
        # use regex for alphanum followed by digits
        match = re.match(r"([A-Z]+)(\d+)", group_id)
        if not match:
            msg = f"Group id {group_id} is malformed"
            raise ParseError(msg)
        category, id_num = match.groups()
        return category, parse_id_num(id_num)


def parse_id_num(id_num: str) -> list[str]:
    if "-" in id_num:
        start, end = id_num.split("-")
        if start.isdigit() and end.isdigit():
            ints = list(range(int(start), int(end) + 1))
            end_letter = ""
        else:
            start_digit = "".join(filter(str.isdigit, start))
            end_digit = "".join(filter(str.isdigit, end))
            start_letter = start.removeprefix(start_digit)
            end_letter = end.removeprefix(end_digit)
            if start_letter != end_letter:
                msg = f"Group id {id_num} is malformed"
                raise ParseError(msg)
            ints = list(range(int(start_digit), int(end_digit) + 1))

        return [str(i) + end_letter for i in ints]
    else:
        return [id_num]


# Find all combinations of groups matching with events
group_ids = person_df["Group ID"].drop_nulls().unique()
rows: list[tuple[str, str]] = []
for group_id in group_ids:
    for event_row in event_df.iter_rows(named=True):
        if is_group_match(group_id=group_id, group_str=event_row["Group"]):
            rows.append((group_id, event_row["Event ID"]))

# Create a DataFrame from the rows
group_df = polars.DataFrame(
    rows,
    schema={
        "Group ID": polars.Utf8,
        "Event ID": polars.UInt32,
    },
    orient="row",
)

# Join the DataFrames
assert not event_df["Event ID"].has_nulls()
assert not group_df["Event ID"].has_nulls()
assert not group_df["Group ID"].has_nulls()
assert not person_df["Group ID"].has_nulls()
joined_df = group_df.join(event_df, on="Event ID", how="full", validate="m:1")
if joined_df["Group ID"].has_nulls():
    msg = (
        f"Some events haven't been assigned to any group:\n"
        f"{joined_df.filter(pl.col('Group ID').is_null())}"
    )
    raise NotImplementedError(msg)

joined_df = joined_df.join(person_df, on="Group ID", how="full", validate="m:m")
if joined_df["Event ID"].has_nulls():
    msg = (
        f"Sometimes null events are being assigned:\n"
        f"{joined_df.filter(pl.col('Event ID').is_null())}"
    )
    raise NotImplementedError(msg)
# Drop duplicates
joined_df = joined_df.unique(subset=["Event ID", "AUID"])

uaids = person_df["AUID"].unique().to_list()

for uaid in tqdm(uaids):
    someone_df = joined_df.filter(pl.col("AUID") == uaid).sort(
        by=["Date", "Start Time"]
    )

    ics_events: list[ICSEvent] = []
    for row in someone_df.iter_rows(named=True):
        ics_event = ICSEvent(
            begin=datetime.datetime.combine(date=row["Date"], time=row["Start Time"]),
            end=datetime.datetime.combine(date=row["Date"], time=row["End Time"]),
            location=row["Venue"],
            categories=["University", row["Group ID"]]
            if row["Group ID"]
            else ["University"],
            name=row["Title"] if row["Title"] else f"{row['Session']}({row['Module']})",
        )
        if row["Title"] and not row["Staff"]:
            ics_event.description = row["Title"]
        elif row["Staff"] and not row["Title"]:
            ics_event.description = f"Staff: {row['Staff']}"
        elif row["Title"] and row["Staff"]:
            ics_event.description = f"{row['Title']} Staff: {row['Staff']}"

        ics_events.append(ics_event)

    calendar = Calendar(events=ics_events)

    filename = dump_dir_by_csv_name[CSV_NAME] / f"auid{row['AUID']}.ics"
    with open(filename, mode="w", encoding="UTF8") as my_file:
        my_file.writelines(calendar.serialize_iter())
