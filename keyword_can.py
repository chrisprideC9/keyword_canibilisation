import streamlit as st
import pandas as pd
import numpy as np
import os
from io import StringIO, BytesIO
import plotly.express as px

def main():
    # Set the page configuration
    st.set_page_config(page_title="📊 CSV Cleaner and Analyzer", layout="wide")

    # App Title and Description
    st.title("📊 CSV Cleaner and Analyzer")
    st.write("""
    Upload a CSV file and specify the branded search terms you want to filter out. The app will process the data by:
    - Removing specified branded search terms
    - Filtering based on impressions
    - Calculating relevant metrics
    - Sorting by Total Keyword Impressions
    - Visualizing the top 10 keywords being cannibalized
    - Providing a cleaned CSV for download
    """)

    # Create a form for user inputs
    with st.form(key='filter_form'):
        st.header("🔧 Configuration")
        
        # 1. Input for Branded Search Terms
        query_to_remove = st.text_input(
            "📝 Enter the branded search terms to remove (separated by commas):",
            placeholder="e.g., BrandA, BrandB, BrandC"
        )
        
        # 2. File Upload
        uploaded_file = st.file_uploader("📂 Upload Your CSV File", type=["csv"])
        
        # 3. Submit Button
        submit_button = st.form_submit_button(label='✅ Submit and Clean Data')

    # Process the data after form submission
    if submit_button:
        if uploaded_file is not None:
            try:
                # Start spinner
                with st.spinner("⏳ Processing your data..."):
                    # Read the CSV file
                    df = pd.read_csv(uploaded_file)
                    
                    # Validate Required Columns
                    required_columns = ['Impressions', 'Query', 'Landing Page']
                    missing_columns = [col for col in required_columns if col not in df.columns]
                    if missing_columns:
                        st.error(f"❌ Missing required columns: {', '.join(missing_columns)}")
                        st.stop()
                    
                    # Data Cleaning
                    # Convert 'Impressions' to numeric, coerce errors, and drop rows with non-numeric 'Impressions'
                    df['Impressions'] = pd.to_numeric(df['Impressions'], errors='coerce')
                    initial_row_count = df.shape[0]
                    df = df.dropna(subset=['Impressions'])
                    df['Impressions'] = df['Impressions'].astype(int)
                    dropped_non_numeric = initial_row_count - df.shape[0]
                    
                    # Sort the DataFrame by 'Impressions' in descending order
                    df = df.sort_values(by='Impressions', ascending=False)
                    
                    # Process Branded Search Terms
                    if query_to_remove:
                        queries_to_remove = [query.strip() for query in query_to_remove.split(',') if query.strip()]
                        if queries_to_remove:
                            df = df[~df['Query'].isin(queries_to_remove)]
                    else:
                        queries_to_remove = []
                    
                    # Drop rows with 'Impressions' less than 10
                    before_filter = df.shape[0]
                    df = df[df['Impressions'] >= 10]
                    dropped_low_impressions = before_filter - df.shape[0]
                    
                    # Calculate total impressions for each query
                    total_impressions = df.groupby('Query')['Impressions'].sum().reset_index()
                    total_impressions.columns = ['Query', 'Total Keyword Impressions']
                    df = pd.merge(df, total_impressions, on='Query', how='left')
                    
                    # Calculate the percentage of impressions for each URL
                    df['Percentage of Impressions'] = (df['Impressions'] / df['Total Keyword Impressions']) * 100
                    
                    # Drop duplicates based on 'Query' and 'Landing Page'
                    df = df.drop_duplicates(subset=['Query', 'Landing Page'])
                    
                    # Filter based on 'Percentage of Impressions'
                    df = df[(df['Percentage of Impressions'] > 10) & (df['Percentage of Impressions'] < 75)]
                    
                    # Reorder columns
                    df = df[['Landing Page', 'Query', 'Impressions', 'Total Keyword Impressions', 'Percentage of Impressions']]
                    
                    # Sort alphabetically by 'Query'
                    df = df.sort_values(by='Query')
                    
                    # Round up 'Percentage of Impressions' and add a percent sign
                    df['Percentage of Impressions'] = np.ceil(df['Percentage of Impressions']).astype(int).astype(str) + '%'
                    
                    # Final Sorting by 'Total Keyword Impressions' Descending
                    df = df.sort_values(by='Total Keyword Impressions', ascending=False)
                    
                    # Identify Top 10 Cannibalized Keywords
                    # Define cannibalization as Queries with multiple Landing Pages
                    cannibalization = df.groupby('Query').agg({
                        'Landing Page': 'nunique',
                        'Total Keyword Impressions': 'first'  # Since it's sorted, first will have the total
                    }).reset_index()
                    cannibalization = cannibalization[cannibalization['Landing Page'] > 1]
                    top_cannibalized = cannibalization.sort_values(by='Total Keyword Impressions', ascending=False).head(10)
                    
                # Success message
                st.success("✅ Data processing complete!")

                # Display Final Cleaned Data
                st.subheader("📈 Final Cleaned Data")
                st.dataframe(df)

                # Provide Download Option
                def convert_df_to_csv(df):
                    return df.to_csv(index=False).encode('utf-8')

                csv = convert_df_to_csv(df)

                st.download_button(
                    label="📥 Download Cleaned CSV",
                    data=csv,
                    file_name='cleaned_data.csv',
                    mime='text/csv',
                )

                # Visualization: Top 10 Cannibalized Keywords
                if not top_cannibalized.empty:
                    st.subheader("📊 Top 10 Cannibalized Keywords")
                    fig = px.bar(
                        top_cannibalized,
                        x='Query',
                        y='Total Keyword Impressions',
                        color='Landing Page',
                        labels={
                            'Query': 'Keyword',
                            'Total Keyword Impressions': 'Total Impressions',
                            'Landing Page': 'Number of Landing Pages'
                        },
                        title='Top 10 Keywords Being Cannibalized',
                        hover_data=['Landing Page']
                    )
                    fig.update_layout(xaxis_title='Keyword', yaxis_title='Total Impressions')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("ℹ️ No cannibalized keywords found in the data.")

            except pd.errors.EmptyDataError:
                st.error("❌ Error: The uploaded file is empty.")
            except pd.errors.ParserError:
                st.error("❌ Error: The uploaded file could not be parsed.")
            except Exception as e:
                st.error(f"❌ An unexpected error occurred: {e}")
        else:
            st.error("❌ Please upload a CSV file before submitting.")

    else:
        st.info("📌 Please fill out the configuration and upload your CSV file to get started.")

if __name__ == "__main__":
        main()
