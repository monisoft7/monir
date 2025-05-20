from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QStatusBar, QMessageBox, QInputDialog,
    QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor, QFont
from tabs.vacations import VacationsTab
from database import DatabaseManager

class DepartmentHeadApp(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.user_role = "department_head"

        # ----------- الألوان والتنسيقات العامة -----------
        self.setWindowTitle("💼 واجهة رئيس القسم")
        self.setGeometry(150, 150, 950, 720)
        self.setFont(QFont("Cairo", 12))

        # إعداد الألوان للواجهة
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8fafc;
            }
            QStatusBar {
                background: #2f80ed;
                color: white;
                font-weight: bold;
            }
            QPushButton {
                background-color: #2f80ed;
                color: white;
                font-weight: bold;
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #1366d6;
            }
            QWidget#mainBox {
                background-color: #ffffff;
                border-radius: 14px;
                border: 1px solid #e0e7ef;
                margin-top: 18px;
                margin-bottom: 18px;
                margin-left: 18px;
                margin-right: 18px;
            }
            QLabel#welcomeLabel {
                color: #2f80ed;
                font-size: 20px;
                font-weight: bold;
                padding: 8px 0;
            }
        """)

        # شريط الحالة
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # المصادقة والحصول على اسم القسم
        self.department_name = self.authenticate_department_head_and_get_department()
        self.setWindowTitle(f"💼 واجهة رئيس القسم - قسم {self.department_name}")

        # زر تحديث البيانات
        self.refresh_btn = QPushButton("🔄 تحديث البيانات")
        self.refresh_btn.setFixedWidth(160)
        self.refresh_btn.clicked.connect(self.refresh_data)

        # تبويب إدارة الإجازات
        self.vacations_tab = VacationsTab(
            self.db,
            user_role="department_head",
            department_name=self.department_name
        )

        # شريط ترحيبي علوي
        title_label = QPushButton(f"👤 رئيس قسم: {self.department_name}")
        title_label.setEnabled(False)
        title_label.setStyleSheet("""
            QPushButton {
                background: #f1f6fb;
                color: #2f80ed;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)
        title_label.setFixedWidth(260)

        top_layout = QHBoxLayout()
        top_layout.addWidget(title_label)
        top_layout.addStretch()
        top_layout.addWidget(self.refresh_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)

        # حاوية رئيسية ذات مظهر احترافي
        main_box = QWidget(objectName="mainBox")
        box_layout = QVBoxLayout()
        box_layout.addWidget(self.vacations_tab)
        main_box.setLayout(box_layout)
        main_layout.addWidget(main_box)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def refresh_data(self):
        """تحديث بيانات الإجازات"""
        self.vacations_tab.refresh_data()
        self.status_bar.showMessage("تم تحديث البيانات.", 3000)

    def authenticate_department_head_and_get_department(self):
        """
        يطلب كلمة مرور رئيس القسم ويرجع اسم القسم عند التحقق
        """
        import sys

        max_attempts = 3
        attempts = 0
        while attempts < max_attempts:
            password, ok_pressed = QInputDialog.getText(
                self,
                "التحقق من كلمة المرور",
                "أدخل كلمة مرور رئيس القسم:"
            )
            if not ok_pressed:
                sys.exit(0)  # خروج إذا تم الإلغاء

            # تحقق من كلمة المرور في جدول الأقسام وأرجع اسم القسم
            self.db.execute_query(
                "SELECT name FROM departments WHERE head_password=?",
                (password,),
                commit=False
            )
            row = self.db.cursor.fetchone()
            if row:
                dept_name = row[0]
                self.status_bar.showMessage(f"مرحباً رئيس قسم {dept_name}", 5000)
                return dept_name
            else:
                attempts += 1
                QMessageBox.warning(self, "كلمة مرور خاطئة", "كلمة المرور غير صحيحة، حاول مرة أخرى.")

        QMessageBox.critical(self, "خطأ", "تم تجاوز عدد المحاولات المسموح به.")
        sys.exit(1)

    def closeEvent(self, event):
        self.db.create_backup()
        super().closeEvent(event)

if __name__ == "__main__":
    import sys
    db = DatabaseManager()
    app = QApplication(sys.argv)
    window = DepartmentHeadApp(db)
    window.show()
    sys.exit(app.exec())