"""
Expense Tracker
Console app for income and expenses, category budgets,
monthly reports, and JSON file persistence.
"""

import json
import os
from datetime import datetime
from collections import defaultdict

DATA_FILE = "expense_data.json"
CATEGORIES = (
    "Food",
    "Transport",
    "Bills",
    "Shopping",
    "Health",
    "Education",
    "Entertainment",
    "Salary",
    "Other",
)


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def money(amount: float) -> str:
    return f"Rs {amount:,.2f}"


def parse_date(value: str):
    value = value.strip()
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        return None


class Tracker:
    def __init__(self, data_file: str = DATA_FILE):
        self.data_file = data_file
        self.records = []
        self.budgets = {}
        self.next_id = 1
        self.load()

    def load(self):
        if not os.path.exists(self.data_file):
            return
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.records = data.get("records", [])
            self.budgets = data.get("budgets", {})
            self.next_id = data.get("next_id", 1)
        except (json.JSONDecodeError, OSError, ValueError):
            print("Warning: could not load saved data. Starting with empty records.")
            self.records = []
            self.budgets = {}
            self.next_id = 1

    def save(self):
        data = {
            "next_id": self.next_id,
            "budgets": self.budgets,
            "records": self.records,
        }
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def add_record(self, kind: str, amount: float, category: str, note: str, date: str):
        if kind not in ("Income", "Expense"):
            return None, "Type must be Income or Expense."
        if amount <= 0:
            return None, "Amount must be greater than 0."
        if category not in CATEGORIES:
            return None, "Unknown category."
        if kind == "Income" and category not in ("Salary", "Other"):
            return None, "Income category must be Salary or Other."
        if kind == "Expense" and category == "Salary":
            return None, "Salary cannot be used for expenses."
        if parse_date(date) is None:
            return None, "Date must be YYYY-MM-DD."

        rec_id = self.next_id
        self.next_id += 1
        record = {
            "id": rec_id,
            "type": kind,
            "amount": round(amount, 2),
            "category": category,
            "note": note.strip(),
            "date": date,
            "created": now(),
        }
        self.records.append(record)
        self.save()
        warning = self._budget_warning(date[:7], category)
        message = f"{kind} of {money(amount)} added (ID {rec_id})."
        if warning:
            message += "\n" + warning
        return rec_id, message

    def find(self, rec_id: int):
        for record in self.records:
            if record["id"] == rec_id:
                return record
        return None

    def delete_record(self, rec_id: int):
        record = self.find(rec_id)
        if record is None:
            return False, "Record not found."
        self.records.remove(record)
        self.save()
        return True, f"Record {rec_id} deleted."

    def update_record(self, rec_id: int, amount=None, category=None, note=None, date=None):
        record = self.find(rec_id)
        if record is None:
            return False, "Record not found."
        if amount is not None:
            if amount <= 0:
                return False, "Amount must be greater than 0."
            record["amount"] = round(amount, 2)
        if category is not None:
            if category not in CATEGORIES:
                return False, "Unknown category."
            if record["type"] == "Income" and category not in ("Salary", "Other"):
                return False, "Income category must be Salary or Other."
            if record["type"] == "Expense" and category == "Salary":
                return False, "Salary cannot be used for expenses."
            record["category"] = category
        if note is not None:
            record["note"] = note.strip()
        if date is not None:
            if parse_date(date) is None:
                return False, "Date must be YYYY-MM-DD."
            record["date"] = date
        self.save()
        return True, f"Record {rec_id} updated."

    def set_budget(self, category: str, amount: float):
        if category not in CATEGORIES or category == "Salary":
            return False, "Set a budget for an expense category."
        if amount < 0:
            return False, "Budget cannot be negative."
        self.budgets[category] = round(amount, 2)
        self.save()
        return True, f"Monthly budget for {category} set to {money(amount)}."

    def _month_records(self, year_month: str):
        return [r for r in self.records if r["date"].startswith(year_month)]

    def totals(self, records=None):
        records = self.records if records is None else records
        income = sum(r["amount"] for r in records if r["type"] == "Income")
        expense = sum(r["amount"] for r in records if r["type"] == "Expense")
        return round(income, 2), round(expense, 2), round(income - expense, 2)

    def category_totals(self, records=None):
        records = self.records if records is None else records
        totals = defaultdict(float)
        for r in records:
            if r["type"] == "Expense":
                totals[r["category"]] += r["amount"]
        return {k: round(v, 2) for k, v in sorted(totals.items())}

    def _budget_warning(self, year_month: str, category: str):
        budget = self.budgets.get(category)
        if budget is None:
            return ""
        spent = sum(
            r["amount"]
            for r in self._month_records(year_month)
            if r["type"] == "Expense" and r["category"] == category
        )
        if spent > budget:
            return f"Budget alert: {category} is over budget ({money(spent)} / {money(budget)})."
        remaining = budget - spent
        if remaining <= budget * 0.1:
            return f"Budget alert: {category} is nearly used ({money(spent)} / {money(budget)})."
        return ""

    def monthly_report(self, year_month: str):
        records = self._month_records(year_month)
        income, expense, net = self.totals(records)
        by_cat = self.category_totals(records)
        alerts = []
        for category, spent in by_cat.items():
            budget = self.budgets.get(category)
            if budget is None:
                continue
            if spent > budget:
                alerts.append(f"{category}: OVER ({money(spent)} / {money(budget)})")
            else:
                alerts.append(f"{category}: {money(spent)} / {money(budget)}")
        return {
            "month": year_month,
            "income": income,
            "expense": expense,
            "net": net,
            "by_category": by_cat,
            "alerts": alerts,
            "records": records,
        }


def read_int(prompt: str):
    raw = input(prompt).strip()
    try:
        return int(raw)
    except ValueError:
        return None


def read_float(prompt: str):
    raw = input(prompt).strip()
    try:
        value = float(raw)
        if value != value:
            return None
        return value
    except ValueError:
        return None


def pause():
    input("\nPress Enter to continue...")


def print_header(title: str):
    print("\n" + "=" * 50)
    print(title.center(50))
    print("=" * 50)


def print_records(records):
    if not records:
        print("No records found.")
        return
    print(
        f"{'ID':<6} {'Date':<12} {'Type':<8} {'Category':<16} "
        f"{'Amount':>14}  Note"
    )
    print("-" * 78)
    for r in sorted(records, key=lambda x: (x["date"], x["id"])):
        print(
            f"{r['id']:<6} {r['date']:<12} {r['type']:<8} {r['category']:<16} "
            f"{money(r['amount']):>14}  {r.get('note', '')}"
        )


class App:
    def __init__(self):
        self.tracker = Tracker()

    def run(self):
        while True:
            print_header("EXPENSE TRACKER")
            print("1. Add Expense")
            print("2. Add Income")
            print("3. View All Records")
            print("4. Filter by Category")
            print("5. Monthly Report")
            print("6. Set Category Budget")
            print("7. Edit Record")
            print("8. Delete Record")
            print("9. Balance Summary")
            print("10. Exit")
            choice = input("\nEnter choice: ").strip()

            if choice == "1":
                self.add_entry("Expense")
            elif choice == "2":
                self.add_entry("Income")
            elif choice == "3":
                self.view_all()
            elif choice == "4":
                self.filter_category()
            elif choice == "5":
                self.monthly_report()
            elif choice == "6":
                self.set_budget()
            elif choice == "7":
                self.edit_record()
            elif choice == "8":
                self.delete_record()
            elif choice == "9":
                self.balance_summary()
            elif choice == "10":
                print("Thank you for using Expense Tracker.")
                break
            else:
                print("Invalid choice. Please try again.")

    def choose_category(self, kind: str):
        options = (
            [c for c in CATEGORIES if c != "Salary"]
            if kind == "Expense"
            else ["Salary", "Other"]
        )
        print("Categories:")
        for i, name in enumerate(options, start=1):
            print(f"  {i}. {name}")
        index = read_int("Select category number: ")
        if index is None or index < 1 or index > len(options):
            return None
        return options[index - 1]

    def add_entry(self, kind: str):
        print_header(f"ADD {kind.upper()}")
        amount = read_float("Amount: ")
        if amount is None:
            print("Invalid amount.")
            pause()
            return
        category = self.choose_category(kind)
        if category is None:
            print("Invalid category.")
            pause()
            return
        note = input("Note (optional): ").strip()
        date_raw = input(f"Date YYYY-MM-DD [Enter for {today()}]: ").strip()
        date = today() if date_raw == "" else date_raw
        _, message = self.tracker.add_record(kind, amount, category, note, date)
        print(message)
        pause()

    def view_all(self):
        print_header("ALL RECORDS")
        print_records(self.tracker.records)
        income, expense, net = self.tracker.totals()
        print("-" * 78)
        print(f"Income: {money(income)}   Expenses: {money(expense)}   Net: {money(net)}")
        pause()

    def filter_category(self):
        print_header("FILTER BY CATEGORY")
        print("Categories:")
        for i, name in enumerate(CATEGORIES, start=1):
            print(f"  {i}. {name}")
        index = read_int("Select category number: ")
        if index is None or index < 1 or index > len(CATEGORIES):
            print("Invalid category.")
            pause()
            return
        category = CATEGORIES[index - 1]
        matches = [r for r in self.tracker.records if r["category"] == category]
        print_records(matches)
        total = sum(r["amount"] for r in matches)
        print(f"\nTotal in {category}: {money(total)}")
        pause()

    def monthly_report(self):
        print_header("MONTHLY REPORT")
        month = input(f"Month YYYY-MM [Enter for {today()[:7]}]: ").strip()
        if month == "":
            month = today()[:7]
        try:
            datetime.strptime(month, "%Y-%m")
        except ValueError:
            print("Month must be YYYY-MM.")
            pause()
            return
        report = self.tracker.monthly_report(month)
        print(f"Month: {report['month']}")
        print(f"Income   : {money(report['income'])}")
        print(f"Expenses : {money(report['expense'])}")
        print(f"Net      : {money(report['net'])}")
        print("\nExpenses by category:")
        if report["by_category"]:
            for cat, amount in report["by_category"].items():
                print(f"  {cat:<16} {money(amount)}")
        else:
            print("  None")
        if report["alerts"]:
            print("\nBudgets:")
            for line in report["alerts"]:
                print(f"  {line}")
        print()
        print_records(report["records"])
        pause()

    def set_budget(self):
        print_header("SET MONTHLY BUDGET")
        options = [c for c in CATEGORIES if c != "Salary"]
        for i, name in enumerate(options, start=1):
            current = self.tracker.budgets.get(name)
            extra = f" (current {money(current)})" if current is not None else ""
            print(f"  {i}. {name}{extra}")
        index = read_int("Select category number: ")
        if index is None or index < 1 or index > len(options):
            print("Invalid category.")
            pause()
            return
        amount = read_float("Monthly budget amount: ")
        if amount is None:
            print("Invalid amount.")
            pause()
            return
        ok, message = self.tracker.set_budget(options[index - 1], amount)
        print(message)
        pause()

    def edit_record(self):
        print_header("EDIT RECORD")
        rec_id = read_int("Record ID: ")
        if rec_id is None:
            print("Invalid ID.")
            pause()
            return
        record = self.tracker.find(rec_id)
        if record is None:
            print("Record not found.")
            pause()
            return
        print_records([record])
        amount_raw = input("New amount (Enter to keep): ").strip()
        amount = None
        if amount_raw:
            try:
                amount = float(amount_raw)
            except ValueError:
                print("Invalid amount.")
                pause()
                return
        change_cat = input("Change category? (y/N): ").strip().lower()
        category = None
        if change_cat == "y":
            category = self.choose_category(record["type"])
            if category is None:
                print("Invalid category. Keeping the current one.")
        note_raw = input("New note (Enter to keep): ")
        note = None if note_raw == "" else note_raw
        date_raw = input("New date YYYY-MM-DD (Enter to keep): ").strip()
        date = None if date_raw == "" else date_raw
        ok, message = self.tracker.update_record(
            rec_id, amount=amount, category=category, note=note, date=date
        )
        print(message)
        pause()

    def delete_record(self):
        print_header("DELETE RECORD")
        rec_id = read_int("Record ID: ")
        if rec_id is None:
            print("Invalid ID.")
            pause()
            return
        confirm = input("Type YES to delete: ").strip()
        if confirm != "YES":
            print("Record was not deleted.")
            pause()
            return
        ok, message = self.tracker.delete_record(rec_id)
        print(message)
        pause()

    def balance_summary(self):
        print_header("BALANCE SUMMARY")
        income, expense, net = self.tracker.totals()
        print(f"Total income   : {money(income)}")
        print(f"Total expenses : {money(expense)}")
        print(f"Net balance    : {money(net)}")
        print("\nExpenses by category:")
        by_cat = self.tracker.category_totals()
        if by_cat:
            for cat, amount in by_cat.items():
                budget = self.tracker.budgets.get(cat)
                extra = f"  (budget {money(budget)})" if budget is not None else ""
                print(f"  {cat:<16} {money(amount)}{extra}")
        else:
            print("  None")
        pause()


if __name__ == "__main__":
    App().run()
