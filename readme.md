# PDF Keyword → Wikidata Mapper

This project extracts keywords from PDF documents using **KeyBERT**,  
maps them to **Wikidata entities**, and allows you to query the full  
property relations of each entity through a Streamlit interface.

## ✨ Features

\- Upload a PDF file (example provided)
\- Extract keywords with **KeyBERT**  
\- Map keywords to Wikidata QIDs  
\- Display results in a table with clickable links to Wikidata  
\- Query full property relations (SPARQL) for each entity

## 🚀 Setup & Run

Clone the repository and run the following commands:

```
python3 -m venv .venv
source ./.venv/bin/activate
pip3 install -r requirements.txt
streamlit run app.py
```

## 📖 Usage

1\. Start the app with:

```
streamlit run app.py
```

2\. Upload a PDF file.  
3\. Click **Start Processing** to extract keywords and map them.  
4\. Use the **Query props** button to view all Wikidata properties of an entity.
