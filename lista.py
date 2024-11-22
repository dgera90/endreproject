from flask import Flask, request, render_template, send_file, session
import pandas as pd
import io
from datetime import datetime
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'random_secret_key'  # Titkos kulcs a session kezeléshez

@app.route('/')
def upload_file():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_file():
    file = request.files['file']

    if not file:
        error_message = "Hiányzó fájl"
        return render_template('index.html', error_message=error_message)

    # Ellenőrizzük, hogy a fájl CSV kiterjesztésű-e
    if not file.filename.endswith('.csv'):
        error_message = "Csak CSV fájlokat tölthetsz fel."
        return render_template('index.html', error_message=error_message)

    try:
        # CSV fájl beolvasása, UTF-8 kódolás, pontosvessző elválasztóval
        df = pd.read_csv(file, delimiter=';', encoding='utf-8')

        # Ellenőrizzük, hogy vannak-e a szükséges oszlopok
        if 'Termék Név' not in df.columns:
            error_message = "Nincs 'Termék Név' nevű oszlop a fájlban."
            return render_template('index.html', error_message=error_message)
        if 'Mennyiség' not in df.columns:
            error_message = "Nincs 'Mennyiség' nevű oszlop a fájlban."
            return render_template('index.html', error_message=error_message)

        # Számoljuk össze a termékek mennyiségét
        result = df.groupby('Termék Név')['Mennyiség'].sum().reset_index()
        result.columns = ['Termék Név', 'Összes Mennyiség']

        # Az eredményeket tároljuk a session-ben
        session['result'] = result.to_dict(orient='records')

        return render_template('index.html', result=result.to_dict(orient='records'))

    except Exception as e:
        error_message = f"Hiba a fájl feldolgozásakor: {e}"
        return render_template('index.html', error_message=error_message)
    
@app.route('/download_csv', methods=['POST'])
def download_csv():
    # Ellenőrizzük, hogy van-e eredmény a session-ben
    result = session.get('result')

    if not result:
        return "Nincs eredmény a fájl letöltéséhez."

    # Az eredményt pandas DataFrame-ként alakítjuk
    result_df = pd.DataFrame(result)

    # Eredmény írása CSV-be memóriába UTF-8 kódolással
    output = io.StringIO()
    result_df.to_csv(output, index=False, sep=';', encoding='utf-8-sig')  # Helyes elválasztó és kódolás
    output.seek(0)

    # Fájl neve a jelenlegi dátummal
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    download_name = f"eredmeny_{current_time}.csv"

    # A fájl visszaküldése
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),  # UTF-8 BOM kódolás
        mimetype='text/csv',
        as_attachment=True,
        download_name=download_name  # Fájl neve dátummal
    )

@app.route('/download_excel', methods=['POST'])
def download_excel():
    # Ellenőrizzük, hogy van-e eredmény a session-ben
    result = session.get('result')

    if not result:
        return "Nincs eredmény a fájl letöltéséhez."

    # Az eredményt pandas DataFrame-ként alakítjuk
    result_df = pd.DataFrame(result)

    # Excel fájl generálása
    wb = Workbook()
    ws = wb.active
    ws.title = "Eredmény"

    # Átalakítjuk a DataFrame-et a munkalapra
    for r in dataframe_to_rows(result_df, index=False, header=True):
        ws.append(r)

    # Oszlopok szélességének beállítása
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter  # Az oszlop betűje
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = (max_length + 2)  # Néhány karaktert adunk hozzá
        ws.column_dimensions[column].width = adjusted_width

    # Fájl létrehozása a memóriában
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    # Fájl neve a jelenlegi dátummal
    current_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    download_name = f"eredmeny_{current_time}.xlsx"

    # A fájl visszaküldése
    return send_file(
        output,
        as_attachment=True,
        download_name=download_name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == '__main__':
    app.run(debug=True)
