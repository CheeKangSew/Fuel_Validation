# -*- coding: utf-8 -*-
"""
Created on Mon Aug 12 09:43:58 2024

@author: User
"""

import streamlit as st
import pandas as pd
import logging
from io import BytesIO

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to validate fuel data
def validate_fuel_data(df, validation_df):
    try:
        df = df.dropna(subset=['Pump Date'])
        df.columns = df.columns.str.strip()  
        
        df = df.rename(columns={'Truck': 'Truck Odometer', 'Actual': 'Actual Qty'})

        df['Pump Date'] = pd.to_datetime(df['Pump Date']).dt.strftime('%d-%m-%Y')
        validation_df['Delivery Date'] = pd.to_datetime(validation_df['Delivery Date']).dt.strftime('%d-%m-%Y')
        
        df['Truck No.'] = df['Truck No.'].astype(str).str.strip()
        validation_df['Vehicle License Number'] = validation_df['Vehicle License Number'].astype(str).str.strip()
        
        df['Trace No'] = df['Trace No'].astype(str).str.strip()
        validation_df['Receipt Number'] = validation_df['Receipt Number'].astype(str).str.strip()

        merged_df = pd.merge(df, validation_df, left_on=['Truck No.', 'Pump Date'], 
                             right_on=['Vehicle License Number', 'Delivery Date'], how='left', suffixes=('', '_Validation'))
        
        merged_df['Match Found'] = merged_df['Delivery Date'].notna() & merged_df['Vehicle License Number'].notna()

        merged_df['Amount Match'] = merged_df.apply(lambda x: 'Yes' if x['Amount'] == x['Net Amount in Customer currency'] else 'No', axis=1)

        mismatched_rows = merged_df[~merged_df['Match Found']]
        if not mismatched_rows.empty:
            logging.warning("Rows with no matching records:")
            logging.warning(mismatched_rows.to_string())

        return merged_df

    except Exception as e:
        logging.error(f"An error occurred during validation: {e}")
        st.error(f"An error occurred: {e}")
        return pd.DataFrame()

# Function to calculate fuel consumption
def calculate_fuel_consumption(df):
    try:
        df = df.dropna(how='all')
        df.columns = df.columns.str.strip()
        
        df['Pump Date'] = pd.to_datetime(df['Pump Date']).dt.strftime('%d-%m-%Y')
        df['Log Date'] = pd.to_datetime(df['Log Date']).dt.strftime('%d-%m-%Y')
        
        df = df.rename(columns={'Truck': 'Truck Odometer', 'Actual': 'Actual Qty'})
        
        df = df.sort_values(by=['Truck No.', 'Pump Date'])
        
        df['OdometerDiff'] = df.groupby('Truck No.')['Truck Odometer'].diff()
        
        df['RollingOdometerDiff'] = df.groupby('Truck No.')['OdometerDiff'].rolling(window=2, min_periods=1).sum().reset_index(level=0, drop=True)
        
        df['RollingActualQty'] = df.groupby('Truck No.')['Actual Qty'].rolling(window=2, min_periods=1).sum().reset_index(level=0, drop=True)
        
        df['Fuel Efficiency'] = df['RollingOdometerDiff'] / df['RollingActualQty']
        
        return df
    
    except Exception as e:
        logging.error(f"An error occurred during fuel consumption calculation: {e}")
        st.error(f"An error occurred: {e}")
        return pd.DataFrame()

# Streamlit application
def main():
    st.title("Fuel Data Validation and Consumption Tool")

    st.write("""
    This tool allows you to validate fuel data by comparing it with a validation file,
    and calculate fuel consumption for the given data. Upload your files and click 'Process' to get started.
    """)

    # File uploaders for the main data and validation data
    uploaded_file = st.file_uploader("Upload your Diesel Log Excel file", type="xlsx")
    validation_file = st.file_uploader("Upload your Shell Statement Excel file", type="xlsx")

    if uploaded_file:
        try:
            fuel_data = pd.read_excel(uploaded_file, skiprows=[0, 1, 2, 3, 4, 6, 7, 8, 9])
            
            # Remove specified columns
            fuel_data = fuel_data.drop(columns=['Unnamed: 13', 'Pump Skid Tank'], errors='ignore')             

            if validation_file:
                validation_data = pd.read_excel(validation_file)
                validated_df = validate_fuel_data(fuel_data, validation_data)

                if not validated_df.empty:
                    st.success("Validation complete! See the results below.")
                    st.write(validated_df)
                    
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        validated_df.to_excel(writer, index=False, sheet_name='Validated Data')
                    st.download_button(
                        label="Download Validated Data",
                        data=buffer,
                        file_name="Validated_Fuel_Data.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.warning("Validation complete, but no matches were found.")
            
            # Calculate fuel consumption
            fuel_consumption_df = calculate_fuel_consumption(fuel_data)
            st.success("Fuel consumption calculation complete! See the results below.")
            st.write(fuel_consumption_df)

            buffer_consumption = BytesIO()
            with pd.ExcelWriter(buffer_consumption, engine='openpyxl') as writer:
                fuel_consumption_df.to_excel(writer, index=False, sheet_name='Fuel Consumption Data')
            st.download_button(
                label="Download Fuel Consumption Data",
                data=buffer_consumption,
                file_name="Fuel_Consumption_Data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"An error occurred while processing the files: {e}")

if __name__ == "__main__":
    main()
