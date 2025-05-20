from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton,
    QLabel, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt

class ApprovalTab(QWidget):
    def __init__(self, db_manager, user_role="manager"):
        super().__init__()
        self.db = db_manager
        self.user_role = user_role  # "manager" أو "department_head"
        self.setup_ui()
        self.load_pending_vacations()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "ID", "الموظف", "النوع", "من", "إلى", "المدة",
            "حالة المدير", "حالة رئيس القسم", "موافقة", "رفض", "إلغاء"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(QLabel("طلبات الإجازات تحت الإجراء"))
        layout.addWidget(self.table)
        self.setLayout(layout)

    def load_pending_vacations(self):
        self.table.setRowCount(0)
        # جلب جميع الطلبات التي حالتها تحت الإجراء
        query = """
            SELECT v.id, e.name, v.type, v.start_date,
                   v.end_date, v.duration, v.status, v.dept_approval
            FROM vacations v
            JOIN employees e ON v.employee_id = e.id
            WHERE v.status='تحت الإجراء' OR v.dept_approval='تحت الإجراء'
            ORDER BY v.start_date DESC
        """
        self.db.execute_query(query)
        vacations = self.db.cursor.fetchall()
        self.table.setRowCount(len(vacations) if vacations else 1)
        if not vacations:
            self.table.setItem(0, 0, QTableWidgetItem("لا يوجد طلبات تحت الإجراء"))
            for col in range(1, 11):
                self.table.setItem(0, col, QTableWidgetItem(""))
            return

        for row_idx, row in enumerate(vacations):
            vac_id, emp_name, vac_type, start, end, days, status, dept_approval = row
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(vac_id) if vac_id else ''))
            self.table.setItem(row_idx, 1, QTableWidgetItem(emp_name if emp_name else ''))
            self.table.setItem(row_idx, 2, QTableWidgetItem(vac_type if vac_type else ''))
            self.table.setItem(row_idx, 3, QTableWidgetItem(start if start else ''))
            self.table.setItem(row_idx, 4, QTableWidgetItem(end if end else ''))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(days) if days else ''))
            self.table.setItem(row_idx, 6, QTableWidgetItem(status if status else ''))
            self.table.setItem(row_idx, 7, QTableWidgetItem(dept_approval if dept_approval else ''))

            approve_btn = QPushButton("موافقة")
            reject_btn = QPushButton("رفض")
            cancel_btn = QPushButton("إلغاء")

            approve_btn.clicked.connect(lambda _, v_id=vac_id: self.approve_vacation(v_id))
            reject_btn.clicked.connect(lambda _, v_id=vac_id: self.reject_vacation(v_id))
            cancel_btn.clicked.connect(lambda _, v_id=vac_id: self.cancel_vacation(v_id))

            # الشرط الصحيح لظهور الأزرار:
            # تظهر الأزرار لرئيس القسم إذا dept_approval == 'تحت الإجراء'
            # تظهر الأزرار للمدير إذا status == 'تحت الإجراء' و dept_approval == 'موافق'
            show_action = False
            if self.user_role == "department_head" and dept_approval == "تحت الإجراء":
                show_action = True
            elif self.user_role == "manager" and status == "تحت الإجراء" and dept_approval == "موافق":
                show_action = True

            if show_action:
                self.table.setCellWidget(row_idx, 8, approve_btn)
                self.table.setCellWidget(row_idx, 9, reject_btn)
                self.table.setCellWidget(row_idx, 10, cancel_btn)
            else:
                self.table.setCellWidget(row_idx, 8, QLabel("-"))
                self.table.setCellWidget(row_idx, 9, QLabel("-"))
                self.table.setCellWidget(row_idx, 10, QLabel("-"))

    def approve_vacation(self, vac_id):
        try:
            if self.user_role == "department_head":
                self.db.execute_query(
                    "UPDATE vacations SET dept_approval='موافق' WHERE id=?",
                    (vac_id,), commit=True
                )
            else:  # manager
                self.db.execute_query("SELECT employee_id, type, duration FROM vacations WHERE id=?", (vac_id,))
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
            self.load_pending_vacations()
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
            self.load_pending_vacations()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ أثناء الرفض: {e}")

    def cancel_vacation(self, vac_id):
        try:
            self.db.execute_query(
                "UPDATE vacations SET status='ملغاة', dept_approval='ملغاة' WHERE id=?",
                (vac_id,), commit=True
            )
            self.db.execute_query("SELECT employee_id, type, duration FROM vacations WHERE id=?", (vac_id,))
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
            self.load_pending_vacations()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ أثناء الإلغاء: {e}")

    def refresh_data(self):
        self.load_pending_vacations()