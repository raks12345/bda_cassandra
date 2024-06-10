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
session.execute("CREATE KEYSPACE IF NOT EXISTS fitness WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}")
session.set_keyspace('fitness')
session.execute('''CREATE TABLE IF NOT EXISTS fitness_entries (
                        id UUID PRIMARY KEY,
                        exercise TEXT,
                        repetitions DECIMAL,
                        muscle TEXT,
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
    rows = session.execute('SELECT * FROM fitness_entries')
    entries = [{'id': row.id, 'exercise': row.exercise, 'repetitions': row.repetitions, 'muscle': row.muscle, 'date': row.date} for row in rows]

    # Extract distinct muscles from entries
    all_muscles = [entry['muscle'] for entry in entries]

    # Filter out empty muscles
    non_empty_muscles = set(muscle for muscle in all_muscles if muscle)

    # Get the selected muscle from the request
    selected_muscle = request.args.get('muscle')

    # Filter entries for the selected muscle if specified
    if selected_muscle:
        entries = [entry for entry in entries if entry['muscle'] == selected_muscle]

    return render_template('index.html', entries=entries, muscles=non_empty_muscles, selected_muscle=selected_muscle)

@app.route('/add', methods=['POST'])
def add():
    exercise = request.form['exercise']
    repetitions = request.form['repetitions']
    muscle = request.form.get('muscle')
    date = request.form.get('date')

    if exercise != "" and repetitions != "":
        if muscle == "":
            muscle = "default"

        # Insert entry into the database
        session.execute('INSERT INTO fitness_entries (id, exercise, repetitions, muscle, date) VALUES (%s, %s, %s, %s, %s)',
                        (uuid4(), exercise, float(repetitions), muscle, date))

    return redirect(url_for('index'))

@app.route('/delete/<uuid:id>')
def delete(id):
    session.execute('DELETE FROM fitness_entries WHERE id = %s', [id])
    return redirect(url_for('index'))

@app.route('/entries_count_chart')
def entries_count_chart():
    rows = session.execute('SELECT * FROM fitness_entries')
    entry_counts = defaultdict(int)
    for row in rows:
        entry_counts[row.muscle] += 1

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
    rows = session.execute('SELECT * FROM fitness_entries')
    entry_counts = defaultdict(int)
    for row in rows:
        entry_counts[row.muscle] += 1

    # Create a histogram
    labels = list(entry_counts.keys())
    sizes = list(entry_counts.values())
    fig, ax = create_plot()
    ax.bar(labels, sizes)
    ax.set_xlabel('Muscle')
    ax.set_ylabel('Number of Entries')
    ax.set_title('Number of Entries in Each Muscle')

    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    # Save the histogram to a BytesIO object
    img_bytes = save_plot(fig)

    # Send the histogram image as a file
    return send_file(img_bytes, mimetype='image/png')

@app.route('/entry_date')
def entry_date():
    # Fetch data from the database
    rows = session.execute('SELECT * FROM fitness_entries')
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
    rows = session.execute('SELECT * FROM fitness_entries')
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

