import os
import csv
from flask import Flask, render_template_string, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Use a non-interactive backend for Matplotlib
import matplotlib.pyplot as plt
from io import BytesIO, StringIO
import base64

# --- App Configuration ---
app = Flask(__name__)
# Define the path for the database file within a dedicated instance folder
instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance')
os.makedirs(instance_path, exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "expenses.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Model ---
class Expense(db.Model):
    """Represents an expense record in the database."""
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.Date, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"Expense(id={self.id}, amount={self.amount}, category='{self.category}', date='{self.date_posted}')"

# --- HTML Template ---
# Using render_template_string to keep everything in a single file.
# Styled with Tailwind CSS for a modern look.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Personal Expense Tracker</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="bg-gray-100 text-gray-800">
    <div class="container mx-auto p-4 sm:p-6 lg:p-8 max-w-4xl">
        <h1 class="text-3xl font-bold text-center mb-6 text-gray-700">Personal Expense Tracker</h1>

        <!-- Main Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            <!-- Left Column: Add Expense & Summary -->
            <div class="lg:col-span-1 space-y-6">
                <!-- Add Expense Form -->
                <div class="bg-white p-6 rounded-lg shadow-md">
                    <h2 class="text-xl font-semibold mb-4">Add New Expense</h2>
                    <form action="{{ url_for('add_expense') }}" method="post">
                        <div class="mb-4">
                            <label for="amount" class="block text-sm font-medium text-gray-600">Amount</label>
                            <input type="number" step="0.01" name="amount" id="amount" required
                                class="mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                        </div>
                        <div class="mb-4">
                            <label for="category" class="block text-sm font-medium text-gray-600">Category</label>
                            <input type="text" name="category" id="category" required
                                class="mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
                        </div>
                        <button type="submit"
                            class="w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition duration-150 ease-in-out">
                            Add Expense
                        </button>
                    </form>
                </div>

                <!-- Monthly Summary -->
                <div class="bg-white p-6 rounded-lg shadow-md">
                    <h2 class="text-xl font-semibold mb-4">Monthly Summary</h2>
                    <p class="text-gray-600 mb-2">Total for {{ month_name }}: <span class="font-bold text-lg text-green-600">${{ "%.2f"|format(total_expenses) }}</span></p>
                    {% if chart %}
                    <div class="mt-4">
                        <h3 class="text-md font-semibold mb-2 text-center">Expense Breakdown</h3>
                        <img src="data:image/png;base64,{{ chart }}" alt="Expense Chart" class="mx-auto rounded-lg">
                    </div>
                    {% else %}
                    <p class="text-gray-500 text-sm mt-4">No expenses this month to generate a chart.</p>
                    {% endif %}
                </div>
            </div>

            <!-- Right Column: Expense List -->
            <div class="lg:col-span-2 bg-white p-6 rounded-lg shadow-md">
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-xl font-semibold">All Expenses</h2>
                    <a href="{{ url_for('export_csv') }}" 
                       class="bg-green-500 text-white py-2 px-4 rounded-md hover:bg-green-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition duration-150 ease-in-out text-sm">
                        Export as CSV
                    </a>
                </div>
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Category</th>
                                <th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                                <th scope="col" class="relative px-6 py-3">
                                    <span class="sr-only">Delete</span>
                                </th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                            {% for expense in expenses %}
                            <tr>
                                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${{ "%.2f"|format(expense.amount) }}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ expense.category }}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ expense.date_posted.strftime('%Y-%m-%d') }}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                    <a href="{{ url_for('delete_expense', id=expense.id) }}" class="text-red-600 hover:text-red-900">Delete</a>
                                </td>
                            </tr>
                            {% else %}
                            <tr>
                                <td colspan="4" class="px-6 py-4 text-center text-gray-500">No expenses recorded yet.</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

# --- Charting Function ---
def create_expense_chart(expenses):
    """Generates a pie chart from expense data and returns it as a base64 string."""
    if not expenses:
        return None
    
    # Aggregate amounts by category
    category_totals = {}
    for expense in expenses:
        category_totals[expense.category] = category_totals.get(expense.category, 0) + expense.amount
    
    labels = category_totals.keys()
    sizes = category_totals.values()
    
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=plt.cm.Paired.colors)
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    
    # Save chart to a memory buffer
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    
    # Encode buffer to base64
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return image_base64

# --- Flask Routes ---
@app.route('/')
def index():
    """Main page: displays all expenses and the monthly summary."""
    # Query all expenses, ordered by most recent
    all_expenses = Expense.query.order_by(Expense.date_posted.desc()).all()
    
    # Calculate monthly summary
    today = datetime.utcnow()
    month_start = today.replace(day=1)
    
    monthly_expenses = [
        e for e in all_expenses 
        if e.date_posted.year == month_start.year and e.date_posted.month == month_start.month
    ]
    
    total_monthly_expenses = sum(e.amount for e in monthly_expenses)
    
    # Generate the chart
    chart_image = create_expense_chart(monthly_expenses)
    
    return render_template_string(
        HTML_TEMPLATE,
        expenses=all_expenses,
        total_expenses=total_monthly_expenses,
        month_name=today.strftime('%B'),
        chart=chart_image
    )

@app.route('/add', methods=['POST'])
def add_expense():
    """Handles the addition of a new expense."""
    amount = request.form.get('amount')
    category = request.form.get('category')
    
    if amount and category:
        try:
            new_expense = Expense(
                amount=float(amount),
                category=category.strip().title()
            )
            db.session.add(new_expense)
            db.session.commit()
        except ValueError:
            # Handle cases where amount is not a valid float
            pass
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete_expense(id):
    """Deletes an expense by its ID."""
    expense_to_delete = Expense.query.get_or_404(id)
    try:
        db.session.delete(expense_to_delete)
        db.session.commit()
    except:
        # Handle potential deletion errors
        pass
    return redirect(url_for('index'))

@app.route('/export')
def export_csv():
    """Exports all expenses to a CSV file."""
    all_expenses = Expense.query.all()
    
    # Use StringIO to build the CSV in memory as a string
    si = StringIO()
    writer = csv.writer(si)
    
    # Write header
    writer.writerow(['ID', 'Amount', 'Category', 'Date'])
    
    # Write data rows
    for expense in all_expenses:
        writer.writerow([
            expense.id,
            expense.amount,
            expense.category,
            expense.date_posted.strftime('%Y-%m-%d')
        ])
    
    # Create a BytesIO object, encode the string, and write it
    mem_file = BytesIO()
    mem_file.write(si.getvalue().encode('utf-8'))
    # Reset the file pointer to the beginning
    mem_file.seek(0)
    
    return send_file(
        mem_file,
        mimetype='text/csv',
        download_name='expenses.csv',
        as_attachment=True
    )

# --- Main Execution ---
if __name__ == '__main__':
    with app.app_context():
        # Create the database and tables if they don't exist
        db.create_all()
    app.run(debug=True)

