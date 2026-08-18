import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
import sys
import subprocess
import hashlib

# ==========================================
# ส่วนที่ 1: ระบบฐานข้อมูลและการจัดการไฟล์ (Database & File Management)
# ==========================================
def init_db():
    try:
        conn = sqlite3.connect('passexam.db')
        c = conn.cursor()
        
        # สร้างตารางผู้ใช้งาน
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT UNIQUE,
                      password TEXT)''')
        
        # สร้างตารางเนื้อหาสรุป
        c.execute('''CREATE TABLE IF NOT EXISTS summaries
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      subject TEXT,
                      title TEXT,
                      content TEXT,
                      video_path TEXT)''')
        
        # อัปเดตคอลัมน์ใหม่สำหรับตาราง summaries แบบปลอดภัย
        try:
            c.execute("ALTER TABLE summaries ADD COLUMN user_id INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass
            
        try:
            c.execute("ALTER TABLE summaries ADD COLUMN video_path TEXT")
        except sqlite3.OperationalError:
            pass

        # สร้างตารางคะแนน (รูปแบบใหม่)
        c.execute('''CREATE TABLE IF NOT EXISTS scores
                     (user_id INTEGER,
                      subject TEXT,
                      score INTEGER,
                      PRIMARY KEY (user_id, subject))''')
                      
        # === ระบบซ่อมแซมและอัปเกรดตาราง scores อัตโนมัติ ===
        try:
            c.execute("SELECT user_id FROM scores LIMIT 1")
        except sqlite3.OperationalError:
            # ถ้าไม่มีคอลัมน์ user_id แสดงว่าเป็นตารางเวอร์ชันเก่า ให้สร้างใหม่และย้ายข้อมูล
            c.execute("ALTER TABLE scores RENAME TO temp_scores")
            c.execute('''CREATE TABLE scores
                         (user_id INTEGER DEFAULT 1,
                          subject TEXT,
                          score INTEGER,
                          PRIMARY KEY (user_id, subject))''')
            try:
                # ลองดึงข้อมูลเก่ามาใส่ใน user_id 1
                c.execute("INSERT INTO scores (user_id, subject, score) SELECT 1, subject, score FROM temp_scores")
            except:
                pass
            c.execute("DROP TABLE temp_scores")
        # ==============================================

        conn.commit()
    except Exception as e:
        print(f"Database Initialization Error: {e}")
    finally:
        conn.close()

def hash_pwd(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ตัวแปร Global เก็บสถานะผู้ใช้ที่ล็อกอินอยู่
CURRENT_USER_ID = None
CURRENT_USERNAME = None

def save_summary(subject, title, content, video_path=""):
    try:
        conn = sqlite3.connect('passexam.db')
        c = conn.cursor()
        c.execute("INSERT INTO summaries (user_id, subject, title, content, video_path) VALUES (?, ?, ?, ?, ?)", 
                  (CURRENT_USER_ID, subject, title, content, video_path))
        conn.commit()
    except Exception as e:
        messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการบันทึกข้อมูล: {e}")
    finally:
        conn.close()

def update_summary(record_id, subject, title, content, video_path=""):
    try:
        conn = sqlite3.connect('passexam.db')
        c = conn.cursor()
        c.execute("UPDATE summaries SET subject=?, title=?, content=?, video_path=? WHERE id=? AND user_id=?", 
                  (subject, title, content, video_path, record_id, CURRENT_USER_ID))
        conn.commit()
    except Exception as e:
        messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการอัปเดตข้อมูล: {e}")
    finally:
        conn.close()

def delete_summary(record_id):
    try:
        conn = sqlite3.connect('passexam.db')
        c = conn.cursor()
        c.execute("DELETE FROM summaries WHERE id=? AND user_id=?", (record_id, CURRENT_USER_ID))
        conn.commit()
    except Exception as e:
        messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการลบข้อมูล: {e}")
    finally:
        conn.close()

def get_summaries(keyword=""):
    rows = []
    try:
        conn = sqlite3.connect('passexam.db')
        c = conn.cursor()
        if keyword:
            wildcard = f"%{keyword}%"
            c.execute("SELECT id, subject, title, content, video_path FROM summaries WHERE user_id=? AND (subject LIKE ? OR title LIKE ? OR content LIKE ?)", 
                      (CURRENT_USER_ID, wildcard, wildcard, wildcard))
        else:
            c.execute("SELECT id, subject, title, content, video_path FROM summaries WHERE user_id=?", (CURRENT_USER_ID,))
        rows = c.fetchall()
    except Exception as e:
        print(f"Error fetching summaries: {e}")
    finally:
        conn.close()
    return rows

def get_overall_readiness():
    score = 0
    try:
        conn = sqlite3.connect('passexam.db')
        c = conn.cursor()
        c.execute("SELECT AVG(score) FROM scores WHERE user_id=?", (CURRENT_USER_ID,))
        res = c.fetchone()[0]
        if res:
            score = int(res)
    except Exception as e:
        print(f"Error fetching readiness: {e}")
    finally:
        conn.close()
    return score

def open_media(path):
    if not path or not os.path.exists(path):
        messagebox.showerror("ไม่พบไฟล์", "ไม่พบไฟล์สื่อนี้ในเครื่อง (ไฟล์อาจถูกย้ายหรือถูกลบไปแล้ว)")
        return
    try:
        if sys.platform == "win32": 
            os.startfile(path)
        elif sys.platform == "darwin": 
            subprocess.call(["open", path])
        else: 
            subprocess.call(["xdg-open", path])
    except Exception as e:
        messagebox.showerror("ข้อผิดพลาด", f"ไม่สามารถเปิดไฟล์ได้: {e}")


# ==========================================
# ส่วนที่ 2: ระบบควิซ (Quiz System)
# ==========================================
class QuizWindow:
    def __init__(self, parent, subject, items, callback_on_finish):
        self.top = tk.Toplevel(parent)
        self.top.title(f"ทำแบบทดสอบทบทวน: {subject}")
        self.top.geometry("650x600")
        self.top.configure(bg="#F4F6F9")
        self.top.grab_set()

        self.subject = subject
        self.items = items
        self.total = len(items)
        self.current_idx = 0
        self.score = 0
        self.callback_on_finish = callback_on_finish

        self.build_ui()
        self.load_question()

    def build_ui(self):
        top_frame = tk.Frame(self.top, bg="#F4F6F9")
        top_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        self.lbl_prog = tk.Label(top_frame, text="", font=("Helvetica", 12), bg="#F4F6F9", fg="#555")
        self.lbl_prog.pack(side="left")
        
        self.lbl_score_display = tk.Label(top_frame, text=f"คะแนน: 0 / {self.total}", font=("Helvetica", 12, "bold"), bg="#F4F6F9", fg="#2D7A71")
        self.lbl_score_display.pack(side="right")

        self.lbl_q = tk.Label(self.top, text="", font=("Helvetica", 18, "bold"), bg="#F4F6F9", wraplength=550)
        self.lbl_q.pack(pady=10)

        card_frame = tk.Frame(self.top, bg="white", highlightbackground="#CCC", highlightthickness=1)
        card_frame.pack(fill="both", expand=True, padx=40, pady=10)

        self.lbl_ans = tk.Label(card_frame, text="", font=("Helvetica", 14), bg="white", wraplength=500, justify="left")
        self.lbl_ans.pack(pady=30, padx=20, fill="both", expand=True)

        self.btn_frame = tk.Frame(self.top, bg="#F4F6F9")
        self.btn_frame.pack(pady=20)

        self.btn_show = tk.Button(self.btn_frame, text="👀 กดเพื่อดูเฉลย", bg="#3498DB", fg="white", font=("Helvetica", 14, "bold"), padx=30, pady=10, command=self.show_answer)
        
        self.btn_correct = tk.Button(self.btn_frame, text="✅ จำได้", bg="#27AE60", fg="white", font=("Helvetica", 14, "bold"), padx=20, pady=5, command=lambda: self.process_answer(True))
        self.btn_skip = tk.Button(self.btn_frame, text="⏩ ข้าม (ไม่คิดคะแนน)", bg="#95A5A6", fg="white", font=("Helvetica", 14, "bold"), padx=20, pady=5, command=lambda: self.process_answer(False))

    def load_question(self):
        self.lbl_prog.config(text=f"ข้อที่ {self.current_idx + 1} จาก {self.total}")
        self.lbl_q.config(text=f"หัวข้อ: {self.items[self.current_idx][0]}")
        self.lbl_ans.config(text="ลองนึกคำตอบในใจ แล้วกดปุ่มเพื่อดูเฉลย...", fg="gray")
        
        self.btn_correct.pack_forget()
        self.btn_skip.pack_forget()
        self.btn_show.pack()

    def show_answer(self):
        current_ans = self.items[self.current_idx][1]
        self.lbl_ans.config(text=current_ans, fg="#222")
        
        self.btn_show.pack_forget()
        self.btn_correct.pack(side="left", padx=10)
        self.btn_skip.pack(side="left", padx=10)

    def process_answer(self, is_correct):
        if is_correct:
            self.score += 1
            
        self.lbl_score_display.config(text=f"คะแนน: {self.score} / {self.total}")
        self.current_idx += 1
        
        if self.current_idx < self.total:
            self.load_question() 
        else:
            self.finish_quiz()

    def finish_quiz(self):
        percentage = int((self.score / self.total) * 100)
        
        try:
            conn = sqlite3.connect('passexam.db')
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO scores (user_id, subject, score) VALUES (?, ?, ?)", 
                      (CURRENT_USER_ID, self.subject, percentage))
            conn.commit()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"บันทึกคะแนนไม่สำเร็จ: {e}")

        self.top.destroy()
        
        if self.callback_on_finish:
            self.callback_on_finish()
            
        msg = f"🎉 ทำแบบทดสอบเสร็จสิ้น!\n\nคุณจำได้ทั้งหมด {self.score} ข้อ จาก {self.total} ข้อ\nคิดเป็นความพร้อม {percentage}%\n\nระบบอัปเดตคะแนนลงแดชบอร์ดเรียบร้อยแล้ว!"
        messagebox.showinfo("สรุปผลทดสอบ", msg)


# ==========================================
# ส่วนที่ 3: หน้าตาโปรแกรมหลัก (Main Application GUI)
# ==========================================
class PassExamApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PassExam - ระบบทบทวนความรู้และบันทึกข้อมูล")
        self.root.geometry("1200x800")
        self.root.configure(bg="#F4F6F9")
        
        init_db()
        
        self.container = tk.Frame(root, bg="#F4F6F9")
        self.container.pack(fill="both", expand=True)
        
        self.build_login_screen()

    def build_login_screen(self):
        for widget in self.container.winfo_children(): 
            widget.destroy()
        
        login_frame = tk.Frame(self.container, bg="white", width=450, height=550, highlightbackground="#DDDDDD", highlightthickness=1)
        login_frame.place(relx=0.5, rely=0.5, anchor="center")
        login_frame.pack_propagate(False)

        tk.Label(login_frame, text="PassExam", font=("Helvetica", 32, "bold"), fg="#322253", bg="white").pack(pady=(50, 5))
        tk.Label(login_frame, text="แอปพลิเคชันสำหรับเตรียมความพร้อม", font=("Helvetica", 14), fg="gray", bg="white").pack(pady=(0, 40))

        tk.Label(login_frame, text="ชื่อผู้ใช้งาน (Username)", font=("Helvetica", 12), bg="white").pack(anchor="w", padx=50)
        user_entry = tk.Entry(login_frame, font=("Helvetica", 14), bg="#F4F6F9", relief="flat")
        user_entry.pack(fill="x", padx=50, pady=(5, 20), ipady=8)

        tk.Label(login_frame, text="รหัสผ่าน (Password)", font=("Helvetica", 12), bg="white").pack(anchor="w", padx=50)
        pwd_entry = tk.Entry(login_frame, font=("Helvetica", 14), bg="#F4F6F9", relief="flat", show="*")
        pwd_entry.pack(fill="x", padx=50, pady=(5, 30), ipady=8)

        def login_action():
            u = user_entry.get().strip()
            p = pwd_entry.get().strip()
            if not u or not p: 
                return messagebox.showwarning("แจ้งเตือน", "กรุณากรอกข้อมูลให้ครบถ้วน")
                
            try:
                conn = sqlite3.connect('passexam.db')
                c = conn.cursor()
                c.execute("SELECT id, username FROM users WHERE username=? AND password=?", (u, hash_pwd(p)))
                user = c.fetchone()
                conn.close()
                
                if user:
                    global CURRENT_USER_ID, CURRENT_USERNAME
                    CURRENT_USER_ID, CURRENT_USERNAME = user[0], user[1]
                    self.build_main_app()
                else: 
                    messagebox.showerror("ผิดพลาด", "ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง")
            except Exception as e:
                messagebox.showerror("System Error", f"Database error: {e}")

        def register_action():
            u = user_entry.get().strip()
            p = pwd_entry.get().strip()
            if not u or not p: 
                return messagebox.showwarning("แจ้งเตือน", "กรุณากรอกข้อมูลให้ครบเพื่อสมัคร")
                
            try:
                conn = sqlite3.connect('passexam.db')
                c = conn.cursor()
                c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (u, hash_pwd(p)))
                conn.commit()
                conn.close()
                messagebox.showinfo("สำเร็จ", "สมัครสมาชิกเรียบร้อยแล้ว! กรุณากดเข้าสู่ระบบ")
            except sqlite3.IntegrityError: 
                messagebox.showerror("ผิดพลาด", "ชื่อผู้ใช้งานนี้มีคนใช้แล้ว โปรดใช้ชื่ออื่น")
                if 'conn' in locals(): conn.close()
            except Exception as e:
                messagebox.showerror("System Error", f"Error: {e}")

        tk.Button(login_frame, text="เข้าสู่ระบบ", font=("Helvetica", 14, "bold"), bg="#2D7A71", fg="white", relief="flat", command=login_action).pack(fill="x", padx=50, pady=5, ipady=8)
        tk.Button(login_frame, text="สมัครสมาชิกใหม่", font=("Helvetica", 12), bg="#F4F6F9", fg="#322253", relief="flat", command=register_action).pack(fill="x", padx=50, pady=5, ipady=8)

    def build_main_app(self):
        for widget in self.container.winfo_children(): 
            widget.destroy()

        self.pages = {}
        
        sidebar = tk.Frame(self.container, bg="#322253", width=250)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self.main_content = tk.Frame(self.container, bg="#F4F6F9")
        self.main_content.pack(side="right", fill="both", expand=True)

        tk.Label(sidebar, text="PassExam", font=("Helvetica", 28, "bold"), fg="white", bg="#322253").pack(pady=(40, 5))
        tk.Label(sidebar, text=f"👤 ผู้ใช้: {CURRENT_USERNAME}", font=("Helvetica", 12), fg="#FFD700", bg="#322253").pack(pady=(0, 40))

        btn_config = {"bg": "#322253", "fg": "white", "font": ("Helvetica", 14), "relief": "flat", "anchor": "w", "padx": 30, "pady": 12, "cursor": "hand2"}
        
        tk.Button(sidebar, text="📊 แดชบอร์ด (Home)", command=lambda: self.show_page("Home"), **btn_config).pack(fill="x", pady=2)
        tk.Button(sidebar, text="📚 คลังความรู้ (Library)", command=lambda: self.show_page("Library"), **btn_config).pack(fill="x", pady=2)
        tk.Button(sidebar, text="📝 ทำแบบทดสอบ (Quiz)", command=self.open_quiz_setup, **btn_config).pack(fill="x", pady=2)
        
        tk.Button(sidebar, text="🚪 ออกจากระบบ", command=self.logout, bg="#322253", fg="#E53935", font=("Helvetica", 14), relief="flat", anchor="w", padx=30, pady=12, cursor="hand2").pack(side="bottom", fill="x", pady=30)

        self.pages["Home"] = tk.Frame(self.main_content, bg="#F4F6F9")
        self.pages["Library"] = tk.Frame(self.main_content, bg="#F4F6F9")
        
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")
        
        self.main_content.grid_rowconfigure(0, weight=1)
        self.main_content.grid_columnconfigure(0, weight=1)

        self.setup_home_page()
        self.setup_library_page()
        self.show_page("Home")

    def show_page(self, page_name):
        try:
            self.pages[page_name].tkraise()
            if page_name == "Home": 
                self.update_home_stats()
            if page_name == "Library": 
                self.refresh_library()
        except Exception as e:
            print(f"Error navigating to {page_name}: {e}")

    def logout(self):
        global CURRENT_USER_ID, CURRENT_USERNAME
        CURRENT_USER_ID, CURRENT_USERNAME = None, None
        self.build_login_screen()

    def setup_home_page(self):
        page = self.pages["Home"]
        
        header = tk.Frame(page, bg="#2D7A71", height=120)
        header.pack(fill="x")
        tk.Label(header, text="ภาพรวมการเรียนของคุณ", font=("Helvetica", 28, "bold"), fg="white", bg="#2D7A71").pack(anchor="w", padx=40, pady=(30, 0))
        self.welcome_lbl = tk.Label(header, text=f"ยินดีต้อนรับกลับมา, {CURRENT_USERNAME}!", font=("Helvetica", 14), fg="#E8F0FE", bg="#2D7A71")
        self.welcome_lbl.pack(anchor="w", padx=40, pady=(5, 20))

        stats_container = tk.Frame(page, bg="#F4F6F9")
        stats_container.pack(fill="x", padx=40, pady=20)
        stats_container.grid_columnconfigure(0, weight=1)
        stats_container.grid_columnconfigure(1, weight=1)

        chart_card = tk.Frame(stats_container, bg="white", highlightbackground="#DDDDDD", highlightthickness=1)
        chart_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tk.Label(chart_card, text="ความพร้อมโดยรวม", font=("Helvetica", 16, "bold"), bg="white", fg="#333").pack(pady=(20, 5))
        
        self.progress_canvas = tk.Canvas(chart_card, width=220, height=220, bg="white", highlightthickness=0)
        self.progress_canvas.pack(pady=10)

        stat_card = tk.Frame(stats_container, bg="white", highlightbackground="#DDDDDD", highlightthickness=1)
        stat_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        tk.Label(stat_card, text="สถิติข้อมูลคลังความรู้", font=("Helvetica", 16, "bold"), bg="white", fg="#333").pack(pady=(20, 15))
        
        self.stat_sum_lbl = tk.Label(stat_card, text="📚 จำนวนสรุปที่สร้าง: 0 หัวข้อ", font=("Helvetica", 16), bg="white", fg="#444")
        self.stat_sum_lbl.pack(anchor="w", padx=30, pady=10)
        
        self.stat_vid_lbl = tk.Label(stat_card, text="🖼️ จำนวนไฟล์ที่แนบ: 0 ไฟล์", font=("Helvetica", 16), bg="white", fg="#2D7A71")
        self.stat_vid_lbl.pack(anchor="w", padx=30, pady=10)

        self.media_container = tk.Frame(page, bg="white", highlightbackground="#DDDDDD", highlightthickness=1)
        self.media_container.pack(fill="both", expand=True, padx=40, pady=(0, 30))
        
        media_header = tk.Frame(self.media_container, bg="#F8F9FA")
        media_header.pack(fill="x")
        tk.Label(media_header, text="📌 รูปภาพ/วิดีโอ ของคุณ (กดเปิดด่วน)", font=("Helvetica", 14, "bold"), bg="#F8F9FA", fg="#322253").pack(anchor="w", padx=20, pady=10)

        self.media_canvas = tk.Canvas(self.media_container, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.media_container, orient="vertical", command=self.media_canvas.yview)
        
        self.media_list_frame = tk.Frame(self.media_canvas, bg="white")
        
        self.media_list_frame.bind(
            "<Configure>",
            lambda e: self.media_canvas.configure(scrollregion=self.media_canvas.bbox("all"))
        )
        self.media_canvas.create_window((0, 0), window=self.media_list_frame, anchor="nw")
        self.media_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.media_canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)

    def update_home_stats(self):
        try:
            if hasattr(self, 'welcome_lbl'):
                self.welcome_lbl.config(text=f"ยินดีต้อนรับกลับมา, {CURRENT_USERNAME}!")
                
            pct = get_overall_readiness()
            self.progress_canvas.delete("all")
            self.progress_canvas.create_oval(10, 10, 210, 210, outline="#EEEEEE", width=20)
            if pct > 0:
                self.progress_canvas.create_arc(10, 10, 210, 210, start=90, extent=-(pct/100)*359.99, outline="#FFC107", width=20, style="arc")
            self.progress_canvas.create_text(110, 110, text=f"{pct}%", font=("Helvetica", 36, "bold"), fill="#2D7A71")

            summaries = get_summaries()
            total_items = len(summaries)
            total_media = sum(1 for s in summaries if s[4])
            
            self.stat_sum_lbl.config(text=f"📚 จำนวนสรุปที่สร้าง: {total_items} หัวข้อ")
            self.stat_vid_lbl.config(text=f"🖼️ จำนวนไฟล์ที่แนบ: {total_media} ไฟล์")

            for widget in self.media_list_frame.winfo_children(): 
                widget.destroy()
            
            conn = sqlite3.connect('passexam.db')
            c = conn.cursor()
            c.execute("SELECT title, video_path FROM summaries WHERE user_id=? AND video_path != '' AND video_path IS NOT NULL ORDER BY id DESC LIMIT 10", (CURRENT_USER_ID,))
            media_items = c.fetchall()
            conn.close()

            if not media_items:
                tk.Label(self.media_list_frame, text="คุณยังไม่มีรูปภาพหรือวิดีโอที่อัปโหลดไว้...", font=("Helvetica", 12), bg="white", fg="gray").pack(anchor="w", pady=10)
            else:
                for title, path in media_items:
                    btn = tk.Button(self.media_list_frame, text=f"▶ เปิดไฟล์: {title}", 
                                    command=lambda p=path: open_media(p), 
                                    bg="#E8F0FE", fg="#1A73E8", font=("Helvetica", 12, "bold"), 
                                    relief="flat", anchor="w", padx=15, pady=8, cursor="hand2")
                    btn.pack(fill="x", pady=4, ipadx=10)
        
        except Exception as e:
            print(f"Error drawing home page: {e}")

    def setup_library_page(self):
        page = self.pages["Library"]
        
        top_bar = tk.Frame(page, bg="#F4F6F9")
        top_bar.pack(fill="x", padx=40, pady=(30, 10))
        
        tk.Label(top_bar, text="คลังความรู้ทั้งหมด", font=("Helvetica", 24, "bold"), bg="#F4F6F9").pack(side="left")
        
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(top_bar, textvariable=self.search_var, font=("Helvetica", 14), width=35)
        search_entry.pack(side="right", ipady=5)
        tk.Label(top_bar, text="🔍 ค้นหา:", font=("Helvetica", 14), bg="#F4F6F9").pack(side="right", padx=10)
        search_entry.bind('<KeyRelease>', lambda e: self.refresh_library())

        table_frame = tk.Frame(page, bg="#F4F6F9")
        table_frame.pack(fill="both", expand=True, padx=40, pady=10)

        columns = ('id', 'subject', 'title')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='headings')
        self.tree.heading('id', text='ID')
        self.tree.heading('subject', text='วิชา')
        self.tree.heading('title', text='หัวข้อสรุป (ดับเบิ้ลคลิกเพื่อเปิดอ่าน/แก้ไข)')
        
        self.tree.column('id', width=50, anchor='center')
        self.tree.column('subject', width=200)
        self.tree.column('title', width=550)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.tree.bind("<Double-1>", self.open_read_modal)

        btn_frame = tk.Frame(page, bg="#F4F6F9")
        btn_frame.pack(fill="x", padx=40, pady=(10, 30))
        
        tk.Button(btn_frame, text="➕ เพิ่มสรุปใหม่ / แนบไฟล์", command=self.open_editor_modal, bg="#27AE60", fg="white", font=("Helvetica", 14, "bold"), relief="flat", padx=20, pady=10, cursor="hand2").pack(side="right")

    def refresh_library(self):
        try:
            keyword = self.search_var.get()
            for row in self.tree.get_children(): 
                self.tree.delete(row)
                
            for record in get_summaries(keyword):
                display_title = f"📎 {record[2]}" if record[4] else record[2]
                self.tree.insert('', tk.END, values=(record[0], record[1], display_title))
        except Exception as e:
            print(f"Error refreshing library: {e}")

    def open_read_modal(self, event):
        sel = self.tree.focus()
        if not sel: return
        
        try:
            r_id = self.tree.item(sel)['values'][0]
            record = [r for r in get_summaries() if r[0] == r_id][0]
        except:
            return

        modal = tk.Toplevel(self.root)
        modal.title(f"รายละเอียด: {record[2]}")
        modal.geometry("700x600")
        modal.configure(bg="white")
        modal.grab_set()

        tools = tk.Frame(modal, bg="#F8F9FA")
        tools.pack(fill="x")
        
        def do_delete():
            if messagebox.askyesno("ยืนยัน", "ต้องการลบข้อมูลนี้ทิ้งอย่างถาวรใช่หรือไม่?", parent=modal):
                delete_summary(r_id)
                modal.destroy()
                self.refresh_library()
                self.update_home_stats()

        tk.Button(tools, text="🗑️ ลบข้อมูล", command=do_delete, bg="#E53935", fg="white", relief="flat", padx=10).pack(side="right", padx=10, pady=10)
        tk.Button(tools, text="✏️ แก้ไขเนื้อหา", command=lambda: [modal.destroy(), self.open_editor_modal(record)], bg="#FFC107", fg="black", relief="flat", padx=10).pack(side="right", pady=10)

        content_frame = tk.Frame(modal, bg="white")
        content_frame.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(content_frame, text=f"วิชา: {record[1]}", font=("Helvetica", 14, "bold"), fg="#2D7A71", bg="white").pack(anchor="w")
        tk.Label(content_frame, text=record[2], font=("Helvetica", 22, "bold"), bg="white", fg="#333", wraplength=600).pack(anchor="w", pady=(5, 15))
        
        if record[4]:
            tk.Button(content_frame, text="▶ เปิดไฟล์รูปภาพ / วิดีโอแนบ", command=lambda: open_media(record[4]), bg="#3498DB", fg="white", font=("Helvetica", 12, "bold"), relief="flat", padx=15, pady=5).pack(anchor="w", pady=(0, 15))

        text_area = tk.Text(content_frame, font=("Helvetica", 14), wrap="word", bg="#F4F6F9", relief="flat", padx=15, pady=15)
        text_area.pack(fill="both", expand=True)
        text_area.insert(tk.END, record[3])
        text_area.config(state="disabled")

    def open_editor_modal(self, edit_record=None):
        is_edit = edit_record is not None
        modal = tk.Toplevel(self.root)
        modal.title("แก้ไขข้อมูล" if is_edit else "สร้างสรุปความรู้ใหม่")
        modal.geometry("600x650")
        modal.configure(bg="white")
        modal.grab_set()

        container = tk.Frame(modal, bg="white")
        container.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(container, text="หมวดหมู่วิชา:", font=("Helvetica", 12, "bold"), bg="white").pack(anchor="w", pady=(0, 5))
        e_subj = tk.Entry(container, font=("Helvetica", 14), bg="#F4F6F9", relief="flat")
        e_subj.pack(fill="x", ipady=5, pady=(0, 15))

        tk.Label(container, text="ชื่อหัวข้อสรุป:", font=("Helvetica", 12, "bold"), bg="white").pack(anchor="w", pady=(0, 5))
        e_title = tk.Entry(container, font=("Helvetica", 14), bg="#F4F6F9", relief="flat")
        e_title.pack(fill="x", ipady=5, pady=(0, 15))

        tk.Label(container, text="เนื้อหาสรุปย่อ:", font=("Helvetica", 12, "bold"), bg="white").pack(anchor="w", pady=(0, 5))
        t_content = tk.Text(container, font=("Helvetica", 14), bg="#F4F6F9", relief="flat", height=8)
        t_content.pack(fill="both", expand=True, pady=(0, 15))

        v_path = tk.StringVar()
        if is_edit:
            e_subj.insert(0, edit_record[1])
            e_title.insert(0, edit_record[2])
            t_content.insert(tk.END, edit_record[3])
            if edit_record[4]: 
                v_path.set(edit_record[4])

        file_frame = tk.Frame(container, bg="#F8F9FA", highlightthickness=1, highlightbackground="#DDD")
        file_frame.pack(fill="x", pady=(5, 20))
        
        lbl_file = tk.Label(file_frame, text=f"ไฟล์ปัจจุบัน: {os.path.basename(edit_record[4]) if is_edit and edit_record[4] else 'ยังไม่ได้แนบไฟล์'}", bg="#F8F9FA", font=("Helvetica", 11), fg="#555")
        lbl_file.pack(side="left", padx=15, pady=10)
        
        def pick_file():
            p = filedialog.askopenfilename(parent=modal, title="เลือกไฟล์แนบ (รูปภาพ / วิดีโอ)", filetypes=[("All Files", "*.*")])
            if p: 
                v_path.set(p)
                lbl_file.config(text=f"ไฟล์ปัจจุบัน: {os.path.basename(p)}")
        
        tk.Button(file_frame, text="📁 เลือกไฟล์", command=pick_file, bg="#3498DB", fg="white", font=("Helvetica", 11, "bold"), relief="flat", padx=10).pack(side="right", padx=10, pady=5)

        def save_action():
            s = e_subj.get().strip()
            t = e_title.get().strip()
            c = t_content.get("1.0", tk.END).strip()
            v = v_path.get()
            
            if not s or not t: 
                return messagebox.showwarning("เตือน", "กรุณากรอก วิชา และ หัวข้อ ให้ครบถ้วน", parent=modal)
                
            if is_edit: 
                update_summary(edit_record[0], s, t, c, v)
            else: 
                save_summary(s, t, c, v)
                
            modal.destroy()
            self.refresh_library()
            self.update_home_stats()

        tk.Button(modal, text="💾 บันทึกข้อมูล", command=save_action, bg="#2D7A71", fg="white", font=("Helvetica", 16, "bold"), relief="flat", pady=10).pack(fill="x", side="bottom")

    def open_quiz_setup(self):
        summaries = get_summaries()
        if not summaries:
            return messagebox.showinfo("แจ้งเตือน", "คุณยังไม่ได้เพิ่มเนื้อหาในคลังความรู้เลย โปรดเพิ่มเนื้อหาก่อนทำแบบทดสอบครับ")
            
        subjects = list(set([s[1] for s in summaries if s[1]]))
        
        modal = tk.Toplevel(self.root)
        modal.title("เริ่มทำแบบทดสอบ")
        modal.geometry("400x250")
        modal.configure(bg="white")
        modal.grab_set()
        
        tk.Label(modal, text="📚 เลือกวิชาที่ต้องการทดสอบ", font=("Helvetica", 16, "bold"), bg="white", fg="#322253").pack(pady=(30, 15))
        
        cb = ttk.Combobox(modal, values=subjects, state="readonly", font=("Helvetica", 14), width=25)
        cb.pack(pady=10)
        if subjects: cb.current(0)
        
        def start_quiz():
            subj = cb.get()
            if not subj: return
            modal.destroy()
            
            conn = sqlite3.connect('passexam.db')
            c = conn.cursor()
            c.execute("SELECT title, content FROM summaries WHERE user_id=? AND subject=?", (CURRENT_USER_ID, subj))
            items = c.fetchall()
            conn.close()

            if not items:
                messagebox.showwarning("แจ้งเตือน", "เกิดข้อผิดพลาด ไม่พบเนื้อหาในวิชานี้")
                return

            def on_finish():
                self.show_page("Home") 

            QuizWindow(self.root, subj, items, callback_on_finish=on_finish)
            
        tk.Button(modal, text="🚀 เริ่มลุยกันเลย!", command=start_quiz, bg="#2D7A71", fg="white", font=("Helvetica", 14, "bold"), relief="flat", padx=20, pady=10).pack(pady=20)


if __name__ == "__main__":
    root = tk.Tk()
    app = PassExamApp(root)
    root.mainloop()