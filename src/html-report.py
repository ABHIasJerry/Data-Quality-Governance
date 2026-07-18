import pandas as pd
import matplotlib.pyplot as plt
import base64
from io import BytesIO

def generate_report(csv_file_path, output_file="test_report.html", company_name="Your Company Name"):
    # 1. Load the data
    df = pd.read_csv(csv_file_path)

    # 2. Generate Pie Chart
    status_counts = df['test status'].value_counts()
    plt.figure(figsize=(5, 5))
    plt.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', 
            colors=['#28a745', '#dc3545', '#ffc107'], startangle=140)
    plt.title('Test Pass/Fail Distribution')
    
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    chart_base64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close()

    # 3. Create Bootstrap HTML structure
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <title>Test Automation Report</title>
        <style>
            .header-section {{ background-color: #f8f9fa; padding: 20px; border-bottom: 3px solid #0d6efd; margin-bottom: 30px; }}
            .logo {{ max-height: 80px; }}
            .table-container {{ box-shadow: 0 0 20px rgba(0,0,0,0.1); border-radius: 10px; overflow: hidden; }}
        </style>
    </head>
    <body class="bg-light">
        <div class="container py-5">
            <!-- Header Section -->
            <div class="header-section d-flex align-items-center justify-content-between">
                <div>
                    <h1>{company_name}</h1>
                    <p class="text-muted">Quality Assurance Execution Report</p>
                </div>
                <img src="https://via.placeholder.com/150x80?text=Company+Logo" class="logo" alt="Logo">
            </div>

            <!-- Chart Section -->
            <div class="row mb-5">
                <div class="col-md-6 offset-md-3 text-center">
                    <div class="card p-3">
                        <img src="data:image/png;base64,{chart_base64}" class="img-fluid" alt="Chart">
                    </div>
                </div>
            </div>

            <!-- Table Section -->
            <div class="table-container bg-white p-4">
                <h3>Detailed Execution Logs</h3>
                <div class="table-responsive">
                    {df.to_html(classes='table table-striped table-hover', index=False)}
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    with open(output_file, "w") as f:
        f.write(html_template)
    
    print(f"Professional report generated: {output_file}")

# Run the function
generate_report('your_report.csv', company_name="Tech Solutions Inc.")
