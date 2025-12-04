import pandas as pd
import os

def save_to_excel(data, filename="amazon_products.xlsx"):
    """
    Saves a list of dictionaries to an Excel file.
    
    Args:
        data (list): List of dictionaries containing product data.
        filename (str): Name of the output file.
    """
    if not data:
        print("No data to save.")
        return

    try:
        df = pd.DataFrame(data)
        
        # Ensure the directory exists
        directory = os.path.dirname(filename)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        if "Source" in df.columns:
            # Group by Source and write to Excel with titles
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                start_row = 0
                sources = df["Source"].unique()
                
                for source in sources:
                    source_df = df[df["Source"] == source]
                    
                    # Write the title using a trick: write a dataframe with one column and one row, no header
                    pd.DataFrame([f"Source: {source}"]).to_excel(writer, sheet_name='Products', startrow=start_row, startcol=0, index=False, header=False)
                    
                    # Write the data
                    source_df.to_excel(writer, sheet_name='Products', startrow=start_row + 1, index=False)
                    
                    start_row += len(source_df) + 3 # +1 for title, +1 for header, +1 for spacing
        else:
            df.to_excel(filename, index=False)
            
        print(f"Data successfully saved to {filename}")
    except Exception as e:
        print(f"Error saving data to Excel: {e}")
