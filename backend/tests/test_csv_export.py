from app.services.csv_export import spreadsheet_safe, export_csv


def test_spreadsheet_payloads_sanitized():
    for prefix in ('=', '+', '-', '@'):
        assert spreadsheet_safe(prefix + 'cmd').startswith("'")
    assert spreadsheet_safe('Ordinary customer') == 'Ordinary customer'


def test_csv_quotes_customer_data():
    value = export_csv(['name', 'phone'], [('A, B', '+123')])
    assert '"A, B"' in value
    assert "'+123" in value
