"""
Bank Management System
Console app with accounts, deposits, withdrawals, transfers,
transaction history, and JSON file persistence.
"""

import hashlib
import json
import os
from datetime import datetime

DATA_FILE = "bank_data.json"
MIN_BALANCE = 500.0
MAX_DEPOSIT = 1_000_000.0
ACCOUNT_START = 1001


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def money(amount: float) -> str:
    return f"Rs {amount:,.2f}"


class Bank:
    def __init__(self, data_file: str = DATA_FILE):
        self.data_file = data_file
        self.accounts = {}
        self.next_account = ACCOUNT_START
        self.load()

    def load(self):
        if not os.path.exists(self.data_file):
            return
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.accounts = {int(k): v for k, v in data.get("accounts", {}).items()}
            self.next_account = data.get("next_account", ACCOUNT_START)
        except (json.JSONDecodeError, OSError, ValueError):
            print("Warning: could not load saved data. Starting with empty records.")
            self.accounts = {}
            self.next_account = ACCOUNT_START

    def save(self):
        data = {
            "next_account": self.next_account,
            "accounts": {str(k): v for k, v in self.accounts.items()},
        }
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def add_transaction(self, acc_no: int, kind: str, amount: float, note: str = ""):
        account = self.accounts[acc_no]
        account["transactions"].append(
            {
                "time": now(),
                "type": kind,
                "amount": round(amount, 2),
                "balance": round(account["balance"], 2),
                "note": note,
            }
        )

    def create_account(self, name: str, pin: str, initial: float, acc_type: str):
        name = name.strip()
        if not name:
            return None, "Name cannot be empty."
        if not pin.isdigit() or len(pin) != 4:
            return None, "PIN must be exactly 4 digits."
        if initial < MIN_BALANCE:
            return None, f"Minimum opening balance is {money(MIN_BALANCE)}."
        if acc_type not in ("Savings", "Current"):
            return None, "Account type must be Savings or Current."

        acc_no = self.next_account
        self.next_account += 1
        self.accounts[acc_no] = {
            "name": name,
            "pin": hash_pin(pin),
            "balance": round(initial, 2),
            "type": acc_type,
            "created": now(),
            "transactions": [],
        }
        self.add_transaction(acc_no, "OPEN", initial, "Account opened")
        self.save()
        return acc_no, f"Account created. Your account number is {acc_no}."

    def authenticate(self, acc_no: int, pin: str):
        account = self.accounts.get(acc_no)
        if account is None:
            return False, "Account not found."
        if account["pin"] != hash_pin(pin):
            return False, "Incorrect PIN."
        return True, account

    def deposit(self, acc_no: int, amount: float):
        if amount <= 0:
            return False, "Deposit amount must be greater than 0."
        if amount > MAX_DEPOSIT:
            return False, f"Maximum deposit per transaction is {money(MAX_DEPOSIT)}."
        self.accounts[acc_no]["balance"] = round(
            self.accounts[acc_no]["balance"] + amount, 2
        )
        self.add_transaction(acc_no, "DEPOSIT", amount)
        self.save()
        return True, f"Deposited {money(amount)}. New balance: {money(self.accounts[acc_no]['balance'])}."

    def withdraw(self, acc_no: int, amount: float):
        if amount <= 0:
            return False, "Withdrawal amount must be greater than 0."
        balance = self.accounts[acc_no]["balance"]
        if amount > balance:
            return False, "Insufficient funds."
        if balance - amount < MIN_BALANCE:
            return False, f"Must keep at least {money(MIN_BALANCE)} in the account."
        self.accounts[acc_no]["balance"] = round(balance - amount, 2)
        self.add_transaction(acc_no, "WITHDRAW", amount)
        self.save()
        return True, f"Withdrew {money(amount)}. New balance: {money(self.accounts[acc_no]['balance'])}."

    def transfer(self, from_acc: int, to_acc: int, amount: float):
        if from_acc == to_acc:
            return False, "Cannot transfer to the same account."
        if to_acc not in self.accounts:
            return False, "Destination account not found."
        if amount <= 0:
            return False, "Transfer amount must be greater than 0."
        balance = self.accounts[from_acc]["balance"]
        if amount > balance:
            return False, "Insufficient funds."
        if balance - amount < MIN_BALANCE:
            return False, f"Must keep at least {money(MIN_BALANCE)} in the account."

        self.accounts[from_acc]["balance"] = round(balance - amount, 2)
        self.accounts[to_acc]["balance"] = round(
            self.accounts[to_acc]["balance"] + amount, 2
        )
        self.add_transaction(
            from_acc, "TRANSFER OUT", amount, f"To account {to_acc}"
        )
        self.add_transaction(
            to_acc, "TRANSFER IN", amount, f"From account {from_acc}"
        )
        self.save()
        return True, (
            f"Transferred {money(amount)} to account {to_acc}. "
            f"New balance: {money(self.accounts[from_acc]['balance'])}."
        )

    def change_pin(self, acc_no: int, old_pin: str, new_pin: str):
        ok, msg = self.authenticate(acc_no, old_pin)
        if not ok:
            return False, msg
        if not new_pin.isdigit() or len(new_pin) != 4:
            return False, "New PIN must be exactly 4 digits."
        if old_pin == new_pin:
            return False, "New PIN must be different from the current PIN."
        self.accounts[acc_no]["pin"] = hash_pin(new_pin)
        self.save()
        return True, "PIN changed successfully."

    def delete_account(self, acc_no: int):
        name = self.accounts[acc_no]["name"]
        del self.accounts[acc_no]
        self.save()
        return True, f"Account {acc_no} ({name}) has been closed."


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
        if value != value:  # NaN
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


def print_account_summary(acc_no: int, account: dict):
    print(f"Account Number : {acc_no}")
    print(f"Name           : {account['name']}")
    print(f"Type           : {account['type']}")
    print(f"Balance        : {money(account['balance'])}")
    print(f"Opened On      : {account['created']}")


def print_statement(account: dict, last_n: int = 20):
    txs = account["transactions"][-last_n:]
    if not txs:
        print("No transactions yet.")
        return
    print(f"{'Date/Time':<20} {'Type':<14} {'Amount':>14} {'Balance':>14}  Note")
    print("-" * 78)
    for tx in txs:
        print(
            f"{tx['time']:<20} {tx['type']:<14} "
            f"{money(tx['amount']):>14} {money(tx['balance']):>14}  {tx.get('note', '')}"
        )


class App:
    def __init__(self):
        self.bank = Bank()
        self.current = None

    def run(self):
        while True:
            if self.current is None:
                choice = self.main_menu()
                if choice == "1":
                    self.create_account()
                elif choice == "2":
                    self.login()
                elif choice == "3":
                    self.list_accounts()
                elif choice == "4":
                    print("Thank you for using the Bank Management System.")
                    break
                else:
                    print("Invalid choice. Please try again.")
            else:
                choice = self.account_menu()
                if choice == "1":
                    self.show_balance()
                elif choice == "2":
                    self.do_deposit()
                elif choice == "3":
                    self.do_withdraw()
                elif choice == "4":
                    self.do_transfer()
                elif choice == "5":
                    self.show_statement()
                elif choice == "6":
                    self.show_details()
                elif choice == "7":
                    self.do_change_pin()
                elif choice == "8":
                    self.do_close_account()
                elif choice == "9":
                    print("Logged out.")
                    self.current = None
                else:
                    print("Invalid choice. Please try again.")

    def main_menu(self):
        print_header("BANK MANAGEMENT SYSTEM")
        print("1. Create Account")
        print("2. Login")
        print("3. View All Accounts (summary)")
        print("4. Exit")
        return input("\nEnter choice: ").strip()

    def account_menu(self):
        acc_no = self.current
        name = self.bank.accounts[acc_no]["name"]
        print_header(f"Welcome, {name}")
        print(f"Logged in as account {acc_no}")
        print("1. Check Balance")
        print("2. Deposit")
        print("3. Withdraw")
        print("4. Transfer")
        print("5. Transaction History")
        print("6. Account Details")
        print("7. Change PIN")
        print("8. Close Account")
        print("9. Logout")
        return input("\nEnter choice: ").strip()

    def create_account(self):
        print_header("CREATE ACCOUNT")
        name = input("Full name: ").strip()
        acc_type = input("Account type (Savings / Current): ").strip().title()
        pin = input("Choose a 4-digit PIN: ").strip()
        pin2 = input("Confirm PIN: ").strip()
        if pin != pin2:
            print("PINs do not match.")
            pause()
            return
        initial = read_float(f"Opening deposit (min {money(MIN_BALANCE)}): ")
        if initial is None:
            print("Invalid amount.")
            pause()
            return
        acc_no, message = self.bank.create_account(name, pin, initial, acc_type)
        print(message)
        if acc_no is not None:
            print("Keep your account number and PIN safe.")
        pause()

    def login(self):
        print_header("LOGIN")
        acc_no = read_int("Account number: ")
        if acc_no is None:
            print("Invalid account number.")
            pause()
            return
        pin = input("PIN: ").strip()
        ok, result = self.bank.authenticate(acc_no, pin)
        if not ok:
            print(result)
            pause()
            return
        self.current = acc_no
        print(f"Login successful. Hello, {result['name']}!")
        pause()

    def list_accounts(self):
        print_header("ALL ACCOUNTS")
        if not self.bank.accounts:
            print("No accounts yet.")
            pause()
            return
        print(f"{'Acc No':<10} {'Name':<22} {'Type':<10} {'Balance':>14}")
        print("-" * 58)
        for acc_no, acc in sorted(self.bank.accounts.items()):
            print(
                f"{acc_no:<10} {acc['name'][:22]:<22} {acc['type']:<10} "
                f"{money(acc['balance']):>14}"
            )
        pause()

    def show_balance(self):
        acc = self.bank.accounts[self.current]
        print_header("BALANCE")
        print(f"Available balance: {money(acc['balance'])}")
        pause()

    def do_deposit(self):
        print_header("DEPOSIT")
        amount = read_float("Amount: ")
        if amount is None:
            print("Invalid amount.")
            pause()
            return
        ok, message = self.bank.deposit(self.current, amount)
        print(message)
        pause()

    def do_withdraw(self):
        print_header("WITHDRAW")
        amount = read_float("Amount: ")
        if amount is None:
            print("Invalid amount.")
            pause()
            return
        ok, message = self.bank.withdraw(self.current, amount)
        print(message)
        pause()

    def do_transfer(self):
        print_header("TRANSFER")
        to_acc = read_int("Destination account number: ")
        if to_acc is None:
            print("Invalid account number.")
            pause()
            return
        amount = read_float("Amount: ")
        if amount is None:
            print("Invalid amount.")
            pause()
            return
        ok, message = self.bank.transfer(self.current, to_acc, amount)
        print(message)
        pause()

    def show_statement(self):
        print_header("TRANSACTION HISTORY")
        print_statement(self.bank.accounts[self.current])
        pause()

    def show_details(self):
        print_header("ACCOUNT DETAILS")
        print_account_summary(self.current, self.bank.accounts[self.current])
        pause()

    def do_change_pin(self):
        print_header("CHANGE PIN")
        old_pin = input("Current PIN: ").strip()
        new_pin = input("New 4-digit PIN: ").strip()
        new_pin2 = input("Confirm new PIN: ").strip()
        if new_pin != new_pin2:
            print("New PINs do not match.")
            pause()
            return
        ok, message = self.bank.change_pin(self.current, old_pin, new_pin)
        print(message)
        pause()

    def do_close_account(self):
        print_header("CLOSE ACCOUNT")
        confirm = input("Type YES to permanently close this account: ").strip()
        if confirm != "YES":
            print("Account was not closed.")
            pause()
            return
        pin = input("Enter PIN to confirm: ").strip()
        ok, result = self.bank.authenticate(self.current, pin)
        if not ok:
            print(result)
            pause()
            return
        _, message = self.bank.delete_account(self.current)
        print(message)
        self.current = None
        pause()


if __name__ == "__main__":
    App().run()
