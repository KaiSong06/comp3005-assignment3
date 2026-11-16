# COMP 3005 — Assignment 3, Question 1

Python command-line application for the PostgreSQL `students` table.

Public repository: https://github.com/KaiSong06/comp3005-assignment3

## Setup

Install Python 3.10 or newer and PostgreSQL, including its `psql` and
`createdb` command-line tools. Start PostgreSQL and use a database role
allowed to create a database. Clone the repository and run setup:

```sh
git clone https://github.com/KaiSong06/comp3005-assignment3.git
cd comp3005-assignment3
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
createdb comp3005_a3
export DATABASE_URL='dbname=comp3005_a3'
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/setup.sql
```

The setup script targets a new, empty database. It creates the table and
inserts the three supplied records in one transaction. It intentionally fails
if the table already exists, so rerunning setup cannot silently duplicate
the seed data or delete existing records.

For a server requiring a username or password, configure `DATABASE_URL`
with the appropriate PostgreSQL connection parameters, or use PostgreSQL's
`PGHOST`, `PGPORT`, `PGUSER`, and password-file facilities. Keep credentials
out of source control. The default connection uses `dbname=comp3005_a3`.

Python is interpreted, so no compilation step is needed.

## Run

```sh
python src/students.py list
python src/students.py add Alex Taylor alex.taylor@example.com 2023-09-03
python src/students.py update-email 4 alex.updated@example.com
python src/students.py list
python src/students.py delete 4
python src/students.py list
```

In a fresh database, the added student's ID is 4. Always use the ID printed
by `add` if you have already inserted other records. Omit the date to store
SQL NULL. A supplied date must be a valid `YYYY-MM-DD` date.

## Required functions

- `getAllStudents()` selects, displays and returns every row in ID order.
- `addStudent(first_name, last_name, email, enrollment_date)` inserts a row
  and returns the generated ID.
- `updateStudentEmail(student_id, new_email)` updates the matching row and
  returns whether it existed.
- `deleteStudent(student_id)` deletes the matching row and returns whether
  it existed.

All values are passed separately through Psycopg placeholders. Each function
opens a connection context, commits on success, rolls back on an exception,
and closes the connection. PostgreSQL enforces the identity primary key,
required names/email, unique email, and date type. Missing IDs and database
errors are reported without claiming the operation succeeded.

## Verification

The integration test creates a unique temporary schema in the configured
database, exercises the real PostgreSQL server, and drops only that schema
when finished. It does not modify the main `students` table.

```sh
python -m unittest discover -s tests -v
```

## Video demonstration

[Watch the demonstration (3 minutes 31 seconds)](https://drive.google.com/file/d/1HFTv5_-Nm9XkSq9QMkYOT83q1o8hoLBy/view?usp=drivesdk).

## Files

- `sql/setup.sql`: table definition and supplied initial data.
- `src/students.py`: application and command-line interface.
- `tests/test_students.py`: real-database integration checks.
- `requirements.txt`: Python dependency.
