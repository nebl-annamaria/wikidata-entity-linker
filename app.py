import streamlit as st
from pypdf import PdfReader
import requests
import pandas as pd
import json
from keybert import KeyBERT
from collections import Counter

# --- Load model ---
kw_model = KeyBERT()

# --- Extract text from PDF in chunks ---
def extract_text_from_pdf(file, chunk_size=500):
    reader = PdfReader(file)
    text = " ".join(page.extract_text() or "" for page in reader.pages)
    words = text.split()
    chunks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
    return chunks

# --- Keyword extraction with KeyBERT ---
def extract_entities_keybert(text, top_n=5):
    keywords = kw_model.extract_keywords(
        text, 
        keyphrase_ngram_range=(1, 3),
        top_n=top_n)
    return [kw for kw, _ in keywords]

# --- Wikidata search ---
def search_wikidata(query, limit=1):
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "search": query,
        "language": "en",
        "format": "json",
        "limit": limit
    }
    headers = {"User-Agent": "thesis-demo/0.1 (your_email@example.com)"}
    
    r = requests.get(url, params=params, headers=headers)
    if r.status_code != 200:
        print("Error:", r.status_code, r.text[:500])
        return None

    try:
        data = r.json()
    except Exception:
        print("Non-JSON response:", r.text[:500])
        return None

    if data.get("search"):
        return data["search"][0]["id"], data["search"][0]["label"]
    return None

# --- Full statement query for a given QID ---
def get_all_statements(qid, lang="en"):
    url = "https://query.wikidata.org/sparql"
    query = f"""
    SELECT
      ?property
      ?propertyLabel
      ?statementValue
      ?statementValueLabel
      ?qualifierProperty
      ?qualifierPropertyLabel
      ?qualifierValue
      ?qualifierValueLabel
      ?unitOfMeasure
      ?unitOfMeasureLabel
      ?statementRankLabel
    WHERE {{
      VALUES ?item {{wd:{qid}}}
      ?item ?propertyPredicate ?statement .
      ?statement ?statementPropertyPredicate ?statementValue .
      ?property wikibase:claim ?propertyPredicate .
      ?property wikibase:statementProperty ?statementPropertyPredicate .
      ?statement wikibase:rank ?statementRank .
      BIND(IF(?statementRank = wikibase:NormalRank, "Normal",
        IF(?statementRank = wikibase:PreferredRank, "Preferred",
        IF(?statementRank = wikibase:DeprecatedRank, "Deprecated", "Unknown"))) AS ?statementRankLabel)
      OPTIONAL {{ ?statement ?qualifierPredicate ?qualifierValue .
                 ?qualifierProperty wikibase:qualifier ?qualifierPredicate . }}
      OPTIONAL {{ ?statement ?statementValueNodePredicate ?valueNode .
                 ?valueNode wikibase:quantityUnit ?unitOfMeasure . }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "{lang}, en". }}
    }}
    ORDER BY ?property ?statementValue ?qualifierProperty ?qualifierValue
    """
    r = requests.get(url, params={"query": query, "format": "json"})
    data = r.json()
    rows = []
    for b in data["results"]["bindings"]:
        prop_uri = b.get("property", {}).get("value", "")
        prop_code = prop_uri.split("/")[-1] if prop_uri else None
        rows.append({
            "property_id": prop_code,
            "property": b.get("propertyLabel", {}).get("value"),
            "value": b.get("statementValueLabel", {}).get("value", b.get("statementValue", {}).get("value")),
            "qualifier": b.get("qualifierPropertyLabel", {}).get("value"),
            "qualifier_value": b.get("qualifierValueLabel", {}).get("value"),
            "unit": b.get("unitOfMeasureLabel", {}).get("value"),
            "rank": b.get("statementRankLabel", {}).get("value")
        })
    return rows


# --- Streamlit UI ---
st.title("📑 PDF Keyword → Wikidata Mapper")

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

# --- Session state ---
if "selected_qid" not in st.session_state:
    st.session_state.selected_qid = None
if "results" not in st.session_state:
    st.session_state.results = []

# --- Helpers ---
def select_qid(qid):
    st.session_state.selected_qid = qid

def go_back():
    st.session_state.selected_qid = None


# --- Process only when the button is clicked ---
if uploaded_file and st.button("Start Processing"):
    st.info("⏳ Processing...")

    chunks = extract_text_from_pdf(uploaded_file)
    st.write(f"👉 {len(chunks)} text chunks were extracted from the PDF.")

    # Collect keywords
    all_entities = []
    for chunk in chunks:
        all_entities.extend(extract_entities_keybert(chunk, top_n=5))

    if all_entities:
        counts = Counter(all_entities)

        st.success(f"🎉 Found {len(all_entities)} keywords, "
                   f"{len(counts)} unique items!")

        results = []
        progress_text = "🔎 Running Wikidata lookups..."
        progress_bar = st.progress(0, text=progress_text)

        for i, (ent, count) in enumerate(counts.items()):
            wd_result = search_wikidata(ent)
            if wd_result:
                qid, wd_label = wd_result
                results.append({
                    "keyword": ent,
                    "count": count,
                    "wikidata_label": wd_label,
                    "qid": qid
                })
            progress_bar.progress((i + 1) / len(counts), text=progress_text)

        progress_bar.empty()

        if results:
            st.session_state.results = results
            st.session_state.selected_qid = None  # reset selection
        else:
            st.warning("No Wikidata matches found.")
    else:
        st.warning("No keywords were found in the document.")

# --- Show Wikidata matches if results exist ---
if st.session_state.results and not st.session_state.selected_qid:
    df = pd.DataFrame(st.session_state.results)
    st.write("### 🔗 Wikidata matches (Keywords with QIDs)")

    # Header row
    header_cols = st.columns([3, 2, 3, 2])
    header_cols[0].markdown("**Keyword**")
    header_cols[1].markdown("**QID**")
    header_cols[2].markdown("**Wikidata Label**")
    header_cols[3].markdown("**Actions**")

    # Data rows
    for i, row in df.iterrows():
        cols = st.columns([3, 2, 3, 2])
        cols[0].write(row["keyword"])
        # QID as clickable link
        qid_url = f"https://www.wikidata.org/wiki/{row['qid']}"
        cols[1].markdown(f"[{row['qid']}]({qid_url})")
        cols[2].write(row["wikidata_label"])
        cols[3].button(
            "Query props",
            key=f"props_{i}",
            on_click=select_qid,
            args=(row["qid"],)
        )

# --- Show full property query if a QID is selected ---
if st.session_state.selected_qid:
    qid = st.session_state.selected_qid
    st.write(f"### 🔍 Full property query for {qid}")

    st.button("⬅️ Back to entity table", on_click=go_back)

    props = get_all_statements(qid)
    if props:
        st.write("#### Property relations with details")
        prop_df = pd.DataFrame(props)
        st.dataframe(prop_df, use_container_width=True)
    else:
        st.warning("No properties found for this entity.")
