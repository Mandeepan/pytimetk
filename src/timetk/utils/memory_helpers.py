import numpy as np
import pandas as pd

def reduce_memory_usage(df):
  """
  Iterate through all columns of a Pandas DataFrame and modify the dtypes to reduce memory usage.

  Parameters:
  -----------
  df: pandas.DataFrame
      Input dataframe to reduce memory usage.
  
  Returns:
  --------
  pandas.DataFrame
    Dataframe with reduced memory usage.

  """

  def _convert_boolean_to_int8(df,col):
    """
    Convert a boolean column to int8 to save memory.
    """
    if df[col].dtype != bool:
      return df
    df[col] = df[col].astype(np.int8)
    return df
  
  # Iterate over each column in the dataframe
  for col in df.columns:
    # Get the current column dtype
    col_type = df[col].dtype

    # Check if column is boolean
    if col_type == bool:
      # If the column is boolean, convert it to int8 to save memory
      df = _convert_boolean_to_int8(df, col)

    # Check if the column is not an object (i.e., it's not a numeric column)
    elif col_type != object:
      # Get the minimum and maximum values of the current column
      c_min = df[col].min()
      c_max = df[col].max()

      # Check if the column is an integer type
      if str(col_type)[:3] == 'int':
        # Iterate over possible integer types and find the smallest type that can accomodate the column values
        for dtype in [np.int8, np.uint8, np.int16, np.uint16, np.int32, np.uint32, np.int64, np.uint64]:
          if c_min > np.iinfo(dtype).min and c_max < np.iinfo(dtype).max:
            df[col] = df[col].astype(dtype)
            break

      # Check if the column is a float type
      elif str(col_type)[:5] == 'float':
      # Iterate over possible float types and find the smallest type that can accomodate the column values
        for dtype in [np.float16, np.float32, np.float64]:
          if c_min > np.finfo(dtype).min and c_max < np.finfo(dtype).max:
            df[col] = df[col].astype(dtype)
            break

    # If the column is an object type, convert it to categorical type to save memory
    else:
      df[col] = df[col].astype('category')
    
  # Return the memory optimized
  return df
