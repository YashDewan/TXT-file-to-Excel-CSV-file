from flask import Flask, request, send_file, jsonify, render_template  # include render_template
import csv
from collections import defaultdict
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FILE = 'output.csv'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

def parse_dn(dn_line):
    dn_value = dn_line.strip()[4:]
    parts = dn_value.split(',')
    dn_dict = defaultdict(list)
    for part in parts:
        if '=' in part:
            k, v = part.split('=', 1)
            dn_dict[k].append(v)
    return dn_dict

def flatten_dn_dict(dn_dict):
    result = {}
    for k, v_list in dn_dict.items():
        for i, v in enumerate(v_list):
            result[f"{k}{i+1}"] = v
    return result

def process_ldif_file(filename):
    records = []
    current_record = None

    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if line == '':
            if current_record:
                records.append(current_record)
                current_record = None
            continue

        if line.startswith('dn: cn='):
            if current_record:
                records.append(current_record)
            dn_dict = parse_dn(line)
            dn_flat = flatten_dn_dict(dn_dict)
            current_record = dn_flat
        else:
            if current_record is not None and ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                existing_keys = [k for k in current_record if k.startswith(key)]
                new_key = f"{key}{len(existing_keys)+1}"
                current_record[new_key] = value

    if current_record:
        records.append(current_record)

    header_keys = set()
    for rec in records:
        header_keys.update(rec.keys())
    header = sorted(header_keys)

    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header, extrasaction='ignore')
        writer.writeheader()
        for rec in records:
            row = {k: rec.get(k, '') for k in header}
            writer.writerow(row)

    return len(records), OUTPUT_FILE

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    records_processed, output_path = process_ldif_file(filepath)
    return send_file(output_path, as_attachment=True, download_name="converted_output.csv")

if __name__ == '__main__':
    app.run(debug=True)
