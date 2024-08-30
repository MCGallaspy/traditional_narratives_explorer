import pandas as pd
import streamlit as st
import editdistance
import re
import urllib
import unicodedata

st.set_page_config(layout="wide")

st.title("Traditional Narratives Search Tool")

@st.cache_data
def get_lines():
    with open("words_2012.txt", "r", encoding="utf8") as f:
        lines = f.readlines()
    df = pd.DataFrame(data=lines)
    df = df.rename(columns={0: "Line"})
    df.index.name = "Line number"
    df.Line = df.Line.apply(lambda x: unicodedata.normalize("NFC", x))
    return df


df = get_lines()


@st.cache_data
def search(search_mode, match_mode, search_term, df):
    """ Search a dataframe in various modes for a given search term.
    Cached to hopefully improve online performance.
    """
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
    
    return hits


with st.sidebar:
    st.header("Search parameters")
    
    mode_options = (
        "contains",
        "starts with",
        "edit distance",
        "python regex",
    )
    
    try:
        assert "mode" not in st.session_state
        qp_mode = urllib.parse.unquote_plus(st.query_params["mode"])
        mode_index = mode_options.index(qp_mode)
        search_mode = st.selectbox(
            "Search mode",
            mode_options,
            index=mode_index,
            key="mode",
        )
    except (ValueError, KeyError, AssertionError):
        search_mode = st.selectbox(
            "Search mode",
            mode_options,
            key="mode",
        )
        if search_mode and "mode" in st.query_params:
            st.query_params["mode"] = urllib.parse.quote_plus(search_mode)
        
    try:
        assert "term" not in st.session_state
        qp_term = urllib.parse.unquote_plus(st.query_params["term"])
        search_term = st.text_input(
            "Search term",
            qp_term,
            placeholder="e.g. he.eats",
            key="term",
        )
    except (KeyError, AssertionError):
        search_term = st.text_input(
            "Search term",
            st.session_state.get("term", ""),
            placeholder="e.g. he.eats",
            key="term",
        )
        if search_term and "term" in st.query_params:
            st.query_params["term"] = urllib.parse.quote_plus(search_term)
    
    st.markdown("*You can copy the following special characters into your clipboard "
                "by clicking on them.*")
    special_chars = [
        ["š", "ž", "ʔ"],
        [None, "á", "à"],
        ["ą", "ą́", "ą̀"],
        [None, "é", "è"],
        ["ę", "ę́", "ę̀"],
        [None, "í", "ì"],
        [None, "ó", "ò"],
        ["ǫ", "ǫ́", "ǫ̀"],
        [None, "ú", "ù"],
    ]
    n = 4
    for charset in special_chars:
        cols = st.columns(n)
        assert len(charset) <= n
        for col, char in zip(cols, charset):
            if char is not None:
                col.code(char)
    
    st.subheader("Advanced options")
    
    try:
        assert "context" not in st.session_state
        qp_context = urllib.parse.unquote_plus(st.query_params["context"])
        qp_context = int(qp_context)
        context_size = st.number_input(
            "Context size", min_value=0, value=qp_context, max_value=100, step=1,
            key="context",
        )
    except (KeyError, ValueError, AssertionError):
        context_size = st.number_input(
            "Context size", min_value=0, value=3, max_value=100, step=1,
            key="context",
        )
        if context_size and "context" in st.query_params:
            st.query_params["context"] = context_size

    
    try:
        assert "ndisp" not in st.session_state
        qp_ndisp = urllib.parse.unquote_plus(st.query_params["ndisp"])
        qp_ndisp = int(qp_ndisp)
        num_display_results = st.number_input(
            "Max number of search results to display", min_value=1, value=qp_ndisp, step=1,
            key="ndisp",
        )
    except (KeyError, ValueError, AssertionError):
        num_display_results = st.number_input(
            "Max number of search results to display", min_value=1, value=100, step=1,
            key="ndisp",
        )
        if num_display_results and "ndisp" in st.query_params:
            st.query_params["ndisp"] = num_display_results
    
    match_mode_options = (
        "match individual words",
        "match whole line",
    )
    
    try:
        assert "match_mode" not in st.session_state
        qp_match_mode = urllib.parse.unquote_plus(st.query_params["match_mode"])
        match_mode_index = match_mode_options.index(qp_match_mode)
        match_mode = st.selectbox(
            "search modifiers",
            match_mode_options,
            index=match_mode_index,
            key="match_mode",
        )
    except (ValueError, KeyError, AssertionError):
        match_mode = st.selectbox(
            "search modifiers",
            match_mode_options,
            key="match_mode",
        )
        if match_mode and "match_mode" in st.query_params:
            st.query_params["match_mode"] = urllib.parse.quote_plus(match_mode)
    
    st.markdown('---')
    
    try:
        assert "normalize" not in st.session_state
        qp_normalize = urllib.parse.unquote_plus(st.query_params["normalize"])
        qp_normalize = True if qp_normalize == "True" else False
        normalize = st.toggle(
            "Normalize UNICODE characters in search term?",
            value=qp_normalize,
            key="normalize",
        )
    except (KeyError, AssertionError):
        normalize = st.toggle(
            "Normalize UNICODE characters in search term?",
            value=True,
            key="normalize",
        )
        if "normalize" in st.query_params:
            st.query_params["normalize"] = normalize
    
    st.markdown("When enabled, this normalizes the search term to UNICODE normal form c (NFC). "
                "For example the two character UNICODE sequence `ǫ` (which is really `o` and "
                "followed by a combining ogonek character `̨`) would be replaced in the search term "
                "with a distinct but visually identical character `ǫ`.")


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
    query_str += f"&normalize={urllib.parse.quote_plus(str(normalize))}"
    st.markdown(f"[Permalink to search results](?{query_str})")
    
    if normalize:
        search_term = unicodedata.normalize("NFC", search_term)
    
    hits = search(search_mode, match_mode, search_term, df)
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