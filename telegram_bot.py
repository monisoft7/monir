from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler
)
import logging
from datetime import datetime, timedelta
from PyQt6.QtCore import QDate

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
(
    PASSWORD, NATIONAL_ID, SERIAL_NUMBER, MAIN_MENU,
    VACATION_TYPE, VACATION_DEATH_TYPE, VACATION_DEATH_RELATION,
    VACATION_DATE, VACATION_DURATION, CONFIRM_REQUEST
) = range(10)

BOT_PASSWORD = "adw2025"

class EmployeeQueryBot:
    def __init__(self, token, db_manager):
        self.token = token
        self.db = db_manager
        self.setup_handlers()

    def setup_handlers(self):
        self.application = ApplicationBuilder().token(self.token).build()
    
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.check_password)],
                NATIONAL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_national_id)],
                SERIAL_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_serial_number)],
                MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_main_menu)],
                VACATION_TYPE: [
                    MessageHandler(filters.Regex("^(سنوية|وفاة|حج|زواج|وضع|مرضية|↩️ رجوع|إلغاء)$"), self.handle_vacation_type),
                    MessageHandler(filters.Regex("^(وضع عادي|وضع توأم)$"), self.handle_vacation_subtype)
                ],
                VACATION_DEATH_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_vacation_death_type)],
                VACATION_DEATH_RELATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_vacation_death_relation)],
                VACATION_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_vacation_date_selection)],
                VACATION_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_vacation_duration)],
                CONFIRM_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm_request)]
            },
            fallbacks=[
                CommandHandler('cancel', self.cancel),
                MessageHandler(filters.Regex("^إلغاء$"), self.cancel)
            ],
            allow_reentry=True
        )
        self.application.add_handler(conv_handler)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "مرحباً بك في نظام إدارة الموظفين\n"
            "الرجاء إدخال كلمة المرور:",
            reply_markup=ReplyKeyboardMarkup([["إلغاء"]], resize_keyboard=True)
        )
        return PASSWORD

    async def check_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text != BOT_PASSWORD:
            await update.message.reply_text("كلمة مرور خاطئة، حاول مرة أخرى", reply_markup=ReplyKeyboardMarkup([["إلغاء"]], resize_keyboard=True))
            return PASSWORD
        await update.message.reply_text("الرجاء إدخال الرقم الوطني:", reply_markup=ReplyKeyboardMarkup([["إلغاء"]], resize_keyboard=True))
        return NATIONAL_ID

    async def handle_national_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['national_id'] = update.message.text
        await update.message.reply_text("الرجاء إدخال الرقم الآلي:", reply_markup=ReplyKeyboardMarkup([["إلغاء"]], resize_keyboard=True))
        return SERIAL_NUMBER

    async def handle_serial_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        employee = self.get_employee(
            context.user_data['national_id'],
            update.message.text
        )
        if not employee:
            await update.message.reply_text("بيانات غير صحيحة، الرجاء المحاولة مرة أخرى", reply_markup=ReplyKeyboardMarkup([["إلغاء"]], resize_keyboard=True))
            return ConversationHandler.END
        context.user_data['employee'] = employee
        # حفظ emp_id للاستخدام في show_work_days
        context.user_data['employee_id'] = employee['id']
        await self.show_main_menu(update)
        return MAIN_MENU

    async def show_main_menu(self, update: Update):
        keyboard = [
            ["📅 طلب إجازة", "📝 سجل الغياب"],
            ["📊 الدرجة الوظيفية", "✈️ رصيد الإجازات"],
            ["📋 سجل الإجازات", "📅 أيام العمل"],
            ["👤 بياناتي الأساسية"],
            ["إلغاء"]
        ]
        await update.message.reply_text(
            "اختر الخيار المطلوب:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    async def handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if text == "إلغاء":
            return await self.cancel(update, context)
        if text.startswith("❌ إلغاء الإجازة"):
            try:
                vac_id = int(text.replace("❌ إلغاء الإجازة", "").strip())
                self.db.execute_query("SELECT type, duration, status FROM vacations WHERE id=? AND employee_id=?", (vac_id, context.user_data['employee']['id']))
                row = self.db.cursor.fetchone()
                if not row:
                    await update.message.reply_text("تعذر العثور على الإجازة.")
                    return MAIN_MENU
                vac_type, duration, status = row
                if status != "approved":
                    await update.message.reply_text("لا يمكن إلغاء إلا الإجازات الموافق عليها فقط.")
                    return MAIN_MENU
                self.db.execute_query("UPDATE vacations SET status='canceled' WHERE id=?", (vac_id,))
                if vac_type == "سنوية":
                    self.db.execute_query(
                        "UPDATE employees SET vacation_balance = vacation_balance + ? WHERE id = ?",
                        (duration, context.user_data['employee']['id'])
                    )
                await update.message.reply_text("تم إلغاء الإجازة بنجاح وتم استرجاع الأيام للرصيد.")
                await self.show_vacation_history(update, context)
                return MAIN_MENU
            except Exception as e:
                await update.message.reply_text(f"حدث خطأ أثناء الإلغاء: {str(e)}")
                return MAIN_MENU

        if text == "📅 طلب إجازة":
            await self.show_vacation_types(update)
            return VACATION_TYPE
        elif text == "📝 سجل الغياب":
            await self.show_absence_records(update, context)
            return MAIN_MENU
        elif text == "📊 الدرجة الوظيفية":
            await self.show_job_grade(update, context)
            return MAIN_MENU
        elif text == "✈️ رصيد الإجازات":
            await self.show_vacation_balance(update, context)
            return MAIN_MENU
        elif text == "📋 سجل الإجازات":
            await self.show_vacation_history(update, context)
            return MAIN_MENU
        elif text == "📅 أيام العمل":
            await self.show_work_days(update, context)
            return MAIN_MENU
        elif text == "👤 بياناتي الأساسية":
            await self.show_basic_info(update, context)
            return MAIN_MENU
        else:
            await self.show_main_menu(update)
            return MAIN_MENU

    async def show_vacation_types(self, update: Update):
        keyboard = [
            ["سنوية", "وفاة", "حج"],
            ["زواج", "وضع", "مرضية"],
            ["↩️ رجوع", "إلغاء"]
        ]
        await update.message.reply_text(
            "اختر نوع الإجازة:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    async def handle_vacation_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text in ("إلغاء",):
            return await self.cancel(update, context)
        vac_type = update.message.text
        if vac_type == "↩️ رجوع":
            await self.show_main_menu(update)
            return MAIN_MENU
        context.user_data['vacation'] = {"type": vac_type}
        if vac_type == "وفاة":
            keyboard = [["وفاة من الدرجة الأولى", "وفاة من الدرجة الثانية"], ["↩️ رجوع", "إلغاء"]]
            await update.message.reply_text(
                "اختر نوع إجازة الوفاة:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return VACATION_DEATH_TYPE
        elif vac_type == "وضع":
            keyboard = [["وضع عادي", "وضع توأم"], ["↩️ رجوع", "إلغاء"]]
            await update.message.reply_text(
                "اختر نوع إجازة الوضع:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return VACATION_TYPE
        else:
            context.user_data['date_step'] = 'year'
            await update.message.reply_text(
                "الرجاء إدخال سنة بداية الإجازة (مثال: 2023):",
                reply_markup=ReplyKeyboardMarkup([["↩️ رجوع", "إلغاء"]], resize_keyboard=True)
            )
            return VACATION_DATE

    async def handle_vacation_subtype(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text == "إلغاء":
            return await self.cancel(update, context)
        subtype = update.message.text
        if subtype == "↩️ رجوع":
            await self.show_vacation_types(update)
            return VACATION_TYPE
        context.user_data['vacation']['subtype'] = subtype
        context.user_data['date_step'] = 'year'
        await update.message.reply_text(
            "الرجاء إدخال سنة بداية الإجازة (مثال: 2023):",
            reply_markup=ReplyKeyboardMarkup([["↩️ رجوع", "إلغاء"]], resize_keyboard=True)
        )
        return VACATION_DATE

    async def show_work_days(self, update, context):
        emp_id = context.user_data.get('employee_id')
        if not emp_id:
            await update.message.reply_text("لم أستطع تحديد الموظف. يرجى التأكد من اختيار الموظف أولاً.")
            return

        # جلب أيام العمل من قاعدة البيانات
        self.db.execute_query("SELECT work_days FROM employees WHERE id = ?", (emp_id,))
        result = self.db.cursor.fetchone()
        if not result:
            await update.message.reply_text("لم يتم العثور على بيانات هذا الموظف.")
            return

        work_days = result[0] or ""
        if work_days == "الندب" or work_days == "تفرغ":
            await update.message.reply_text(f"حالة الموظف: {work_days}")
        elif work_days:
            # تحويل النص لقائمة أيام وفترات
            days_map = {
                "0": "السبت", "1": "الأحد", "2": "الإثنين",
                "3": "الثلاثاء", "4": "الأربعاء", "5": "الخميس", "6": "الجمعة"
            }
            periods_map = {"M": "صباحية", "E": "مسائية", "F": "كامل اليوم"}
            msg = "أيام العمل:\n"
            for wd in work_days.split(","):
                if ":" in wd:
                    day, period = wd.split(":")
                    msg += f"- {days_map.get(day, day)}: {periods_map.get(period, period)}\n"
            await update.message.reply_text(msg)
        else:
            await update.message.reply_text("لا توجد بيانات أيام عمل لهذا الموظف.")



    async def handle_vacation_death_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text == "إلغاء":
            return await self.cancel(update, context)
        death_type = update.message.text
        if death_type == "↩️ رجوع":
            await self.show_vacation_types(update)
            return VACATION_TYPE
        context.user_data['vacation']['death_type'] = death_type
        if death_type == "وفاة من الدرجة الأولى":
            keyboard = [
                ["أب", "أم"],
                ["ابن", "ابنة"],
                ["زوج", "زوجة"],
                ["جد", "جدة"],
                ["↩️ رجوع", "إلغاء"]
            ]
            await update.message.reply_text(
                "اختر صلة القرابة مع المتوفى:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return VACATION_DEATH_RELATION
        else:
            context.user_data['vacation']['relation'] = "أقارب آخرون"
            context.user_data['vacation']['duration'] = 3
            context.user_data['date_step'] = 'year'
            await update.message.reply_text(
                "الرجاء إدخال سنة الوفاة (مثال: 2023):",
                reply_markup=ReplyKeyboardMarkup([["↩️ رجوع", "إلغاء"]], resize_keyboard=True)
            )
            return VACATION_DATE

    async def handle_vacation_death_relation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text == "إلغاء":
            return await self.cancel(update, context)
        relation = update.message.text
        if relation == "↩️ رجوع":
            keyboard = [["وفاة من الدرجة الأولى", "وفاة من الدرجة الثانية"], ["↩️ رجوع", "إلغاء"]]
            await update.message.reply_text(
                "اختر نوع إجازة الوفاة:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return VACATION_DEATH_TYPE
        context.user_data['vacation']['relation'] = relation
        if relation == "زوج":
            context.user_data['vacation']['duration'] = 130
        else:
            context.user_data['vacation']['duration'] = 7
        context.user_data['date_step'] = 'year'
        await update.message.reply_text(
            "الرجاء إدخال سنة الوفاة (مثال: 2023):",
            reply_markup=ReplyKeyboardMarkup([["↩️ رجوع", "إلغاء"]], resize_keyboard=True)
        )
        return VACATION_DATE

    async def handle_vacation_date_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        if text == "إلغاء":
            return await self.cancel(update, context)
        if text == "↩️ رجوع":
            if context.user_data['vacation']['type'] == "وفاة":
                if context.user_data['vacation'].get('death_type'):
                    await self.handle_vacation_death_type(update, context)
                    return VACATION_DEATH_TYPE
                else:
                    await self.show_vacation_types(update)
                    return VACATION_TYPE
            else:
                await self.show_vacation_types(update)
                return VACATION_TYPE

        try:
            current_step = context.user_data.get('date_step', 'year')
            if current_step == 'year':
                year = int(text)
                if year < 2000 or year > 2100:
                    raise ValueError("السنة يجب أن تكون بين 2000 و 2100")
                context.user_data['vacation']['year'] = year
                context.user_data['date_step'] = 'month'
                keyboard = [[str(i) for i in range(1, 13)]]
                keyboard.append(["↩️ رجوع", "إلغاء"])
                await update.message.reply_text(
                    "الرجاء اختيار رقم الشهر:",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
                )
                return VACATION_DATE
            elif current_step == 'month':
                month = int(text)
                if not 1 <= month <= 12:
                    raise ValueError("الشهر يجب أن يكون بين 1 و 12")
                context.user_data['vacation']['month'] = month
                context.user_data['date_step'] = 'day'
                year = context.user_data['vacation']['year']
                if month == 2:
                    days_in_month = 29 if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0) else 28
                elif month in [4, 6, 9, 11]:
                    days_in_month = 30
                else:
                    days_in_month = 31
                day_keyboard = []
                row = []
                for i in range(1, days_in_month + 1):
                    row.append(str(i))
                    if len(row) == 7:
                        day_keyboard.append(row)
                        row = []
                if row:
                    day_keyboard.append(row)
                day_keyboard.append(["↩️ رجوع", "إلغاء"])
                await update.message.reply_text(
                    f"الرجاء اختيار رقم اليوم:",
                    reply_markup=ReplyKeyboardMarkup(day_keyboard, resize_keyboard=True, one_time_keyboard=True)
                )
                return VACATION_DATE
            elif current_step == 'day':
                day = int(text)
                year = context.user_data['vacation']['year']
                month = context.user_data['vacation']['month']
                if not QDate(year, month, day).isValid():
                    raise ValueError("تاريخ غير صالح")
                start_date = f"{year}-{month:02d}-{day:02d}"
                context.user_data['vacation']['start_date'] = start_date
                vac_type = context.user_data['vacation']['type']

                if vac_type == "سنوية":
                    await update.message.reply_text(
                        "أدخل عدد أيام الإجازة السنوية (1-90):",
                        reply_markup=ReplyKeyboardMarkup([["↩️ رجوع", "إلغاء"]], resize_keyboard=True)
                    )
                    return VACATION_DURATION
                elif vac_type == "مرضية":
                    await update.message.reply_text(
                        "أدخل عدد أيام الإجازة المرضية:",
                        reply_markup=ReplyKeyboardMarkup([["↩️ رجوع", "إلغاء"]], resize_keyboard=True)
                    )
                    return VACATION_DURATION
                elif vac_type == "وضع":
                    subtype = context.user_data['vacation'].get('subtype', 'وضع عادي')
                    if subtype == "وضع توأم":
                        context.user_data['vacation']['duration'] = 112
                    else:
                        context.user_data['vacation']['duration'] = 98
                else:
                    if vac_type == "حج":
                        context.user_data['vacation']['duration'] = 20
                    elif vac_type == "زواج":
                        context.user_data['vacation']['duration'] = 14

                end_date = (QDate(year, month, day).addDays(context.user_data['vacation']['duration'] - 1)).toString("yyyy-MM-dd")
                context.user_data['vacation']['end_date'] = end_date
                if 'date_step' in context.user_data:
                    del context.user_data['date_step']
                return await self.show_vacation_summary(update, context)
            return VACATION_DATE
        except Exception as e:
            await update.message.reply_text(
                f"خطأ في الإدخال: {str(e)}\nالرجاء المحاولة مرة أخرى:",
                reply_markup=ReplyKeyboardMarkup([["↩️ رجوع", "إلغاء"]], resize_keyboard=True)
            )
            return VACATION_DATE

    async def handle_vacation_duration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text == "إلغاء":
            return await self.cancel(update, context)
        if update.message.text == "↩️ رجوع":
            context.user_data['date_step'] = 'day'
            await update.message.reply_text(
                "اختر اليوم من جديد:",
                reply_markup=ReplyKeyboardRemove()
            )
            return VACATION_DATE
        try:
            duration = int(update.message.text)
            vac_type = context.user_data['vacation']['type']
            if vac_type == "سنوية":
                if not 1 <= duration <= 90:
                    raise ValueError("مدة الإجازة السنوية يجب أن تكون بين 1 و 90 يوم")
            elif vac_type == "مرضية":
                if duration < 1:
                    raise ValueError("مدة الإجازة المرضية يجب أن تكون يوم واحد على الأقل")
            context.user_data['vacation']['duration'] = duration
            if 'start_date' in context.user_data['vacation']:
                start_date = QDate.fromString(context.user_data['vacation']['start_date'], "yyyy-MM-dd")
                end_date = start_date.addDays(duration - 1)
                context.user_data['vacation']['end_date'] = end_date.toString("yyyy-MM-dd")
                return await self.show_vacation_summary(update, context)
            else:
                await update.message.reply_text(
                    "الرجاء إدخال تاريخ بداية الإجازة (YYYY-MM-DD):",
                    reply_markup=ReplyKeyboardMarkup([["↩️ رجوع", "إلغاء"]], resize_keyboard=True)
                )
                return VACATION_DATE
        except Exception as e:
            await update.message.reply_text(
                f"قيمة غير صالحة. الرجاء إدخال عدد أيام صحيح: {str(e)}",
                reply_markup=ReplyKeyboardMarkup([["↩️ رجوع", "إلغاء"]], resize_keyboard=True)
            )
            return VACATION_DURATION

    async def show_vacation_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        vacation = context.user_data['vacation']
        summary = "📋 ملخص طلب الإجازة:\n\n"
        summary += f"• النوع: {vacation['type']}\n"
        if vacation['type'] == "وفاة":
            summary += f"• نوع الوفاة: {vacation.get('death_type', '')}\n"
            if vacation.get('relation'):
                summary += f"• صلة القرابة: {vacation['relation']}\n"
        summary += f"• تاريخ البداية: {vacation['start_date']}\n"
        summary += f"• تاريخ النهاية: {vacation['end_date']}\n"
        if vacation['type'] in ["وضع"]:
            weeks = vacation['duration'] // 7
            summary += f"• المدة: {weeks} أسبوع\n"
        else:
            summary += f"• المدة: {vacation['duration']} يوم\n"
        summary += "\nهل تريد تأكيد طلب الإجازة؟"
        keyboard = [["نعم", "لا", "↩️ رجوع", "إلغاء"]]
        await update.message.reply_text(
            summary,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return CONFIRM_REQUEST



    async def confirm_request(self, update, context):
        if 'employee' not in context.user_data:
            await update.message.reply_text("حدث خطأ: لم يتم اختيار الموظف، يرجى البدء من جديد.")
            return MAIN_MENU

        response = update.message.text.lower()
        if response == "إلغاء":
            await update.message.reply_text("تم إلغاء الطلب.")
            return MAIN_MENU

        try:
            vacation = context.user_data['vacation']
            emp_id = context.user_data['employee']['id']

            # بناء التواريخ إذا ناقصة
            if 'start_date' not in vacation:
                if all(k in vacation for k in ('year', 'month', 'day')):
                    start_date = f"{vacation['year']}-{vacation['month']:02d}-{vacation['day']:02d}"
                    vacation['start_date'] = start_date
                else:
                    raise ValueError("بيانات التاريخ غير مكتملة، الرجاء إعادة إدخال التاريخ")
            if 'end_date' not in vacation:
                start_dt = datetime.strptime(vacation['start_date'], "%Y-%m-%d")
                end_dt = start_dt + timedelta(days=vacation['duration'] - 1)
                vacation['end_date'] = end_dt.strftime("%Y-%m-%d")

            # تحديد الحالة الافتراضية للإجازة
            status = 'تحت الإجراء'
            if vacation['type'] in ["مرضية", "وضع"]:
                status = 'موافق'  # الموافقة تلقائيًا للإجازات المرضية والوضع

            # إضافة الملاحظة تلقائيًا حسب النوع
            notes = vacation.get('notes', '').strip() if vacation.get('notes') else ""
            extra_note = ""
            if vacation['type'] == "مرضية":
                extra_note = "هذه الإجازة مرضية وتمت الموافقة عليها تلقائيًا."
            elif vacation['type'] == "وضع":
                extra_note = "هذه إجازة وضع وتمت الموافقة عليها تلقائيًا."
            if extra_note:
                notes = (notes + "\n" if notes else "") + extra_note

            # حفظ الطلب في قاعدة البيانات
            self.db.execute_query(
                "INSERT INTO vacations (employee_id, type, relation, start_date, end_date, duration, notes, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (emp_id, vacation['type'], vacation.get('relation'), vacation['start_date'], vacation['end_date'], vacation['duration'], notes, status)
            )

            # إرسال إشعار إلى المدير عند الموافقة التلقائية
            if status == "موافق":
                self.notify_manager(emp_id, vacation['type'], vacation['start_date'], vacation['end_date'])

            await update.message.reply_text(
                f"✅ تم تقديم طلب الإجازة بنجاح\n"
                f"النوع: {vacation['type']}\n"
                f"الحالة: {status}\n"
                f"من {vacation['start_date']} إلى {vacation['end_date']}\n"
                f"المدة: {vacation['duration']} يوم\n"
                f"ملاحظات: {notes}"
            )

            if 'vacation' in context.user_data:
                del context.user_data['vacation']
            return MAIN_MENU
        except Exception as e:
            await update.message.reply_text(
                f"حدث خطأ أثناء تقديم الطلب: {str(e)}\nالرجاء المحاولة مرة أخرى أو التواصل مع الدعم."
            )
            return ConversationHandler.END


    # مثال لدالة إدخال رقم وطني (طبق هذا في كل دوال الحقول الحساسة)
    async def ask_national_id(self, update, context):
        user_input = update.message.text.strip()
        if user_input == "إلغاء":
            await update.message.reply_text("تم الإلغاء.")
            return ConversationHandler.END


    async def show_vacation_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text == "↩️ رجوع" or update.message.text == "إلغاء":
            await self.show_main_menu(update)
            return MAIN_MENU
        try:
            self.db.execute_query("""
                SELECT vacation_balance 
                FROM employees 
                WHERE id = ?
            """, (context.user_data['employee']['id'],))
            balance = self.db.cursor.fetchone()[0]
            await update.message.reply_text(
                f"✈️ رصيد الإجازات: {balance} يوم حتى تاريخ 31/12/2024",
                reply_markup=ReplyKeyboardMarkup([["↩️ رجوع", "إلغاء"]], resize_keyboard=True)
            )
            return MAIN_MENU
        except Exception as e:
            await update.message.reply_text(f"حدث خطأ: {str(e)}")
            return MAIN_MENU


            keyboard = []
            response = "📋 سجل الإجازات (آخر 10 إجازات):\n\n"
            for rec in records:
                vac_id, vac_type, start, end, days, status = rec
                response += (
                    f"📅 {start} إلى {end}\n"
                    f"• النوع: {vac_type}\n"
                    f"• المدة: {days} يوم\n"
                    f"• الحالة: {status}\n"
                )
                if status == "approved":
                    keyboard.append([f"❌ إلغاء الإجازة {vac_id}"])
                response += "\n"
            keyboard.append(["↩️ رجوع", "إلغاء"])
            await update.message.reply_text(
                response,
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return MAIN_MENU
        except Exception as e:
            await update.message.reply_text(f"حدث خطأ: {str(e)}")
            return MAIN_MENU

    async def show_absence_records(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text == "↩️ رجوع" or update.message.text == "إلغاء":
            await self.show_main_menu(update)
            return MAIN_MENU
        try:
            self.db.execute_query("""
                SELECT date, type, duration 
                FROM absences 
                WHERE employee_id = ?
                ORDER BY date DESC 
                LIMIT 30
            """, (context.user_data['employee']['id'],))
            records = self.db.cursor.fetchall()
            if not records:
                await update.message.reply_text(
                    "لا يوجد سجل غياب لك",
                    reply_markup=ReplyKeyboardMarkup([["↩️ رجوع", "إلغاء"]], resize_keyboard=True)
                )
                return MAIN_MENU
            response = "📝 سجل الغياب (آخر 30 يوم):\n"
            for date, abs_type, duration in records:
                response += f"\n📅 {date}: {abs_type} ({duration} يوم)"
            await update.message.reply_text(
                response,
                reply_markup=ReplyKeyboardMarkup([["↩️ رجوع", "إلغاء"]], resize_keyboard=True)
            )
            return MAIN_MENU
        except Exception as e:
            await update.message.reply_text(f"حدث خطأ: {str(e)}")
            return MAIN_MENU

    async def show_job_grade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text == "↩️ رجوع" or update.message.text == "إلغاء":
            await self.show_main_menu(update)
            return MAIN_MENU
        try:
            self.db.execute_query("""
                SELECT job_grade, grade_date, bonus 
                FROM employees 
                WHERE id = ?
            """, (context.user_data['employee']['id'],))
            grade, grade_date, bonus = self.db.cursor.fetchone()
            response = (
                "📊 الدرجة الوظيفية:\n"
                f"• الدرجة: {grade}\n"
                f"• تاريخ الحصول: {grade_date}\n"
                f"• العلاوة: {bonus}"
            )
            await update.message.reply_text(
                response,
                reply_markup=ReplyKeyboardMarkup([["↩️ رجوع", "إلغاء"]], resize_keyboard=True)
            )
            return MAIN_MENU
        except Exception as e:
            await update.message.reply_text(f"حدث خطأ: {str(e)}")
            return MAIN_MENU

    async def show_vacation_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text == "↩️ رجوع" or update.message.text == "إلغاء":
            await self.show_main_menu(update)
            return MAIN_MENU
        try:
            self.db.execute_query("""
                SELECT vacation_balance 
                FROM employees 
                WHERE id = ?
            """, (context.user_data['employee']['id'],))
            balance = self.db.cursor.fetchone()[0]
            await update.message.reply_text(
                f"✈️ رصيد الإجازات: {balance} يوم",
                reply_markup=ReplyKeyboardMarkup([["↩️ رجوع", "إلغاء"]], resize_keyboard=True)
            )
            return MAIN_MENU
        except Exception as e:
            await update.message.reply_text(f"حدث خطأ: {str(e)}")
            return MAIN_MENU

    async def show_basic_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text == "↩️ رجوع" or update.message.text == "إلغاء":
            await self.show_main_menu(update)
            return MAIN_MENU
        employee = context.user_data['employee']
        response = (
            "👤 البيانات الأساسية:\n"
            f"• الاسم: {employee['name']}\n"
            f"• الرقم الوطني: {employee['national_id']}\n"
            f"• القسم: {employee['department']}\n"
            f"• تاريخ التعيين: {employee['hiring_date']}"
        )
        await update.message.reply_text(
            response,
            reply_markup=ReplyKeyboardMarkup([["↩️ رجوع", "إلغاء"]], resize_keyboard=True)
        )
        return MAIN_MENU



    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "تم إلغاء العملية والعودة للقائمة الرئيسية.",
            reply_markup=ReplyKeyboardRemove()
        )
        await self.show_main_menu(update)
        return MAIN_MENU

    def get_employee(self, national_id: str, serial_number: str) -> dict:
        try:
            self.db.execute_query("""
                SELECT id, name, national_id, department, 
                       job_grade, hiring_date, vacation_balance
                FROM employees
                WHERE national_id=? AND serial_number=?
            """, (national_id, serial_number))
            if row := self.db.cursor.fetchone():
                return {
                    'id': row[0],
                    'name': row[1],
                    'national_id': row[2],
                    'department': row[3],
                    'job_grade': row[4],
                    'hiring_date': row[5],
                    'vacation_balance': row[6]
                }
        except Exception as e:
            logger.error(f"Error fetching employee: {str(e)}")
        return None

    def run(self):
        self.application.run_polling()