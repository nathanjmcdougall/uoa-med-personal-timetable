import sqlite3

from ics import Event

from uoa_med_personal_timetable.date import fixdate2


def get_gp_visit(name, c: sqlite3.Cursor):
    # 2:00 PM,5:00 PM,Offsite,LabILA,GP Visit
    # "Student Name" TEXT, "Site" TEXT, "GP Visit date"
    sql = 'select * from gpvisit where `student name`="' + name + '"'
    rs = c.execute(sql)
    gps = rs.fetchall()
    if len(gps) == 0:
        return 0, None, None
    gp = gps[0]
    x = gp[2] + ",2:00 PM,5:00 PM," + gp[1] + ",LabILA - GP Visit\r\n"
    e = Event()
    e.begin = fixdate2(gp[2] + " 2:00 PM")
    e.end = fixdate2(gp[2] + " 5:00 PM")
    e.location = gp[1]
    e.name = "GP Visit"
    e.description = "LabILA"
    sql = 'update gpvisit set matched=1 where `student name`="' + name + '"'
    rs = c.execute(sql)
    return 1, x, e
