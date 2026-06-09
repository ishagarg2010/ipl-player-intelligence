import streamlit as st
import os
from supabase import create_client
from openai import OpenAI
import pandas as pd
import plotly.express as px

# Page config
st.set_page_config(
    page_title="IPL Player Intelligence Platform",
    page_icon="🏏",
    layout="wide"
)

# Initialize clients
@st.cache_resource
def init_clients():
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return supabase, openai_client

supabase, openai_client = init_clients()

# Title
st.title("🏏 IPL Player Intelligence Platform")
st.caption("Ask questions about IPL players in plain English")

# Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["AI Analyst", "Player Dashboard"])

if page == "AI Analyst":
    st.header("Ask the AI Analyst")
    
    # Example questions
    st.markdown("**Try asking:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Top 10 run scorers"):
            st.session_state.question = "Who are the top 10 run scorers in IPL history?"
    with col2:
        if st.button("Best strike rates"):
            st.session_state.question = "Who has the best strike rate with over 1000 balls faced?"
    with col3:
        if st.button("Most Player of Match"):
            st.session_state.question = "Who has won player of the match most times?"

    # Question input
    question = st.text_input(
        "Your question:",
        value=st.session_state.get("question", ""),
        placeholder="e.g. Who is the most consistent batsman across all seasons?"
    )

    if question:
        with st.spinner("Analysing..."):
            # Fetch relevant data
            result = supabase.table('player_summary')\
                .select("*")\
                .order('total_runs', desc=True)\
                .limit(20)\
                .execute()
            
            players_df = pd.DataFrame(result.data)
            
            # Get AI insight
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert IPL cricket analyst. 
                        Answer questions using the data provided. 
                        Be specific with numbers. Keep answers under 150 words."""
                    },
                    {
                        "role": "user",
                        "content": f"""Player data:{players_df.to_string(index=False)}

        Question: {question}"""
                    }
                ]
    )
    
        insight = response.choices[0].message.content
        
        # Display results
        st.markdown("### 🤖 AI Insight")
        st.info(insight)
        
        st.markdown("### 📊 Supporting Data")
        st.dataframe(players_df, use_container_width=True)

elif page == "Player Dashboard":
    st.header("Player Performance Dashboard")
    
    # Load data
    @st.cache_data
    def load_players():
        result = supabase.table('player_summary')\
            .select("*")\
            .order('total_runs', desc=True)\
            .limit(50)\
            .execute()
        return pd.DataFrame(result.data)
    
    players_df = load_players()
    
    ## Debug line — remove later
    #st.write(f"Rows loaded: {len(players_df)}")

    # Top run scorers chart
    st.subheader("Top 10 Run Scorers")
    top10 = players_df.head(10)
    fig1 = px.bar(
        top10,
        x='player',
        y='total_runs',
        color='total_runs',
        color_continuous_scale='Reds',
        title='Top 10 IPL Run Scorers'
    )
    fig1.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig1, use_container_width=True)
    
    # Strike rate vs runs scatter
    st.subheader("Strike Rate vs Total Runs")
    fig2 = px.scatter(
        players_df,
        x='total_runs',
        y='strike_rate',
        hover_name='player',
        color='strike_rate',
        color_continuous_scale='Viridis',
        title='Strike Rate vs Total Runs (hover for player name)'
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    # Raw data table
    st.subheader("Full Player Stats")
    st.dataframe(players_df, use_container_width=True)