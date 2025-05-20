from datetime import datetime

def reset_emergency_vacation_balances(db):
    today = datetime.today()
    if today.month == 1 and today.day == 1:  # أول يوم في السنة
        db.execute_query("UPDATE employees SET emergency_vacation_balance=12", commit=True)