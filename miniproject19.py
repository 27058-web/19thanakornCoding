import sqlite3

class StudySharePlatform:
    def __init__(self, db_name="studyshare.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # 1. ตารางเก็บข้อมูลผู้ใช้งาน (แบ่ง Role เป็น นักเรียน, ครู, รุ่นพี่มหาลัย)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL 
            )
        ''')
        
        # 2. ตารางเก็บโพสต์สรุปความรู้และเทคนิคการจำ
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author_id INTEGER,
                subject TEXT NOT NULL,
                grade_level TEXT NOT NULL,
                content TEXT NOT NULL,
                memory_trick TEXT,
                FOREIGN KEY (author_id) REFERENCES users(id)
            )
        ''')
        self.conn.commit()

    def register_user(self, username, role):
        cursor = self.conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, role) VALUES (?, ?)', (username, role))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"ชื่อผู้ใช้ '{username}' มีในระบบแล้ว")
            return None

    def post_summary(self, author_id, subject, grade_level, content, memory_trick="ไม่มี"):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO summaries (author_id, subject, grade_level, content, memory_trick)
            VALUES (?, ?, ?, ?, ?)
        ''', (author_id, subject, grade_level, content, memory_trick))
        self.conn.commit()
        print(f"✅ บันทึกสรุปวิชา {subject} (ชั้น {grade_level}) สำเร็จ!")

    def search_summaries(self, subject=None, grade_level=None):
        cursor = self.conn.cursor()
        
        # ดึงข้อมูลโพสต์พร้อมชื่อและสถานะของผู้เขียน
        query = '''
            SELECT users.username, users.role, summaries.subject, summaries.grade_level, summaries.content, summaries.memory_trick
            FROM summaries
            JOIN users ON summaries.author_id = users.id
            WHERE 1=1
        '''
        params = []
        
        if subject:
            query += ' AND summaries.subject = ?'
            params.append(subject)
        if grade_level:
            query += ' AND summaries.grade_level = ?'
            params.append(grade_level)
            
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        print(f"\n--- ผลการค้นหา ({len(results)} รายการ) ---")
        for row in results:
            print(f"ผู้เขียน: {row[0]} ({row[1]})")
            print(f"วิชา: {row[2]} | ระดับชั้น: {row[3]}")
            print(f"เนื้อหาสรุป: {row[4]}")
            print(f"💡 เทคนิคการจำ: {row[5]}")
            print("-" * 30)

# ==========================================
# ตัวอย่างการจำลองใช้งานระบบจริง
# ==========================================
if __name__ == "__main__":
    app = StudySharePlatform()

    # 1. จำลองการสมัครสมาชิกของผู้ใช้แต่ละกลุ่ม
    p_jan_id = app.register_user("พี่แจน_วิศวะ", "รุ่นพี่มหาลัย")
    kru_som_id = app.register_user("ครูสมศรี", "ครู")
    nong_joy_id = app.register_user("น้องจอย", "นักเรียน")

    # 2. จำลองการแชร์ความรู้และเทคนิค
    if p_jan_id:
        app.post_summary(
            author_id=p_jan_id,
            subject="ฟิสิกส์",
            grade_level="ม.4",
            content="การเคลื่อนที่แนวตรง v = u + at ใช้เมื่อไม่รู้ระยะทาง (s)",
            memory_trick="ท่องว่า 'วีเท่ากับยูบวกเอที ไม่มีเอส'"
        )

    if kru_som_id:
        app.post_summary(
            author_id=kru_som_id,
            subject="ชีววิทยา",
            grade_level="ม.5",
            content="การสังเคราะห์ด้วยแสงเกิดขึ้นที่คลอโรพลาสต์...",
            memory_trick="จำโครงสร้างคลอโรพลาสต์เป็นรูปเหรียญ (ไทลาคอยด์) เรียงซ้อนกัน (กรานุม)"
        )

    # 3. น้องจอย (นักเรียน) ค้นหาสรุปวิชาฟิสิกส์
    app.search_summaries(subject="ฟิสิกส์")