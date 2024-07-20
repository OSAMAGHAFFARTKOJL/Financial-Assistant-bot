import os
import openai
import pdfplumber
import pandas as pd
import re
import matplotlib.pyplot as plt
import streamlit as st

client = openai.OpenAI(
    api_key="8d024f37fbdd2166941276baf3e2796851e085a916b9df97e3aeaccff0516040",
    base_url="https://api.together.xyz/v1",
)

# Function to extract tables from PDF
def extract_tables_from_pdf(pdf_path):
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                df = pd.DataFrame(table[1:], columns=table[0])
                tables.append(df)
    return tables

# Function to ask questions about the extracted data
def ask_question(question, data):
    response = client.chat.completions.create(
        model="meta-llama/Llama-3-8b-chat-hf",
        messages=[
            {"role": "system", "content": "You are a financial analyst. Answer questions based on the provided financial data."},
            {"role": "user", "content": f"Financial data: {data}\n\n{question}"},
        ]
    )
    return response.choices[0].message.content

# Function to extract financial data from text
def extract_financial_data(text):
    patterns = {
        'Revenue': re.compile(r'Revenue Analysis:[\s\S]*?Year 1: \$([\d,]+)[\s\S]*?Year 2: \$([\d,]+)[\s\S]*?Year 3: \$([\d,]+)'),
        'COGS': re.compile(r'COGS Analysis:[\s\S]*?Year 1: \$([\d,]+)[\s\S]*?Year 2: \$([\d,]+)[\s\S]*?Year 3: \$([\d,]+)'),
        'Gross Profit': re.compile(r'Gross Profit Analysis:[\s\S]*?Year 1: \$([\d,]+)[\s\S]*?Year 2: \$([\d,]+)[\s\S]*?Year 3: \$([\d,]+)'),
        'Operating Expenses': re.compile(r'Operating Expenses Analysis:[\s\S]*?Year 1: \$([\d,]+)[\s\S]*?Year 2: \$([\d,]+)[\s\S]*?Year 3: \$([\d,]+)'),
        'Net Income': re.compile(r'Net Income Analysis:[\s\S]*?Year 1: \$([\d,]+)[\s\S]*?Year 2: -?\$([\d,]+)[\s\S]*?Year 3: \$([\d,]+)')
    }
    data = {}
    for key, pattern in patterns.items():
        match = pattern.search(text)
        if match:
            data[key] = [int(m.replace(',', '')) for m in match.groups()]
    return data

# Streamlit interface
st.title("Financial Report Analysis Assistant")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# File upload
uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")

if uploaded_file is not None:
    # Save uploaded file to a temporary location
    temp_file_path = f"/tmp/{uploaded_file.name}"
    with open(temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Extract tables from the uploaded PDF
    tables = extract_tables_from_pdf(temp_file_path)

    # Assuming the financial data is in the first table
    if tables:
        data = tables[0]
        data_dict = data.to_dict(orient='list')
    else:
        st.error("No tables found in the PDF")
        st.stop()

# React to user input
if prompt := st.chat_input("Ask a question about the financial data:"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Check if PDF data is available
    if 'data_dict' in locals():
        answer = ask_question(prompt, data_dict)
        st.session_state.messages.append({"role": "assistant", "content": answer})

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            st.markdown(answer)

        # Extract data for plotting
        financial_data = extract_financial_data(answer)

        if financial_data:  # Check if any data was extracted
            # Define years
            years = ['Year 1', 'Year 2', 'Year 3']

            # Plot each financial metric
            fig, axs = plt.subplots(3, 2, figsize=(15, 15))
            for i, (metric, values) in enumerate(financial_data.items()):
                ax = axs[i // 2, i % 2]
                ax.plot(years, values, marker='o')
                ax.set_title(metric)
                ax.set_xlabel('Year')
                ax.set_ylabel('Amount ($)')
                ax.grid(True)

            # Remove the empty subplot if necessary
            if len(financial_data) % 2 != 0:
                fig.delaxes(axs[-1, -1])

            # Adjust layout
            plt.tight_layout()
            st.pyplot(fig)
        else:
            st.warning("No valid financial data found for plotting.")
    else:
        st.warning("Please upload a PDF file to analyze.")
