import matplotlib
matplotlib.use('Agg')  # Use the 'Agg' backend which doesn't require a display
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import io
from flask import send_file, Flask, render_template, request, redirect, url_for
from cassandra.cluster import Cluster
from uuid import uuid4
from collections import defaultdict

app = Flask(__name__)

# Connect to the Cassandra cluster
cluster = Cluster(['127.0.0.1'])  # Replace '127.0.0.1' with your Cassandra node IP
session = cluster.connect()
session.execute("CREATE KEYSPACE IF NOT EXISTS finance WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}")
session.set_keyspace('finance')
session.execute('''CREATE TABLE IF NOT EXISTS finance_entries (
                        id UUID PRIMARY KEY,
                        entry_type TEXT,
                        amount DECIMAL,
                        category TEXT,
                        date TEXT
                   )''')

# Ensure each request has its own Matplotlib instance
def create_plot():
    fig, ax = plt.subplots()
    return fig, ax

def save_plot(fig):
    img_bytes = io.BytesIO()
    fig.savefig(img_bytes, format='png')
    img_bytes.seek(0)
    plt.close(fig)
    return img_bytes

@app.route('/')
def index():
    # Get all entries
    rows = session.execute('SELECT * FROM finance_entries')
    entries = [{'id': row.id, 'entry_type': row.entry_type, 'amount': row.amount, 'category': row.category, 'date': row.date} for row in rows]

    # Extract distinct categories from entries
    all_categories = [entry['category'] for entry in entries]

    # Filter out empty categories
    non_empty_categories = set(category for category in all_categories if category)

    # Get the selected category from the request
    selected_category = request.args.get('category')

    # Filter entries for the selected category if specified
    if selected_category:
        entries = [entry for entry in entries if entry['category'] == selected_category]

    return render_template('index.html', entries=entries, categories=non_empty_categories, selected_category=selected_category)

@app.route('/add', methods=['POST'])
def add():
    entry_type = request.form['entry_type']
    amount = request.form['amount']
    category = request.form.get('category')
    date = request.form.get('date')

    if entry_type != "" and amount != "":
        if category == "":
            category = "default"

        # Insert entry into the database
        session.execute('INSERT INTO finance_entries (id, entry_type, amount, category, date) VALUES (%s, %s, %s, %s, %s)',
                        (uuid4(), entry_type, float(amount), category, date))

    return redirect(url_for('index'))

@app.route('/delete/<uuid:id>')
def delete(id):
    session.execute('DELETE FROM finance_entries WHERE id = %s', [id])
    return redirect(url_for('index'))

@app.route('/entries_count_chart')
def entries_count_chart():
    rows = session.execute('SELECT * FROM finance_entries')
    entry_counts = defaultdict(int)
    for row in rows:
        entry_counts[row.category] += 1

    # Create a pie chart
    labels = list(entry_counts.keys())
    sizes = list(entry_counts.values())
    fig, ax = create_plot()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%')
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle

    # Save the plot to a BytesIO object
    img_bytes = save_plot(fig)

    # Send the image as a file
    return send_file(img_bytes, mimetype='image/png')

@app.route('/entry_histogram')
def entry_histogram():
    # Fetch data from the database
    rows = session.execute('SELECT * FROM finance_entries')
    entry_counts = defaultdict(int)
    for row in rows:
        entry_counts[row.category] += 1

    # Create a histogram
    labels = list(entry_counts.keys())
    sizes = list(entry_counts.values())
    fig, ax = create_plot()
    ax.bar(labels, sizes)
    ax.set_xlabel('Category')
    ax.set_ylabel('Number of Entries')
    ax.set_title('Number of Entries in Each Category')

    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    # Save the histogram to a BytesIO object
    img_bytes = save_plot(fig)

    # Send the histogram image as a file
    return send_file(img_bytes, mimetype='image/png')

@app.route('/entry_date')
def entry_date():
    # Fetch data from the database
    rows = session.execute('SELECT * FROM finance_entries')
    entry_counts = defaultdict(int)

    for row in rows:
        # Extract date from the 'date' field (assuming date is stored in 'YYYY-MM-DD' format)
        date = row.date.split('-')[2]
        entry_counts[date] += 1

    # Create a histogram
    dates = list(entry_counts.keys())
    entries = list(entry_counts.values())

    # Convert dates to integers for proper sorting and plotting
    dates_int = [int(date) for date in dates]
    dates_sorted, entries_sorted = zip(*sorted(zip(dates_int, entries)))

    fig, ax = create_plot()
    ax.bar(dates_sorted, entries_sorted)
    ax.set_xlabel('Day of the Month')
    ax.set_ylabel('Number of Entries')
    ax.set_title('Number of Entries by Day of the Month')

    # Set x-axis ticks to show every day
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))

    # Ensure integers are displayed for days on x-axis
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%d'))

    # Set the x-axis limit from 1 to 31 (assuming 31-day month format)
    ax.set_xlim(1, 31)

    # Save the histogram to a BytesIO object
    img_bytes = save_plot(fig)

    # Send the histogram image as a file
    return send_file(img_bytes, mimetype='image/png')

@app.route('/entry_month')
def entry_month():
    # Fetch data from the database
    rows = session.execute('SELECT * FROM finance_entries')
    entry_counts = defaultdict(int)

    for row in rows:
        # Extract month from the 'date' field (assuming date is stored in 'YYYY-MM-DD' format)
        month = row.date.split('-')[1]
        entry_counts[month] += 1

    # Create a histogram
    months = list(entry_counts.keys())
    entries = list(entry_counts.values())

    # Convert months to integers for proper sorting and plotting
    months_int = [int(month) for month in months]
    months_sorted, entries_sorted = zip(*sorted(zip(months_int, entries)))

    fig, ax = create_plot()
    ax.bar(months_sorted, entries_sorted)
    ax.set_xlabel('Month')
    ax.set_ylabel('Number of Entries')
    ax.set_title('Number of Entries by Month')

    # Set x-axis ticks to show every month
    ax.xaxis.set_major_locator(ticker.MultipleLocator(1))

    # Ensure integers are displayed for months on x-axis
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%d'))

    # Set the x-axis limit from 1 to 12 (assuming 12-month year format)
    ax.set_xlim(1, 12)

    # Save the histogram to a BytesIO object
    img_bytes = save_plot(fig)

    # Send the histogram image as a file
    return send_file(img_bytes, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True)

