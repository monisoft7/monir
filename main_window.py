from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar, QLabel, QVBoxLayout,
    QWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from tabs.employee_view import EmployeeViewTab
from tabs.employee_management import EmployeeManagementTab
from tabs.vacations import VacationsTab
from tabs.absences import AbsencesTab
from tabs.import_export import ImportExportTab
from tabs.approval_tab import ApprovalTab

class MainWindow(QMainWindow):
    def __init__(self, db_manager, user_role="manager"):
        super().__init__()
        self.db = db_manager
        self.user_role = user_role  # يمكنك ضبط هذا عند تسجيل الدخول حسب نوع المستخدم
        self.setup_ui()
        self.setup_notifications()
        self.load_initial_data()
        self.setup_connections()

    def setup_ui(self):
        """تهيئة الواجهة الرئيسية"""
        self.setWindowTitle("نظام إدارة الموظفين - المجمع الصحي ميزران")
        self.setGeometry(100, 100, 1200, 800)
        
        # إنشاء التبويبات الرئيسية
        self.tabs = QTabWidget()
        self.create_tabs()
        
        # إنشاء شريط الحالة
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # تعيين التبويبات كعنصر مركزي مع شريط الإشعارات
        self.notification_bar = QLabel()
        self.notification_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notification_bar.setStyleSheet("""
            background-color: #FFD700;
            padding: 8px;
            font-weight: bold;
            border-bottom: 2px solid #C0C0C0;
        """)
        self.notification_bar.hide()
    
        layout = QVBoxLayout()
        layout.addWidget(self.notification_bar)
        layout.addWidget(self.tabs)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def create_tabs(self):
        """إنشاء وتكوين التبويبات"""
        # تبويب عرض الموظفين
        self.employee_view_tab = EmployeeViewTab(self.db)
        self.tabs.addTab(self.employee_view_tab, "عرض الموظفين")
        
        # تبويب إدارة الموظفين
        self.employee_management_tab = EmployeeManagementTab(self.db, self)
        self.tabs.addTab(self.employee_management_tab, "إدارة الموظفين")
        
        # تبويب الإجازات
        self.vacations_tab = VacationsTab(self.db)
        self.tabs.addTab(self.vacations_tab, "إدارة الإجازات")
        
        # تبويب الغياب
        self.absences_tab = AbsencesTab(self.db)
        self.tabs.addTab(self.absences_tab, "تسجيل الغياب")
        
        # تبويب الاستيراد/التصدير
        self.import_export_tab = ImportExportTab(self.db)
        self.tabs.addTab(self.import_export_tab, "استيراد/تصدير")

        # تبويب الموافقات - يظهر حسب نوع المستخدم
        if self.user_role == "manager":
            self.approval_tab = ApprovalTab(self.db, user_role="manager")
            self.tabs.addTab(self.approval_tab, "موافقات المدير")
        elif self.user_role == "department_head":
            self.approval_tab = ApprovalTab(self.db, user_role="department_head")
            self.tabs.addTab(self.approval_tab, "موافقات رئيس القسم")

    def setup_notifications(self):
        """تهيئة نظام الإشعارات"""
        # تم نقل هذا الكود إلى setup_ui ليسهل الجمع في الـ QVBoxLayout
        self.tabs.currentChanged.connect(self.update_notifications)

    def update_notifications(self):
        """تحديث الإشعارات"""
        try:
            # تم تعديل الاستعلام ليظهر فقط الطلبات التي وافق عليها رئيس القسم
            self.db.execute_query("""
                SELECT COUNT(*) FROM vacations WHERE status='تحت الإجراء' AND dept_approval='موافق'
            """, commit=False)
            count = self.db.cursor.fetchone()[0]
        
            if count > 0:
                self.notification_bar.setText(f"لديك {count} طلبات إجازة بانتظار موافقة المدير")
                self.notification_bar.show()
            else:
                self.notification_bar.hide()
        except Exception as e:
            print(f"Error updating notifications: {e}")

    def setup_connections(self):
        """ربط الإشارات والأحداث"""
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def load_initial_data(self):
        """تحميل البيانات الأولية"""
        try:
            self.employee_view_tab.load_employees()
            self.employee_management_tab.load_departments()
            self.check_pending_requests()
            if hasattr(self, "approval_tab"):
                self.approval_tab.load_pending_vacations()
        except Exception as e:
            self.show_error_message(f"خطأ في تحميل البيانات الأولية: {str(e)}")

    def on_tab_changed(self, index):
        """معالجة تغيير التبويب"""
        current_tab = self.tabs.widget(index)
        if hasattr(current_tab, 'refresh_data'):
            current_tab.refresh_data()
        self.update_notifications()

    def check_pending_requests(self):
        """التحقق من طلبات الإجازة المعلقة عند بدء التشغيل"""
        try:
            # يشمل فقط ما بعد موافقة رئيس القسم
            self.db.execute_query(
                "SELECT COUNT(*) FROM vacations WHERE status='تحت الإجراء' AND dept_approval='موافق'",
                commit=False
            )
            count = self.db.cursor.fetchone()[0]
            if count > 0:
                self.show_notification(f"لديك {count} طلبات إجازة بانتظار موافقة المدير")
        except Exception as e:
            self.show_error_message(f"خطأ في التحقق من الطلبات: {str(e)}")

    def show_notification(self, message: str):
        """عرض إشعار للمستخدم"""
        self.notification_bar.setText(message)
        self.notification_bar.show()

    def hide_notification(self):
        """إخفاء شريط الإشعارات"""
        self.notification_bar.hide()

    def show_error_message(self, message: str):
        """عرض رسالة خطأ"""
        QMessageBox.critical(
            self,
            "خطأ",
            message,
            QMessageBox.StandardButton.Ok
        )

    def closeEvent(self, event):
        """معالجة حدث إغلاق النافذة"""
        self.db.create_backup()
        super().closeEvent(event)