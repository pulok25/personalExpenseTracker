import sqlite3
import csv
from datetime import datetime
import matplotlib.pyplot as plt
from collections import defaultdict

class ExpenseTracker:
    def __init__(self, db_name="expenses.db"):
        """Initialize the expense tracker with SQLite database"""
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_table()
    
    def create_table(self):
        """Create expenses table if it doesn't exist"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT
            )
        ''')
        self.conn.commit()
    
    def add_expense(self, category, amount, description=""):
        """Add a new expense (CREATE operation)"""
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            self.cursor.execute('''
                INSERT INTO expenses (date, category, amount, description)
                VALUES (?, ?, ?, ?)
            ''', (date, category, float(amount), description))
            self.conn.commit()
            print(f"✓ Expense added: ${amount} for {category}")
            return True
        except Exception as e:
            print(f"Error adding expense: {e}")
            return False
    
    def view_all_expenses(self):
        """View all expenses (READ operation)"""
        self.cursor.execute('SELECT * FROM expenses ORDER BY date DESC')
        expenses = self.cursor.fetchall()
        
        if not expenses:
            print("No expenses found.")
            return
        
        print("\n" + "="*80)
        print(f"{'ID':<5} {'Date':<20} {'Category':<15} {'Amount':<10} {'Description'}")
        print("="*80)
        
        for exp in expenses:
            print(f"{exp[0]:<5} {exp[1]:<20} {exp[2]:<15} ${exp[3]:<9.2f} {exp[4]}")
        print("="*80 + "\n")
    
    def view_by_category(self, category):
        """View expenses filtered by category"""
        self.cursor.execute('''
            SELECT * FROM expenses WHERE category = ? ORDER BY date DESC
        ''', (category,))
        expenses = self.cursor.fetchall()
        
        if not expenses:
            print(f"No expenses found for category: {category}")
            return
        
        print(f"\n--- Expenses for {category} ---")
        for exp in expenses:
            print(f"ID: {exp[0]} | Date: {exp[1]} | Amount: ${exp[3]:.2f} | {exp[4]}")
    
    def update_expense(self, expense_id, category=None, amount=None, description=None):
        """Update an existing expense (UPDATE operation)"""
        updates = []
        params = []
        
        if category:
            updates.append("category = ?")
            params.append(category)
        if amount:
            updates.append("amount = ?")
            params.append(float(amount))
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        
        if not updates:
            print("No updates provided.")
            return False
        
        params.append(expense_id)
        query = f"UPDATE expenses SET {', '.join(updates)} WHERE id = ?"
        
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            if self.cursor.rowcount > 0:
                print(f"✓ Expense ID {expense_id} updated successfully")
                return True
            else:
                print(f"No expense found with ID {expense_id}")
                return False
        except Exception as e:
            print(f"Error updating expense: {e}")
            return False
    
    def delete_expense(self, expense_id):
        """Delete an expense (DELETE operation)"""
        try:
            self.cursor.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
            self.conn.commit()
            if self.cursor.rowcount > 0:
                print(f"✓ Expense ID {expense_id} deleted")
                return True
            else:
                print(f"No expense found with ID {expense_id}")
                return False
        except Exception as e:
            print(f"Error deleting expense: {e}")
            return False
    
    def monthly_summary(self, month=None, year=None):
        """Generate monthly summary report"""
        if not month:
            month = datetime.now().month
        if not year:
            year = datetime.now().year
        
        # Query expenses for the specified month
        self.cursor.execute('''
            SELECT category, SUM(amount) as total
            FROM expenses
            WHERE strftime('%m', date) = ? AND strftime('%Y', date) = ?
            GROUP BY category
            ORDER BY total DESC
        ''', (f"{month:02d}", str(year)))
        
        results = self.cursor.fetchall()
        
        if not results:
            print(f"No expenses found for {month}/{year}")
            return
        
        print(f"\n{'='*50}")
        print(f"Monthly Summary: {month}/{year}")
        print(f"{'='*50}")
        
        total = 0
        category_data = {}
        
        for category, amount in results:
            print(f"{category:<20} ${amount:>10.2f}")
            total += amount
            category_data[category] = amount
        
        print(f"{'='*50}")
        print(f"{'TOTAL':<20} ${total:>10.2f}")
        print(f"{'='*50}\n")
        
        return category_data
    
    def export_to_csv(self, filename="expenses_export.csv"):
        """Export all expenses to CSV file"""
        self.cursor.execute('SELECT * FROM expenses ORDER BY date')
        expenses = self.cursor.fetchall()
        
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['ID', 'Date', 'Category', 'Amount', 'Description'])
                writer.writerows(expenses)
            print(f"✓ Expenses exported to {filename}")
            return True
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return False
    
    def visualize_expenses(self, month=None, year=None):
        """Create visualization of expenses by category"""
        if not month:
            month = datetime.now().month
        if not year:
            year = datetime.now().year
        
        category_data = self.monthly_summary(month, year)
        
        if not category_data:
            return
        
        # Create pie chart
        categories = list(category_data.keys())
        amounts = list(category_data.values())
        
        plt.figure(figsize=(10, 6))
        plt.subplot(1, 2, 1)
        plt.pie(amounts, labels=categories, autopct='%1.1f%%', startangle=90)
        plt.title(f'Expense Distribution - {month}/{year}')
        
        # Create bar chart
        plt.subplot(1, 2, 2)
        plt.bar(categories, amounts, color='skyblue')
        plt.xlabel('Category')
        plt.ylabel('Amount ($)')
        plt.title(f'Expenses by Category - {month}/{year}')
        plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(f'expenses_{month}_{year}.png')
        print(f"✓ Chart saved as expenses_{month}_{year}.png")
        plt.show()
    
    def get_categories(self):
        """Get list of all unique categories"""
        self.cursor.execute('SELECT DISTINCT category FROM expenses')
        return [row[0] for row in self.cursor.fetchall()]
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Main function to run the expense tracker"""
    tracker = ExpenseTracker()
    
    while True:
        print("\n" + "="*50)
        print("Personal Expense Tracker")
        print("="*50)
        print("1. Add Expense")
        print("2. View All Expenses")
        print("3. View Expenses by Category")
        print("4. Update Expense")
        print("5. Delete Expense")
        print("6. Monthly Summary")
        print("7. Visualize Expenses")
        print("8. Export to CSV")
        print("9. Exit")
        print("="*50)
        
        choice = input("Enter your choice (1-9): ").strip()
        
        if choice == '1':
            category = input("Enter category (e.g., Food, Transport, Entertainment): ").strip()
            amount = input("Enter amount: ").strip()
            description = input("Enter description (optional): ").strip()
            tracker.add_expense(category, amount, description)
        
        elif choice == '2':
            tracker.view_all_expenses()
        
        elif choice == '3':
            categories = tracker.get_categories()
            if categories:
                print("Available categories:", ", ".join(categories))
            category = input("Enter category: ").strip()
            tracker.view_by_category(category)
        
        elif choice == '4':
            tracker.view_all_expenses()
            expense_id = input("Enter expense ID to update: ").strip()
            category = input("New category (press Enter to skip): ").strip()
            amount = input("New amount (press Enter to skip): ").strip()
            description = input("New description (press Enter to skip): ").strip()
            
            tracker.update_expense(
                expense_id,
                category if category else None,
                amount if amount else None,
                description if description else None
            )
        
        elif choice == '5':
            tracker.view_all_expenses()
            expense_id = input("Enter expense ID to delete: ").strip()
            confirm = input(f"Are you sure you want to delete expense {expense_id}? (yes/no): ")
            if confirm.lower() == 'yes':
                tracker.delete_expense(expense_id)
        
        elif choice == '6':
            month = input("Enter month (1-12, press Enter for current): ").strip()
            year = input("Enter year (press Enter for current): ").strip()
            tracker.monthly_summary(
                int(month) if month else None,
                int(year) if year else None
            )
        
        elif choice == '7':
            month = input("Enter month (1-12, press Enter for current): ").strip()
            year = input("Enter year (press Enter for current): ").strip()
            tracker.visualize_expenses(
                int(month) if month else None,
                int(year) if year else None
            )
        
        elif choice == '8':
            filename = input("Enter filename (press Enter for 'expenses_export.csv'): ").strip()
            tracker.export_to_csv(filename if filename else "expenses_export.csv")
        
        elif choice == '9':
            print("Thank you for using Expense Tracker!")
            tracker.close()
            break
        
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()