from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox,
    QDateEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QMessageBox, QLineEdit, QHeaderView, QGroupBox,
    QSpinBox, QInputDialog
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QFont, QColor, QBrush

class VacationsTab(QWidget):
    def __init__(self, db_manager, user_role="manager", department_name=None):
        super().__init__()
        self.db = db_manager
        self.user_role = user_role
        self.department_name = department_name  # اسم القسم لرئيس القسم فقط
        self.setup_ui()
        self.load_employees()
        self.load_vacations()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        # ==== تحسين مظهر المجموعة ====
        input_group = QGroupBox("بيانات الإجازة")
        input_group.setStyleSheet("""
            QGroupBox {
                background-color: #f5faff;
                border: 1.5px solid #2f80ed;
                border-radius: 10px;
                margin-top: 12px;
                font: bold 14px "Cairo", "Tahoma";
            }
            QGroupBox:title {
                subcontrol-origin: margin;
                subcontrol-position: top right;
                padding: 0 6px;
                background: #2f80ed;
                color: white;
                border-radius: 6px;
            }
        """)
        input_form = QFormLayout()
        input_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.employee_combo = QComboBox()
        self.employee_combo.setStyleSheet("QComboBox { font-size: 13px; }")
        input_form.addRow("الموظف:", self.employee_combo)

        self.vacation_type = QComboBox()
        self.vacation_type.addItems([
            "سنوية", "طارئة", "وفاة", "حج", "زواج", "وضع", "مرضية"
        ])
        self.vacation_type.setStyleSheet("QComboBox { font-size: 13px; }")
        self.vacation_type.currentTextChanged.connect(self.handle_vacation_type_change)
        input_form.addRow("نوع الإجازة:", self.vacation_type)

        self.death_type_combo = QComboBox()
        self.death_type_combo.addItems(["وفاة من الدرجة الأولى", "وفاة من الدرجة الثانية"])
        self.death_type_combo.setVisible(False)
        self.death_type_combo.setStyleSheet("QComboBox { font-size: 13px; }")
        self.death_type_combo.currentTextChanged.connect(self.update_death_vacation_duration)
        input_form.addRow("نوع الوفاة:", self.death_type_combo)

        self.birth_type_combo = QComboBox()
        self.birth_type_combo.addItems(["وضع عادي", "وضع توأم"])
        self.birth_type_combo.setVisible(False)
        self.birth_type_combo.setStyleSheet("QComboBox { font-size: 13px; }")
        self.birth_type_combo.currentTextChanged.connect(self.update_birth_vacation_duration)
        input_form.addRow("نوع الوضع:", self.birth_type_combo)

        dates_group = QGroupBox("فترة الإجازة")
        dates_group.setStyleSheet("""
            QGroupBox {
                background: #eaf1fa;
                border: 1px solid #a8c7e9;
                border-radius: 8px;
                font: bold 12px "Cairo", "Tahoma";
            }
            QGroupBox:title {
                background: #eaf1fa;
                color: #2f80ed;
                border-radius: 4px;
                padding: 0 4px;
            }
        """)
        dates_layout = QHBoxLayout()
        self.start_date = QDateEdit(QDate.currentDate())
        self.start_date.setCalendarPopup(True)
        self.start_date.setStyleSheet("background: #fff;")
        self.start_date.dateChanged.connect(self.update_duration)
        dates_layout.addWidget(QLabel("من:"))
        dates_layout.addWidget(self.start_date)
        self.end_date = QDateEdit(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.setStyleSheet("background: #fff;")
        self.end_date.dateChanged.connect(self.update_duration)
        dates_layout.addWidget(QLabel("إلى:"))
        dates_layout.addWidget(self.end_date)
        dates_group.setLayout(dates_layout)
        input_form.addRow(dates_group)

        self.days_count = QSpinBox()
        self.days_count.setRange(1, 365)
        self.days_count.setReadOnly(False)
        self.days_count.setStyleSheet("background: #fafeff; font-weight: bold; font-size: 13px;")
        input_form.addRow("المدة (أيام):", self.days_count)

        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("ملاحظات إضافية...")
        self.notes_input.setStyleSheet("background: #fafeff; font-size: 13px;")
        input_form.addRow("ملاحظات:", self.notes_input)

        self.save_btn = QPushButton("💾 حفظ الإجازة")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2f80ed;
                color: white;
                font-weight: bold;
                border-radius: 8px;
                padding: 7px 16px;
                font-size: 15px;
            }
            QPushButton:hover { background-color: #1366d6; }
        """)
        self.save_btn.clicked.connect(self.save_vacation)
        input_form.addRow(self.save_btn)

        input_group.setLayout(input_form)
        main_layout.addWidget(input_group)

        # ==== جدول الإجازات ====
        self.vacations_table = QTableWidget()
        self.vacations_table.setColumnCount(11)
        self.vacations_table.setHorizontalHeaderLabels([
            "م", "الموظف", "النوع", "من", "إلى",
            "المدة", "حالة المدير", "حالة رئيس القسم", "موافقة", "رفض", "إلغاء"
        ])
        self.vacations_table.setStyleSheet("""
            QTableWidget {
                background: #fff;
                border-radius: 10px;
                font-size: 13px;
            }
            QHeaderView::section {
                background: #2f80ed;
                color: #fff;
                font-weight: bold;
                border: none;
                border-radius: 0;
                padding: 5px 0;
            }
        """)
        self.vacations_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.vacations_table.horizontalHeader().setStretchLastSection(True)
        self.vacations_table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.vacations_table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.vacations_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.vacations_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.vacations_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.vacations_table.setWordWrap(True)
        self.vacations_table.horizontalHeader().setSectionsMovable(True)
        main_layout.addWidget(QLabel("سجل الإجازات:"))
        main_layout.addWidget(self.vacations_table)
        self.setLayout(main_layout)
        self.setFont(QFont("Cairo", 11))
        self.update_duration()

    def handle_vacation_type_change(self, vac_type):
        self.death_type_combo.setVisible(vac_type == "وفاة")
        self.birth_type_combo.setVisible(vac_type == "وضع")
        today = QDate.currentDate()
        self.start_date.setDate(today)
        self.end_date.setDate(today)
        if vac_type == "طارئة":
            self.days_count.setRange(1, 3)
            self.days_count.setValue(1)
            self.days_count.setReadOnly(False)
        elif vac_type == "سنوية":
            self.days_count.setRange(1, 90)
            self.days_count.setValue(1)
            self.days_count.setReadOnly(False)
        elif vac_type == "حج":
            self.days_count.setRange(20, 20)
            self.days_count.setValue(20)
            self.days_count.setReadOnly(True)
        elif vac_type == "زواج":
            self.days_count.setRange(14, 14)
            self.days_count.setValue(14)
            self.days_count.setReadOnly(True)
        elif vac_type == "وضع":
            self.update_birth_vacation_duration()
        elif vac_type == "مرضية":
            self.days_count.setRange(1, 30)
            self.days_count.setValue(1)
            self.days_count.setReadOnly(False)
        elif vac_type == "وفاة":
            self.update_death_vacation_duration()
        else:
            self.days_count.setReadOnly(False)

    def update_death_vacation_duration(self):
        if self.death_type_combo.currentText() == "وفاة من الدرجة الأولى":
            self.days_count.setRange(7, 7)
            self.days_count.setValue(7)
            self.days_count.setReadOnly(True)
        else:
            self.days_count.setRange(3, 3)
            self.days_count.setValue(3)
            self.days_count.setReadOnly(True)

    def update_birth_vacation_duration(self):
        if self.birth_type_combo.currentText() == "وضع توأم":
            self.days_count.setRange(112, 112)
            self.days_count.setValue(112)
            self.days_count.setReadOnly(True)
        else:
            self.days_count.setRange(98, 98)
            self.days_count.setValue(98)
            self.days_count.setReadOnly(True)

    def load_employees(self):
        try:
            if self.user_role == "department_head" and self.department_name:
                # تحميل فقط موظفي القسم
                self.db.execute_query(
                    "SELECT id, name FROM employees WHERE department=? ORDER BY name",
                    (self.department_name,)
                )
            else:
                # تحميل جميع الموظفين
                self.db.execute_query(
                    "SELECT id, name FROM employees ORDER BY name"
                )
            employees = self.db.cursor.fetchall()
            self.employee_combo.clear()
            for emp_id, name in employees:
                self.employee_combo.addItem(name, emp_id)
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ في تحميل الموظفين: {str(e)}")

    def update_duration(self):
        start = self.start_date.date()
        end = self.end_date.date()
        if start > end:
            self.end_date.setDate(start)
            end = start
        days = start.daysTo(end) + 1
        self.days_count.setValue(days)

    def validate_vacation_data(self):
        errors = []
        if not self.employee_combo.currentData():
            errors.append("الرجاء اختيار موظف")
        start_date = self.start_date.date()
        end_date = self.end_date.date()
        if start_date > end_date:
            errors.append("تاريخ النهاية يجب أن يكون بعد تاريخ البداية")
        if self.days_count.value() < 1:
            errors.append("المدة يجب أن تكون يوم واحد على الأقل")
        return errors

    def save_vacation(self):
        try:
            emp_id = self.employee_combo.currentData()
            if not emp_id:
                QMessageBox.warning(self, "تحذير", "الرجاء اختيار موظف")
                return
            vac_type = self.vacation_type.currentText()
            start_date = self.start_date.date().toString("yyyy-MM-dd")
            end_date = self.end_date.date().toString("yyyy-MM-dd")
            duration = self.days_count.value()
            notes = self.notes_input.text() or "لا يوجد ملاحظات"
            relation = None

            if vac_type == "وفاة":
                death_type = self.death_type_combo.currentText()
                if death_type == "وفاة من الدرجة الأولى":
                    relations = ["أب", "أم", "ابن", "ابنة", "جد", "جدة", "زوج"]
                    relation, ok = QInputDialog.getItem(
                        self, "علاقة المتوفى",
                        "اختر صلة القرابة مع المتوفى:",
                        relations, 0, False
                    )
                    if not ok:
                        return
                    if relation == "زوج":
                        duration = 130
                        self.days_count.setValue(130)
                else:
                    relation = "أقارب آخرون"
                self.update_death_vacation_duration()

            birth_type = None
            if vac_type == "وضع":
                birth_type = self.birth_type_combo.currentText()
                if birth_type == "وضع توأم":
                    duration = 112
                else:
                    duration = 98
                self.days_count.setValue(duration)
                notes = (notes + "\n" if notes else "") + f"نوع الوضع: {birth_type}"

            # تحقق من الرصيد للإجازة الطارئة والسنوية
            if vac_type == "طارئة":
                self.db.execute_query("SELECT emergency_vacation_balance FROM employees WHERE id=?", (emp_id,))
                balance = self.db.cursor.fetchone()[0]
                if duration > balance:
                    QMessageBox.warning(self, "رصيد غير كافٍ", "رصيد الإجازة الطارئة غير كافٍ!")
                    return
            if vac_type == "سنوية":
                self.db.execute_query("SELECT vacation_balance FROM employees WHERE id=?", (emp_id,))
                balance = self.db.cursor.fetchone()[0]
                if duration > balance:
                    QMessageBox.warning(self, "رصيد غير كافٍ", "رصيد الإجازة السنوية غير كافٍ!")
                    return

            errors = self.validate_vacation_data()
            if errors:
                QMessageBox.warning(self, "تحذير", "\n".join(errors))
                return

            if self.check_vacation_conflict(emp_id, start_date, end_date):
                QMessageBox.warning(self, "تحذير", "هناك إجازة أخرى للموظف في هذه الفترة")
                return

            query = """
                INSERT INTO vacations (
                    employee_id, type, relation, start_date, end_date,
                    duration, notes, status, dept_approval, dept_approver, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """
            params = (
                emp_id, vac_type, relation, start_date, end_date,
                duration, notes, 'تحت الإجراء', 'تحت الإجراء', None
            )
            self.db.execute_query(query, params, commit=True)
            QMessageBox.information(
                self, "تم بنجاح",
                f"تم تقديم طلب الإجازة بنجاح\n"
                f"النوع: {vac_type}\n"
                f"المدة: {duration} يوم\n"
                f"من {start_date} إلى {end_date}\n"
                f"ملاحظات: {notes}"
            )
            self.load_vacations()
            self.notes_input.clear()
        except Exception as e:
            QMessageBox.critical(
                self, "خطأ في الحفظ",
                f"حدث خطأ أثناء حفظ الإجازة:\n{str(e)}\n"
                "الرجاء التأكد من صحة جميع البيانات والمحاولة مرة أخرى"
            )

    def check_vacation_conflict(self, emp_id, start_date, end_date):
        try:
            self.db.execute_query("""
                SELECT COUNT(*) FROM vacations
                WHERE employee_id = ?
                AND status != 'مرفوض'
                AND (
                    (? BETWEEN start_date AND end_date)
                    OR (? BETWEEN start_date AND end_date)
                    OR (start_date BETWEEN ? AND ?)
                    OR (end_date BETWEEN ? AND ?)
                )
            """, (emp_id, start_date, end_date, start_date, end_date, start_date, end_date),
            commit=False)
            count = self.db.cursor.fetchone()[0]
            return count > 0
        except Exception as e:
            print(f"Error checking vacation conflict: {e}")
            return False

    def refresh_data(self):
        self.load_vacations()

    def load_vacations(self):
        self.vacations_table.setRowCount(0)
        try:
            # تحميل جميع أو فقط إجازات القسم
            if self.user_role == "department_head" and self.department_name:
                self.db.execute_query("""
                    SELECT v.id, e.name, v.type, v.start_date, v.end_date, v.duration,
                           v.status, v.dept_approval
                    FROM vacations v
                    JOIN employees e ON v.employee_id = e.id
                    WHERE e.department=?
                    ORDER BY v.start_date DESC
                """, (self.department_name,))
            else:
                self.db.execute_query("""
                    SELECT v.id, e.name, v.type, v.start_date, v.end_date, v.duration,
                           v.status, v.dept_approval
                    FROM vacations v
                    JOIN employees e ON v.employee_id = e.id
                    ORDER BY v.start_date DESC
                """)
            vacations = self.db.cursor.fetchall()
            self.vacations_table.setRowCount(len(vacations) if vacations else 1)
            if not vacations:
                self.vacations_table.setItem(0, 0, QTableWidgetItem("لا يوجد طلبات"))
                for col in range(1, self.vacations_table.columnCount()):
                    self.vacations_table.setItem(0, col, QTableWidgetItem(""))
                return

            for row_idx, row in enumerate(vacations):
                vac_id, emp_name, vac_type, start, end, days, status, dept_approval = row
                # رقم متسلسل وليس رقم الجدول الفعلي
                serial_item = QTableWidgetItem(str(row_idx + 1))
                serial_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.vacations_table.setItem(row_idx, 0, serial_item)

                # باقي الأعمدة
                items = [
                    QTableWidgetItem(emp_name if emp_name else ''),
                    QTableWidgetItem(vac_type if vac_type else ''),
                    QTableWidgetItem(start if start else ''),
                    QTableWidgetItem(end if end else ''),
                    QTableWidgetItem(str(days) if days else ''),
                    QTableWidgetItem(status if status else ''),
                    QTableWidgetItem(dept_approval if dept_approval else ''),
                ]

                # تمييز الصف حسب الحالة
                for col, item in enumerate(items, start=1):
                    if status == "موافق":
                        # أخضر هافت
                        item.setBackground(QBrush(QColor(200, 255, 200)))
                        item.setForeground(QBrush(QColor(0, 60, 0)))
                    elif status == "مرفوض":
                        item.setBackground(QBrush(QColor(255, 193, 193)))
                        item.setForeground(QBrush(QColor(120, 0, 0)))
                    elif status == "ملغاة":
                        item.setBackground(QBrush(QColor(220, 220, 220)))
                    elif status == "تحت الإجراء":
                        item.setBackground(QBrush(QColor(255, 255, 180)))
                    self.vacations_table.setItem(row_idx, col, item)

                show_action = False
                if self.user_role == "department_head" and dept_approval == "تحت الإجراء":
                    show_action = True
                elif self.user_role == "manager" and status == "تحت الإجراء" and dept_approval == "موافق":
                    show_action = True

                if show_action:
                    approve_btn = QPushButton("موافقة")
                    reject_btn = QPushButton("رفض")
                    cancel_btn = QPushButton("إلغاء")
                    approve_btn.setStyleSheet("background-color:#22c55e; color:white; font-weight:bold; border-radius:7px")
                    reject_btn.setStyleSheet("background-color:#ef4444; color:white; font-weight:bold; border-radius:7px")
                    cancel_btn.setStyleSheet("background-color:#64748b; color:white; font-weight:bold; border-radius:7px")
                    approve_btn.clicked.connect(lambda _, v_id=vac_id: self.approve_vacation(v_id))
                    reject_btn.clicked.connect(lambda _, v_id=vac_id: self.reject_vacation(v_id))
                    cancel_btn.clicked.connect(lambda _, v_id=vac_id: self.cancel_vacation(v_id))
                    self.vacations_table.setCellWidget(row_idx, 8, approve_btn)
                    self.vacations_table.setCellWidget(row_idx, 9, reject_btn)
                    self.vacations_table.setCellWidget(row_idx, 10, cancel_btn)
                else:
                    self.vacations_table.setCellWidget(row_idx, 8, QLabel("-"))
                    self.vacations_table.setCellWidget(row_idx, 9, QLabel("-"))
                    self.vacations_table.setCellWidget(row_idx, 10, QLabel("-"))
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ أثناء تحميل الإجازات:\n{e}")

    def approve_vacation(self, vac_id):
        try:
            if self.user_role == "department_head":
                self.db.execute_query(
                    "UPDATE vacations SET dept_approval='موافق' WHERE id=?",
                    (vac_id,), commit=True
                )
            else:
                self.db.execute_query("SELECT employee_id, type, duration FROM vacations WHERE id=?", (vac_id,), commit=False)
                emp_id, vac_type, duration = self.db.cursor.fetchone()
                if vac_type == "سنوية":
                    self.db.execute_query(
                        "UPDATE employees SET vacation_balance = vacation_balance - ? WHERE id = ?",
                        (duration, emp_id), commit=True
                    )
                if vac_type == "طارئة":
                    self.db.execute_query(
                        "UPDATE employees SET emergency_vacation_balance = emergency_vacation_balance - ? WHERE id = ?",
                        (duration, emp_id), commit=True
                    )
                self.db.execute_query(
                    "UPDATE vacations SET status='موافق' WHERE id=?",
                    (vac_id,), commit=True
                )
            QMessageBox.information(self, "تمت الموافقة", "تمت الموافقة على الإجازة.")
            self.load_vacations()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ أثناء الموافقة: {e}")

    def reject_vacation(self, vac_id):
        try:
            if self.user_role == "department_head":
                self.db.execute_query(
                    "UPDATE vacations SET dept_approval='مرفوض' WHERE id=?",
                    (vac_id,), commit=True
                )
            else:
                self.db.execute_query(
                    "UPDATE vacations SET status='مرفوض' WHERE id=?",
                    (vac_id,), commit=True
                )
            QMessageBox.information(self, "تم الرفض", "تم رفض الإجازة.")
            self.load_vacations()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ أثناء الرفض: {e}")

    def cancel_vacation(self, vac_id):
        try:
            self.db.execute_query(
                "UPDATE vacations SET status='ملغاة', dept_approval='ملغاة' WHERE id=?",
                (vac_id,), commit=True
            )
            self.db.execute_query("SELECT employee_id, type, duration FROM vacations WHERE id=?", (vac_id,), commit=False)
            emp_id, vac_type, duration = self.db.cursor.fetchone()
            if vac_type == "سنوية":
                self.db.execute_query(
                    "UPDATE employees SET vacation_balance = vacation_balance + ? WHERE id = ?",
                    (duration, emp_id), commit=True
                )
            if vac_type == "طارئة":
                self.db.execute_query(
                    "UPDATE employees SET emergency_vacation_balance = emergency_vacation_balance + ? WHERE id = ?",
                    (duration, emp_id), commit=True
                )
            QMessageBox.information(self, "تم الإلغاء", "تم إلغاء الإجازة.")
            self.load_vacations()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ أثناء الإلغاء: {e}")