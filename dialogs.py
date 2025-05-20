from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QLineEdit,
    QPushButton, QFormLayout, QLabel, QMessageBox, QRadioButton,
    QDialogButtonBox, QDateEdit, QGroupBox
)
from PyQt6.QtCore import QDate

class DepartmentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
        self.load_departments()
        self.load_employees()

    def setup_ui(self):
        """تهيئة واجهة إدارة الأقسام"""
        self.setWindowTitle("إدارة الأقسام")
        self.setFixedSize(500, 350)

        layout = QVBoxLayout()

        # قسم إضافة قسم جديد
        add_group = QGroupBox("إضافة قسم جديد")
        add_layout = QFormLayout()

        self.new_department_input = QLineEdit()
        self.new_department_input.setPlaceholderText("أدخل اسم القسم")
        add_layout.addRow("اسم القسم:", self.new_department_input)

        self.head_combo = QComboBox()
        add_layout.addRow("رئيس القسم:", self.head_combo)

        self.head_password_input = QLineEdit()
        self.head_password_input.setPlaceholderText("كلمة سر رئيس القسم")
        self.head_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        add_layout.addRow("كلمة السر لرئيس القسم:", self.head_password_input)

        self.add_btn = QPushButton("إضافة")
        self.add_btn.clicked.connect(self.add_department)
        add_layout.addRow(self.add_btn)

        add_group.setLayout(add_layout)

        # قسم حذف/تعديل الأقسام
        delete_group = QGroupBox("حذف/تعديل قسم")
        delete_layout = QFormLayout()

        self.department_combo = QComboBox()
        self.department_combo.currentIndexChanged.connect(self.populate_edit_fields)
        delete_layout.addRow("اختر قسم:", self.department_combo)

        self.edit_head_combo = QComboBox()
        delete_layout.addRow("رئيس القسم:", self.edit_head_combo)

        self.edit_head_password_input = QLineEdit()
        self.edit_head_password_input.setPlaceholderText("تغيير كلمة سر رئيس القسم")
        self.edit_head_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        delete_layout.addRow("كلمة السر الجديدة:", self.edit_head_password_input)

        # زر تعديل
        self.update_btn = QPushButton("تعديل بيانات القسم")
        self.update_btn.clicked.connect(self.update_department)
        delete_layout.addRow(self.update_btn)

        # زر حذف
        self.delete_btn = QPushButton("حذف")
        self.delete_btn.clicked.connect(self.delete_department)
        delete_layout.addRow(self.delete_btn)

        delete_group.setLayout(delete_layout)

        # أزرار الإغلاق
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        layout.addWidget(add_group)
        layout.addWidget(delete_group)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def load_departments(self):
        """تحميل قائمة الأقسام"""
        try:
            self.parent.db.execute_query(
                "SELECT name FROM departments ORDER BY name"
            )
            departments = [dept[0] for dept in self.parent.db.cursor.fetchall()]
            self.department_combo.clear()
            self.department_combo.addItems(departments)
        except Exception as e:
            QMessageBox.critical(
                self,
                "خطأ",
                f"خطأ في تحميل الأقسام: {str(e)}"
            )

    def load_employees(self):
        """تحميل قائمة الموظفين لرؤساء الأقسام"""
        try:
            self.parent.db.execute_query(
                "SELECT id, name FROM employees ORDER BY name"
            )
            employees = self.parent.db.cursor.fetchall()
            self.head_combo.clear()
            self.edit_head_combo.clear()
            for emp_id, name in employees:
                self.head_combo.addItem(name, emp_id)
                self.edit_head_combo.addItem(name, emp_id)
        except Exception as e:
            QMessageBox.critical(
                self,
                "خطأ",
                f"خطأ في تحميل الموظفين: {str(e)}"
            )

    def populate_edit_fields(self):
        """عند تغيير القسم المختار، عيّن رئيس القسم وكلمة السر في حقول التعديل"""
        selected = self.department_combo.currentText()
        if not selected:
            return
        try:
            self.parent.db.execute_query(
                "SELECT head_id, head_password FROM departments WHERE name=?",
                (selected,),
                commit=False
            )
            row = self.parent.db.cursor.fetchone()
            if row:
                head_id, head_password = row
                idx = self.edit_head_combo.findData(head_id)
                if idx >= 0:
                    self.edit_head_combo.setCurrentIndex(idx)
                self.edit_head_password_input.setText(head_password if head_password else "")
            else:
                self.edit_head_combo.setCurrentIndex(0)
                self.edit_head_password_input.clear()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ في تحميل بيانات القسم: {str(e)}")

    def add_department(self):
        new_dept = self.new_department_input.text().strip()
        head_id = self.head_combo.currentData()
        head_password = self.head_password_input.text().strip()
        if not new_dept:
            QMessageBox.warning(self, "تحذير", "الرجاء إدخال اسم القسم")
            return
        if not head_id:
            QMessageBox.warning(self, "تحذير", "الرجاء اختيار رئيس قسم")
            return
        if not head_password:
            QMessageBox.warning(self, "تحذير", "الرجاء إدخال كلمة سر رئيس القسم")
            return

        try:
            self.parent.db.execute_query(
                "INSERT OR IGNORE INTO departments (name, head_id, head_password) VALUES (?, ?, ?)",
                (new_dept, head_id, head_password)
            )
            QMessageBox.information(self, "تم", "تمت إضافة القسم بنجاح")
            self.new_department_input.clear()
            self.head_password_input.clear()
            self.load_departments()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ: {str(e)}")

    def update_department(self):
        selected = self.department_combo.currentText()
        if not selected:
            QMessageBox.warning(self, "تحذير", "يرجى اختيار قسم لتعديله")
            return
        head_id = self.edit_head_combo.currentData()
        head_password = self.edit_head_password_input.text().strip()
        if not head_id:
            QMessageBox.warning(self, "تحذير", "يرجى اختيار رئيس قسم")
            return
        if not head_password:
            QMessageBox.warning(self, "تحذير", "يرجى إدخال كلمة سر رئيس القسم")
            return
        try:
            self.parent.db.execute_query(
                "UPDATE departments SET head_id=?, head_password=? WHERE name=?",
                (head_id, head_password, selected)
            )
            QMessageBox.information(self, "تم", "تم تعديل بيانات القسم بنجاح")
            self.load_departments()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء التعديل: {str(e)}")

    def delete_department(self):
        """حذف قسم"""
        selected = self.department_combo.currentText()
        if not selected:
            return
        try:
            # التحقق من عدم وجود موظفين في القسم
            self.parent.db.execute_query(
                "SELECT COUNT(*) FROM employees WHERE department = ?",
                (selected,),
                commit=False
            )
            employee_count = self.parent.db.cursor.fetchone()[0]
            if employee_count > 0:
                QMessageBox.warning(
                    self,
                    "تحذير",
                    f"لا يمكن حذف القسم لأنه يحتوي على {employee_count} موظف"
                )
                return

            confirm = QMessageBox.question(
                self,
                "تأكيد الحذف",
                f"هل أنت متأكد من حذف قسم '{selected}'؟",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.Yes:
                self.parent.db.execute_query(
                    "DELETE FROM departments WHERE name = ?",
                    (selected,)
                )
                QMessageBox.information(
                    self,
                    "تم",
                    "تم حذف القسم بنجاح"
                )
                self.load_departments()

        except Exception as e:
            QMessageBox.critical(
                self,
                "خطأ",
                f"حدث خطأ أثناء الحذف: {str(e)}"
            )

class SearchDialog(QDialog):
    """نافذة البحث المتقدم"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """تهيئة واجهة البحث"""
        self.setWindowTitle("البحث المتقدم")
        self.setFixedSize(400, 200)

        layout = QVBoxLayout()

        # خيارات البحث
        options_group = QGroupBox("خيارات البحث")
        options_layout = QVBoxLayout()

        self.id_radio = QRadioButton("بحث بالرقم الوطني")
        self.name_radio = QRadioButton("بحث بالاسم")
        self.date_radio = QRadioButton("بحث بالتاريخ")

        self.id_radio.setChecked(True)

        options_layout.addWidget(self.id_radio)
        options_layout.addWidget(self.name_radio)
        options_layout.addWidget(self.date_radio)
        options_group.setLayout(options_layout)

        # حقول البحث
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("أدخل كلمة البحث...")

        self.date_from = QDateEdit(QDate.currentDate())
        self.date_from.setCalendarPopup(True)
        self.date_from.setVisible(False)

        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setVisible(False)

        # ربط تغيير خيارات البحث
        self.id_radio.toggled.connect(lambda: self.update_search_fields('id'))
        self.name_radio.toggled.connect(lambda: self.update_search_fields('name'))
        self.date_radio.toggled.connect(lambda: self.update_search_fields('date'))

        # أزرار التنفيذ
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(options_group)
        layout.addWidget(QLabel("كلمة البحث:"))
        layout.addWidget(self.search_input)
        layout.addWidget(QLabel("من تاريخ:"))
        layout.addWidget(self.date_from)
        layout.addWidget(QLabel("إلى تاريخ:"))
        layout.addWidget(self.date_to)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def update_search_fields(self, search_type):
        """تحديث حقول البحث حسب النوع المحدد"""
        if search_type == 'date':
            self.search_input.setVisible(False)
            self.date_from.setVisible(True)
            self.date_to.setVisible(True)
        else:
            self.search_input.setVisible(True)
            self.date_from.setVisible(False)
            self.date_to.setVisible(False)
            self.search_input.setFocus()

    def get_search_params(self):
        """الحصول على معايير البحث"""
        if self.id_radio.isChecked():
            return {
                'type': 'national_id',
                'value': self.search_input.text().strip()
            }
        elif self.name_radio.isChecked():
            return {
                'type': 'name',
                'value': self.search_input.text().strip()
            }
        else:
            return {
                'type': 'date',
                'from': self.date_from.date().toString("yyyy-MM-dd"),
                'to': self.date_to.date().toString("yyyy-MM-dd")
            }