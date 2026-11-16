"""Exercise PostgreSQL constraints and CRUD in a disposable isolated schema."""

import contextlib
import io
import os
from pathlib import Path
import sys
import unittest
import uuid

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import students


class StudentIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.original_url = os.environ.get("DATABASE_URL")
        self.base_url = self.original_url or "dbname=comp3005_a3"
        self.schema = "test_students_" + uuid.uuid4().hex
        with psycopg.connect(self.base_url) as conn:
            conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema)))
        os.environ["DATABASE_URL"] = make_conninfo(
            self.base_url, options=f"-c search_path={self.schema}")
        self.addCleanup(self.cleanup)
        setup = Path(__file__).resolve().parents[1] / "sql" / "setup.sql"
        with students.connect() as conn:
            conn.execute(setup.read_text())

    def cleanup(self):
        if self.original_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = self.original_url
        with psycopg.connect(self.base_url) as conn:
            conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(
                sql.Identifier(self.schema)))

    def test_crud_persists_across_connections(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            initial = students.getAllStudents()
            self.assertEqual([row[1:4] for row in initial], [
                ("John", "Doe", "john.doe@example.com"),
                ("Jane", "Smith", "jane.smith@example.com"),
                ("Jim", "Beam", "jim.beam@example.com")])
            sid = students.addStudent("Alex", "Taylor", "alex@example.com", "2023-09-03")
            self.assertEqual(sid, 4)
            self.assertTrue(students.updateStudentEmail(sid, "updated@example.com"))
            with students.connect() as conn:
                self.assertEqual(conn.execute(
                    "SELECT email FROM students WHERE student_id=%s", (sid,)
                ).fetchone(), ("updated@example.com",))
            self.assertTrue(students.deleteStudent(sid))
            self.assertEqual(students.getAllStudents(), initial)
        self.assertIn("john.doe@example.com", output.getvalue())

    def test_duplicate_email_rolls_back_insert_and_update(self):
        with self.assertRaises(psycopg.errors.UniqueViolation):
            students.addStudent("Other", "Person", "john.doe@example.com", None)
        with self.assertRaises(psycopg.errors.UniqueViolation):
            students.updateStudentEmail(2, "john.doe@example.com")
        with students.connect() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM students").fetchone()[0], 3)
            self.assertEqual(conn.execute(
                "SELECT email FROM students WHERE student_id=2").fetchone()[0],
                "jane.smith@example.com")

    def test_required_fields_and_nullable_date(self):
        for values in [(None, "Doe", "x@example.com", None),
                       ("Jane", None, "x@example.com", None),
                       ("Jane", "Doe", None, None)]:
            with self.assertRaises(psycopg.errors.NotNullViolation):
                students.addStudent(*values)
        with contextlib.redirect_stdout(io.StringIO()):
            sid = students.addStudent("No", "Date", "nodate@example.com", None)
        with students.connect() as conn:
            self.assertIsNone(conn.execute(
                "SELECT enrollment_date FROM students WHERE student_id=%s", (sid,)
            ).fetchone()[0])

    def test_missing_ids_do_not_change_records(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(students.updateStudentEmail(9999, "none@example.com"))
            self.assertFalse(students.deleteStudent(9999))
        with students.connect() as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM students").fetchone()[0], 3)

    def test_sql_text_is_stored_as_data(self):
        name = "O'Connor'); DROP TABLE students; --"
        with contextlib.redirect_stdout(io.StringIO()):
            sid = students.addStudent(name, "Example", "quote@example.com", None)
        with students.connect() as conn:
            self.assertEqual(conn.execute(
                "SELECT first_name FROM students WHERE student_id=%s", (sid,)
            ).fetchone()[0], name)
            self.assertEqual(conn.execute("SELECT count(*) FROM students").fetchone()[0], 4)

    def test_empty_table_displays_without_error(self):
        with students.connect() as conn:
            conn.execute("DELETE FROM students")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(students.getAllStudents(), [])
        self.assertIn("(0 student(s))", output.getvalue())


if __name__ == "__main__":
    unittest.main()
