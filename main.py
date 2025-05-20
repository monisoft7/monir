from multiprocessing import Process
from database import DatabaseManager
from telegram_bot import EmployeeQueryBot
from main_window import MainWindow
from PyQt6.QtWidgets import QApplication
import sys

def run_bot():
    db = DatabaseManager()
    # استخدم التوكن الخاص بك هنا أو من ملف إعدادات
    bot = EmployeeQueryBot("7798615366:AAGhr928M-PZ19usrx6yr2nG0mLBXvP3r0E", db)
    bot.run()

def run_gui():
    app = QApplication(sys.argv)
    db = DatabaseManager()
    window = MainWindow(db)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    # شغل البوت في عملية منفصلة
    bot_process = Process(target=run_bot)
    bot_process.start()
    # شغل الواجهة الرسومية في العملية الرئيسية
    run_gui()
    # عندما تغلق الواجهة، تأكد من إغلاق البوت أيضًا
    bot_process.terminate()
    bot_process.join()