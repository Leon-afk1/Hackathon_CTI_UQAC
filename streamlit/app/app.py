import streamlit as st
import pandas as pd
import numpy as np

# Page config
st.set_page_config(page_title="Test Streamlit", layout="wide")

# Title
st.title("🚀 Streamlit Test App")

# Simple text
st.write("If you see this, Streamlit is running correctly inside Docker!")

# Interactive slider
num_points = st.slider("Select number of data points", min_value=10, max_value=100, value=50)

# Generate sample data
data = pd.DataFrame({
    "x": np.arange(num_points),
    "y": np.random.randn(num_points).cumsum()
})

# Show table
st.subheader("Sample Data")
st.dataframe(data)

# Show chart
st.subheader("Line Chart")
st.line_chart(data.set_index("x")["y"])
