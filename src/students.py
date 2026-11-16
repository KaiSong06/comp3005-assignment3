"""Assignment 3: a PostgreSQL student-record command-line application."""

import argparse
import os
import sys
from datetime import date

import psycopg


def connect():
    """Open the configured database; never embed credentials in source code."""
    return psycopg.connect(os.getenv("DATABASE_URL", "dbname=comp3005_a3"))


def display(rows):
    """Print all five fields in a readable table, including an empty result."""
    headers = ("student_id", "first_name", "last_name", "email", "enrollment_date")
    values = [["NULL" if value is None else str(value) for value in row]
              for row in rows]
    widths = [max(len(header), *(len(row[i]) for row in values))
              if values else len(header)
              for i, header in enumerate(headers)]
    print(" | ".join(header.ljust(widths[i]) for i, header in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in values:
        print(" | ".join(value.ljust(widths[i]) for i, value in enumerate(row)))
    print(f"({len(rows)} student(s))")


def getAllStudents():
    """Retrieve and display every student, ordered by primary key."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT student_id, first_name, last_name, email, enrollment_date "
            "FROM students ORDER BY student_id"
        ).fetchall()
    display(rows)
    return rows


def addStudent(first_name, last_name, email, enrollment_date):
    """Insert one student and return its generated ID after committing."""
    with connect() as conn:
        row = conn.execute(
            "INSERT INTO students (first_name, last_name, email, enrollment_date) "
            "VALUES (%s, %s, %s, %s) RETURNING student_id",
            (first_name, last_name, email, enrollment_date),
        ).fetchone()
    print(f"Added student {row[0]}.")
    return row[0]


def updateStudentEmail(student_id, new_email):
    """Update one student's email; return False when the ID does not exist."""
    with connect() as conn:
        row = conn.execute(
            "UPDATE students SET email = %s WHERE student_id = %s "
            "RETURNING student_id", (new_email, student_id),
        ).fetchone()
    print(f"Updated student {student_id}." if row else
          f"No student with ID {student_id}.")
    return row is not None


def deleteStudent(student_id):
    """Delete one student; return False when the ID does not exist."""
    with connect() as conn:
        row = conn.execute(
            "DELETE FROM students WHERE student_id = %s RETURNING student_id",
            (student_id,),
        ).fetchone()
    print(f"Deleted student {student_id}." if row else
          f"No student with ID {student_id}.")
    return row is not None


def main():
    """Parse a CLI command and report input/database failures without a traceback."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="Display all students")
    add = commands.add_parser("add", help="Add a student")
    add.add_argument("first_name")
    add.add_argument("last_name")
    add.add_argument("email")
    add.add_argument("enrollment_date", type=date.fromisoformat,
                     nargs="?", default=None, help="YYYY-MM-DD; omit for NULL")
    update = commands.add_parser("update-email", help="Change a student's email")
    update.add_argument("student_id", type=int)
    update.add_argument("new_email")
    delete = commands.add_parser("delete", help="Delete a student")
    delete.add_argument("student_id", type=int)
    args = parser.parse_args()

    try:
        if args.command == "list":
            getAllStudents()
        elif args.command == "add":
            addStudent(args.first_name, args.last_name, args.email,
                       args.enrollment_date)
        elif args.command == "update-email":
            if not updateStudentEmail(args.student_id, args.new_email):
                return 1
        elif args.command == "delete":
            if not deleteStudent(args.student_id):
                return 1
    except psycopg.errors.UniqueViolation:
        print("Error: that email address already exists.", file=sys.stderr)
        return 1
    except psycopg.errors.NotNullViolation:
        print("Error: first name, last name and email are required.", file=sys.stderr)
        return 1
    except psycopg.OperationalError:
        print("Error: cannot connect to PostgreSQL. Check DATABASE_URL and "
              "your database server.", file=sys.stderr)
        return 1
    except psycopg.Error as error:
        print(f"Database error: {error.diag.message_primary or 'operation failed'}",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
