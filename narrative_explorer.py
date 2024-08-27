import pandas as pd
import streamlit as st
import editdistance
import re
import urllib

st.set_page_config(layout="wide")

st.title("Traditional Narratives Search Tool")

@st.cache_data
def get_lines():
    with open("words_2012.txt", "r", encoding="utf8") as f:
        lines = f.readlines()
    df = pd.DataFrame(data=lines)
    df = df.rename(columns={0: "Line"})
    df.index.name = "Line number"
    return df

with st.sidebar:
    st.header("Search parameters")
    
    mode_options = (
        "contains",
        "starts with",
        "edit distance",
        "python regex",
    )
    
    try:
        qp_mode = urllib.parse.unquote_plus(st.query_params["mode"])
        mode_index = mode_options.index(qp_mode)
    except (ValueError, KeyError):
        mode_index = 0
    
    search_mode = st.selectbox(
        "Search mode",
        mode_options,
        index=mode_index,
    )

    try:
        qp_term = urllib.parse.unquote_plus(st.query_params["term"])
    except KeyError:
        qp_term = ""

    search_term = st.text_input(
        "Search term",
        qp_term,
        placeholder="e.g. he.eats",
    )
    
    try:
        qp_context = urllib.parse.unquote_plus(st.query_params["context"])
        qp_context = int(qp_context)
    except (KeyError, ValueError):
        qp_context = 3
    
    context_size = st.number_input(
        "Context size", min_value=0, value=qp_context, max_value=100, step=1
    )
    
    try:
        qp_ndisp = urllib.parse.unquote_plus(st.query_params["ndisp"])
        qp_ndisp = int(qp_ndisp)
    except (KeyError, ValueError):
        qp_ndisp = 100
        
    num_display_results = st.number_input(
        "Max number of search results to display", min_value=1, value=qp_ndisp, step=1
    )
    
    st.subheader("Advanced options")
    
    match_mode_options = (
        "match individual words",
        "match whole line",
    )
    
    try:
        qp_match_mode = urllib.parse.unquote_plus(st.query_params["match_mode"])
        match_mode_index = match_mode_options.index(qp_match_mode)
    except (ValueError, KeyError):
        match_mode_index = 0
    
    match_mode = st.selectbox(
        "search modifiers",
        match_mode_options,
        index=match_mode_index,
    )

df = get_lines()

def highlight_line(line, term):
    term.replace(".", "\\.")
    line = line.strip()
    line = r'<span class="result">' + line + r'</span>'
    try:
        start = line.index(term)
        end = start + len(term)
        line = line[:start] + f'<span class="term">{term}</span>' + line[end:]
    except ValueError:
        # Search term not found by list.index
        pass
    return line

st.markdown("""
<style>
.term {color: red;}
.result {font-weight: bold;}
</style>
""", unsafe_allow_html=True)

if search_term:
    
    query_str = ""
    query_str += f"mode={urllib.parse.quote_plus(search_mode)}"
    query_str += f"&term={urllib.parse.quote_plus(search_term)}"
    query_str += f"&context={urllib.parse.quote_plus(str(context_size))}"
    query_str += f"&ndisp={urllib.parse.quote_plus(str(num_display_results))}"
    query_str += f"&match_mode={urllib.parse.quote_plus(match_mode)}"
    st.markdown(f"[Permalink to search results](?{query_str})")
    st.query_params.from_dict({
        "mode": search_mode,
        "term": search_term,
        "context": context_size,
        "ndisp": num_display_results,
        "match_mode": match_mode,
    })

    if search_mode == "starts with":
        hits = df[df.Line.str.startswith(search_term)].index
        if match_mode == "match whole line":
            hits = df[df.Line.str.startswith(search_term.replace(".", r"\."))].index
        elif match_mode == "match individual words":
            mask = df.Line.apply(lambda x: any(word.startswith(search_term) for word in x.split(" ")))
            hits = df[mask].index
    elif search_mode == "contains":
        if match_mode == "match whole line":
            hits = df[df.Line.str.contains(search_term.replace(".", r"\."))].index
        elif match_mode == "match individual words":
            mask = df.Line.apply(lambda x: any(search_term in word for word in x.split()))
            hits = df[mask].index
    elif search_mode == "edit distance":
        if match_mode == "match whole line":
            df['edit_distance'] = df.Line.apply(lambda x: editdistance.eval(x, search_term))
            relevance = df.sort_values(by='edit_distance')
            hits = relevance.index
        elif match_mode == "match individual words":
            df['edit_distance'] = df.Line.apply(
                lambda x: min(editdistance.eval(word, search_term) for word in x.split()))
            relevance = df.sort_values(by='edit_distance')
            hits = relevance.index
    elif search_mode == "python regex":
        if match_mode == "match whole line":
            pattern = re.compile(search_term)
            mask = df.Line.apply(lambda x: bool(pattern.match(x)))
        elif match_mode == "match individual words":
            pattern = re.compile(search_term)
            mask = df.Line.apply(lambda x: any(bool(pattern.match(word)) for word in x.split()))
        hits = df[mask].index
    
    nresults = len(hits)
    if nresults == 0:
        st.markdown(f"No results for search term **{search_term}**")
    hits = hits[:num_display_results]
    df.loc[hits, "Line"] = df.loc[hits, "Line"].apply(
            lambda line: highlight_line(line, search_term))
    ranges = [(hit - context_size, hit + context_size) for hit in hits]
    for i, (start, end) in enumerate(ranges):
        st.subheader(f"Search result {i+1} of {nresults}")
        st.markdown(df.loc[start:end].to_markdown(), unsafe_allow_html=True)
    
else:
    st.dataframe(df, use_container_width=True)
    


