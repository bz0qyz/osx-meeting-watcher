import sqlite3
from datetime import datetime, timedelta

class LogEntry:
    def __init__(self, row_id=None, db_path="example.db", auto_start=False):
        self.db_path = db_path
        self.id = row_id
        self.start_time = None
        self.end_time = None
        self.duration = None

        if row_id and isinstance(row_id, int):
            self._load_from_db(row_id)
        elif row_id and isinstance(row_id, tuple):
            self.id = row_id[0]
            self.start_time = row_id[1]
            self.end_time = row_id[2]
            self.duration = row_id[3]
        if auto_start:
            self.start()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _load_from_db(self, row_id):
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id, start_time, end_time, duration FROM log WHERE id = ?", (row_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            self.id = row[0]
            self.start_time = datetime.fromisoformat(row[1]) if row[1] else None
            self.end_time = datetime.fromisoformat(row[2]) if row[2] else None
            self.duration = row[3]

    def start(self):
        self.start_time = datetime.now()

    def end(self):
        if not self.start_time:
            raise ValueError("start() must be called before end()")

        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO log (start_time, end_time, duration)
            VALUES (?, ?, ?)
        """, (
            self.start_time.isoformat(),
            self.end_time.isoformat(),
            self.duration
        ))
        conn.commit()
        self.id = cursor.lastrowid
        conn.close()

    @property
    def meeting_duration(self):
        if self.duration is None:
            return None
        return str(timedelta(seconds=int(self.duration)))

    @property
    def meeting_date(self):
        if self.end_time is None:
            return None
        meeting_date = datetime.fromisoformat(self.end_time)
        return meeting_date.strftime('%b. %d, %Y')
