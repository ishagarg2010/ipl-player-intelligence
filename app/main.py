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
        st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL"),
        st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
    )
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return supabase, openai_client

supabase, openai_client = init_clients()

# Title
st.title("🏏 IPL Player Intelligence Platform")
st.caption("Ask questions about IPL players in plain English")

# Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["AI Analyst", "Auction Value Score", "Bowler Dashboard", "Batsman Dashboard"])

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
            batting_result = supabase.table('batsman_summary')\
                .select("*")\
                .order('total_runs', desc=True)\
                .limit(20)\
                .execute()
            bowling_result = supabase.table('bowler_summary')\
                .select("*")\
                .order('wickets', desc=True)\
                .limit(20)\
                .execute()
            batting_df = pd.DataFrame(batting_result.data)
            bowlers_df = pd.DataFrame(bowling_result.data)

            
            # Get AI insight
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert IPL cricket analyst. 
                        Answer questions using the data provided. 
                        Be specific with numbers. Keep answers under 150 words.
                        You have access to both batting and bowling data."""
                    },
                    {
                        "role": "user",
                        "content": f"""BATTING DATA (top 20 by runs):{batting_df.to_string(index=False)}
                                        BOWLING DATA (top 20 by wickets):{bowlers_df.to_string(index=False)}
                                        Question: {question}"""
                    }
                ]
    )
    
        insight = response.choices[0].message.content
        
        # Display results
        st.markdown("### 🤖 AI Insight")
        st.info(insight)
        
        st.markdown("### 📊 Supporting Data")
        tab1, tab2 = st.tabs(["Batting", "Bowling"])
        with tab1:
            st.dataframe(batting_df, use_container_width=True)
        with tab2:
            st.dataframe(bowlers_df, use_container_width=True)

elif page == "Batsman Dashboard":
    st.header("Batsman Performance Dashboard")
    
    # Load data
    @st.cache_data
    def load_players():
        result = supabase.table('batsman_summary')\
            .select("*")\
            .order('total_runs', desc=True)\
            .limit(50)\
            .execute()
        return pd.DataFrame(result.data)
    
    batting_df = load_players()
    
    ## Debug line — remove later
    #st.write(f"Rows loaded: {len(batting_df)}")

    # Top run scorers chart
    st.subheader("Top 10 Run Scorers")
    top10 = batting_df.head(10)
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
        batting_df,
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
    st.dataframe(batting_df, use_container_width=True)

elif page == "Auction Value Score":
    st.header("🏆 IPL Player ROI Index")
    st.caption("A data-driven score combining runs, strike rate and consistency — who is worth their auction price?")
    
    from auction_score import calculate_auction_score
    
    # Load all players
    @st.cache_data
    def load_all_players():
        _supabase = create_client(
            st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL"),
            st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
        )
        result = _supabase.table('batsman_summary')\
            .select("*")\
            .execute()
        return pd.DataFrame(result.data)
    
    batting_df = load_all_players()
    scored_df = calculate_auction_score(batting_df)
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Players", len(scored_df))
    with col2:
        st.metric("Elite Players", len(scored_df[scored_df['tier'] == '🔥 Elite']))
    with col3:
        st.metric("Top ROI Score", scored_df['roi_index'].max())
    with col4:
        st.metric("Avg Strike Rate", round(scored_df['strike_rate'].mean(), 2))
    
    # Top 10 by ROI
    st.subheader("Top 10 by ROI Index")
    top10 = scored_df.head(10)
    
    import plotly.express as px
    fig = px.bar(
        top10,
        x='player',
        y='roi_index',
        color='tier',
        color_discrete_map={
            '🔥 Elite': '#FF4B4B',
            '⭐ Premium': '#FFA500',
            '✅ Value': '#00CC44',
            '⚠️ Risky': '#888888'
        },
        title='Top 10 Players by IPL ROI Index'
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)
    
    # Player lookup
    st.subheader("Look up any player")
    player_name = st.text_input("Type a player name:", placeholder="e.g. Virat Kohli")
    
    if player_name:
        match = scored_df[scored_df['player'].str.contains(player_name, case=False, na=False)]
        if len(match) > 0:
            p = match.iloc[0]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("ROI Index", p['roi_index'])
            with col2:
                st.metric("Tier", p['tier'])
            with col3:
                st.metric("Total Runs", int(p['total_runs']))
            with col4:
                st.metric("Strike Rate", p['strike_rate'])
        else:
            st.warning(f"Player '{player_name}' not found. Try a different spelling.")
    
    # Full table
    st.subheader("All Players")
    st.dataframe(
        scored_df[['player', 'total_runs', 'strike_rate', 'roi_index', 'tier']]\
            .reset_index(drop=True),
        use_container_width=True
    )

elif page == "Bowler Dashboard":
    st.header("🎯 Bowler Analysis")
    st.caption("Economy, wickets, and bowling efficiency across IPL seasons")
    
    # Load bowler data
    @st.cache_data
    def load_bowlers():
        _supabase = create_client(
            st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL"),
            st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")
        )
        result = _supabase.table('bowler_summary')\
            .select("*")\
            .execute()
        return pd.DataFrame(result.data)
    
    bowlers_df = load_bowlers()
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Bowlers", len(bowlers_df))
    with col2:
        best_economy = bowlers_df.nsmallest(1, 'economy').iloc[0]
        st.metric("Best Economy", f"{best_economy['economy']}", best_economy['bowler'])
    with col3:
        most_wickets = bowlers_df.nlargest(1, 'wickets').iloc[0]
        st.metric("Most Wickets", int(most_wickets['wickets']), most_wickets['bowler'])
    with col4:
        st.metric("Avg Economy", round(bowlers_df['economy'].mean(), 2))
    
    # Top wicket takers
    st.subheader("Top 10 Wicket Takers")
    top_wickets = bowlers_df.nlargest(10, 'wickets')
    fig1 = px.bar(
        top_wickets,
        x='bowler',
        y='wickets',
        color='economy',
        color_continuous_scale='RdYlGn_r',
        title='Top 10 Wicket Takers (colour = economy rate)',
        labels={'economy': 'Economy'}
    )
    fig1.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig1, use_container_width=True)
    
    # Economy vs wickets scatter
    st.subheader("Economy vs Wickets")
    st.caption("Best bowlers are bottom right — low economy, high wickets")
    top50 = bowlers_df.nlargest(50, 'wickets')
    fig2 = px.scatter(
        top50,
        x='economy',
        y='wickets',
        hover_name='bowler',
        color='bowling_avg',
        size='overs_bowled',
        color_continuous_scale='RdYlGn_r',
        title='Economy vs Wickets — Top 50 Bowlers'
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    # Best death bowlers
    st.subheader("Best Economy Bowlers (min 50 overs)")
    best_economy = bowlers_df[bowlers_df['overs_bowled'] >= 50]\
        .nsmallest(10, 'economy')
    fig3 = px.bar(
        best_economy,
        x='bowler',
        y='economy',
        color='wickets',
        color_continuous_scale='Blues',
        title='Best Economy Rate (minimum 50 overs bowled)'
    )
    fig3.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig3, use_container_width=True)
    
    # Bowler lookup
    st.subheader("Look up any bowler")
    bowler_name = st.text_input(
        "Type a bowler name:", 
        placeholder="e.g. Jasprit Bumrah"
    )
    
    if bowler_name:
        match = bowlers_df[bowlers_df['bowler'].str.contains(
            bowler_name, case=False, na=False
        )]
        if len(match) > 0:
            p = match.iloc[0]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Wickets", int(p['wickets']))
            with col2:
                st.metric("Economy", p['economy'])
            with col3:
                st.metric("Bowling Avg", round(p['bowling_avg'], 2))
            with col4:
                st.metric("Overs Bowled", p['overs_bowled'])
        else:
            st.warning(f"Bowler '{bowler_name}' not found. Try a different spelling.")
    
    # Full table
    st.subheader("All Bowlers")
    st.dataframe(
        bowlers_df[['bowler', 'wickets', 'economy', 
                    'bowling_avg', 'bowling_sr', 'overs_bowled']]\
            .sort_values('wickets', ascending=False)\
            .reset_index(drop=True),
        use_container_width=True
    )