# Financial Transcript Analysis with LongT5 and Mistral

## 📌 Project Overview
This project processes financial transcripts using a combination of:
- **LongT5** (Google's long-text Transformer model) for summarization.
- **Mistral** (via LM Studio API) for extracting financial insights in a structured JSON format.

## 🏗️ Setup Instructions
### 1️⃣ Prerequisites
Ensure you have the following installed:
- Python (>=3.8)
- Pip
- LM Studio (running on `http://192.168.0.106:1234/v1/chat/completions`)
- Required Python libraries

### Clone the Repository
```sh
git clone https://github.com/your-repo/financial-transcript-analysis.git
cd financial-transcript-analysis
```

### Install Dependencies
```sh
pip install -r requirements.txt
```

### Model & API Setup
- **LongT5 Model**: Ensure the Hugging Face `google/long-t5-tglobal-base` model is available.
- **LM Studio**: Run LM Studio on the specified API URL (`192.168.0.106:1234`).

## 🗄️ Database Choice
This project uses **MongoDB** to extract, process, transcribe and store Financial Insights in JSON format .

## 🚀 Running the Project
Run the Python script:
```sh
python main.py
```

## 📌 Project Flow
1️⃣ **Summarize** the financial transcript using LongT5.
2️⃣ **Send** the summarized data to Mistral via the LM Studio API.
3️⃣ **Extract** structured financial insights in JSON format.

## 📬 API Response Format
```json
{
    "narrative": "DECISIVE" or "NON-DECISIVE",
    "direction": "LONG" or "SHORT",
    "Support": [<List of float values>],
    "Resistance": [<List of float values>],
    "Buy_Area": [<List of tuples (float, float), sorted descending>],
    "Sell_Area": [<List of tuples (float, float), sorted ascending>]
}
```

## 🔧 Troubleshooting
- **LM Studio not responding?** Ensure it's running and reachable at `http://192.168.0.106:1234/v1/chat/completions`.
- **Model download issues?** Run:
  ```sh
  pip install transformers torch
  ```
- **JSON decoding errors?** Verify Mistral’s response format using:
  ```sh
  print(response.text)
  ```


## 📞 Contact
For support, open an issue or reach out at `shubhamvidap18@gmail.com`.

