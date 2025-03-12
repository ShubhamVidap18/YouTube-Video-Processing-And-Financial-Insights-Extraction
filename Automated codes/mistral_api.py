import requests
import json
import re  # For extracting valid JSON if needed
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# Load LongT5 model and tokenizer for summarization
TOKENIZER = AutoTokenizer.from_pretrained("google/long-t5-tglobal-base")
MODEL = AutoModelForSeq2SeqLM.from_pretrained("google/long-t5-tglobal-base")

# LM Studio API URL (Ensure LM Studio is running on the specified IP and port)
LM_STUDIO_API_URL = "http://192.168.0.106:1234/v1/chat/completions"

def summarize_transcript(transcript):
    """
    Summarizes long transcripts using the LongT5 model.
    :param transcript: str, raw financial transcript
    :return: str, summarized transcript
    """
    inputs = TOKENIZER("summarize: " + transcript, return_tensors="pt", max_length=4096, truncation=True)
    summary_ids = MODEL.generate(**inputs, max_length=1024, min_length=100, length_penalty=2.0)
    return TOKENIZER.decode(summary_ids[0], skip_special_tokens=True)

def process_transcript_with_mistral(transcript, model="mistral", temperature=0.2):
    """
    Sends a financial transcript to Mistral (LM Studio API) for structured insights.
    :param transcript: str, raw financial transcript
    :param model: str, model name (default: "mistral")
    :param temperature: float, model response randomness (default: 0.2)
    :return: dict or None, structured financial insights
    """
    
    # Summarize transcript before sending to Mistral
    transcript = summarize_transcript(transcript)
    
    # Structured prompt for financial insights extraction
    prompt = f"""
    Analyze the following transcript and extract financial insights in JSON format:
    {transcript}

    The response must strictly follow this format:
    {{
        "narrative": "DECISIVE" or "NON-DECISIVE",
        "direction": "LONG" or "SHORT",
        "Support": [<List of float values>],
        "Resistance": [<List of float values>],
        "Buy_Area": [<List of tuples (float, float), sorted descending>],
        "Sell_Area": [<List of tuples (float, float), sorted ascending>]
    }}
    """
    
    # Prepare API request payload
    payload = {
        "model": model,  # Allow flexibility in model selection
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature
    }
    
    try:
        # Send request to LM Studio API
        response = requests.post(LM_STUDIO_API_URL, json=payload)
        response.raise_for_status()  # Raise error for HTTP issues
        
        response_data = response.json()  # Parse response JSON

        # Validate response structure
        if "choices" not in response_data or not response_data["choices"]:
            raise KeyError("Invalid API response structure: 'choices' key missing.")

        raw_output = response_data["choices"][0]["message"]["content"]
        
        # Attempt JSON parsing, fallback to regex extraction if needed
        try:
            structured_output = json.loads(raw_output)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw_output, re.DOTALL)  # Extract JSON block
            if match:
                structured_output = json.loads(match.group(0))
            else:
                raise ValueError("Failed to extract valid JSON from response.")
        
        return structured_output  # Return structured data
    
    except requests.exceptions.RequestException as req_error:
        print(f"❌ HTTP Request Error: {req_error}")
    except (json.JSONDecodeError, KeyError, ValueError) as parse_error:
        print(f"❌ JSON Parsing Error: {parse_error} | Raw Response: {response_data}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
    
    return None  # Return None in case of failure