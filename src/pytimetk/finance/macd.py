import pandas as pd
import polars as pl
import pandas_flavor as pf
from typing import Union

from pytimetk.utils.checks import check_dataframe_or_groupby, check_date_column, check_value_column
from pytimetk.utils.memory_helpers import reduce_memory_usage


@pf.register_dataframe_method
def augment_macd(
    data: Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy],
    date_column: str,
    close_column: str,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    reduce_memory: bool = False,
    engine: str = 'pandas'
) -> pd.DataFrame:
    """
    Calculate MACD for a given financial instrument using either pandas or polars engine.

    Parameters
    ----------
    data : Union[pd.DataFrame, pd.core.groupby.generic.DataFrameGroupBy]
        Pandas DataFrame or GroupBy object containing financial data.
    date_column : str
        Name of the column containing date information.
    close_column : str
        Name of the column containing closing price data.
    fast_period : int, optional
        Number of periods for the fast EMA in MACD calculation.
    slow_period : int, optional
        Number of periods for the slow EMA in MACD calculation.
    signal_period : int, optional
        Number of periods for the signal line EMA in MACD calculation.
    reduce_memory : bool, optional
        Whether to reduce memory usage of the data before performing the calculation.
    engine : str, optional
        Computation engine to use ('pandas' or 'polars').

    Returns
    -------
    pd.DataFrame
        DataFrame with MACD line, signal line, and MACD histogram added.
        
    Examples
    --------
    
    ``` {python}
    import pandas as pd
    import pytimetk as tk

    df = tk.load_dataset("stocks_daily", parse_dates = ['date'])
    
    df
    ```
    
    ``` {python}
    # MACD pandas engine
    df_macd = (
        df
            .groupby('symbol')
            .augment_macd(
                date_column = 'date', 
                close_column='close', 
                fast_period=12, 
                slow_period=26, 
                signal_period=9, 
                engine = "pandas"
            )
    )
    
    df_macd.glimpse()
    ```
    
    ``` {python}
    # MACD polars engine
    df_macd = (
        df
            .groupby('symbol')
            .augment_macd(
                date_column = 'date', 
                close_column='close', 
                fast_period=12, 
                slow_period=26, 
                signal_period=9, 
                engine = "pandas"
            )
    )
    
    df_macd.glimpse()
    ```
    
    """

    check_dataframe_or_groupby(data)
    check_value_column(data, close_column)
    check_date_column(data, date_column)

    if reduce_memory:
        data = reduce_memory_usage(data)

    if engine == 'pandas':
        ret = _augment_macd_pandas(data, date_column, close_column, fast_period, slow_period, signal_period)
    elif engine == 'polars':
        ret = _augment_macd_polars(data, date_column, close_column, fast_period, slow_period, signal_period)
    else:
        raise ValueError("Invalid engine. Use 'pandas' or 'polars'.")

    if reduce_memory:
        ret = reduce_memory_usage(ret)

    return ret

# Monkey patch the method to pandas groupby objects
pd.core.groupby.generic.DataFrameGroupBy.augment_macd = augment_macd

def _augment_macd_pandas(data, date_column, close_column, fast_period, slow_period, signal_period):
    """
    Internal function to calculate MACD using Pandas.
    """
    if isinstance(data, pd.core.groupby.generic.DataFrameGroupBy):
        # If data is a GroupBy object, apply MACD calculation for each group
        df = data.apply(lambda x: _calculate_macd_pandas(x, close_column, fast_period, slow_period, signal_period))
    elif isinstance(data, pd.DataFrame):
        # If data is a DataFrame, apply MACD calculation directly
        df = data.copy().sort_values(by=date_column)
        df = _calculate_macd_pandas(df, close_column, fast_period, slow_period, signal_period)
    else:
        raise ValueError("data must be a pandas DataFrame or a pandas GroupBy object")

    return df

def _calculate_macd_pandas(df, close_column, fast_period, slow_period, signal_period):
    """
    Calculate MACD, Signal Line, and MACD Histogram for a DataFrame.
    """
    # Calculate Fast and Slow EMAs
    ema_fast = df[close_column].ewm(span=fast_period, adjust=False, min_periods = 0).mean()
    ema_slow = df[close_column].ewm(span=slow_period, adjust=False, min_periods = 0).mean()

    # Calculate MACD Line
    macd_line = ema_fast - ema_slow

    # Calculate Signal Line
    signal_line = macd_line.ewm(span=signal_period, adjust=False, min_periods = 0).mean()

    # Calculate MACD Histogram
    macd_histogram = macd_line - signal_line

    # Add columns
    df[f'{close_column}_macd_line_{fast_period}_{slow_period}_{signal_period}'] = macd_line
    df[f'{close_column}_signal_line_{fast_period}_{slow_period}_{signal_period}'] = signal_line
    df[f'{close_column}_macd_histogram_{fast_period}_{slow_period}_{signal_period}'] = macd_histogram

    return df

def _augment_macd_polars(data, date_column, close_column, fast_period, slow_period, signal_period):
    """
    Internal function to calculate MACD using Polars.
    """
    # Convert to Polars DataFrame if input is a pandas DataFrame or GroupBy object
    if isinstance(data, pd.core.groupby.generic.DataFrameGroupBy):
        # Data is a GroupBy object, use apply to get a DataFrame
        group_names = data.grouper.names
        pandas_df = data.obj
        pl_df = pl.from_pandas(pandas_df)
    elif isinstance(data, pd.DataFrame):
        pl_df = pl.from_pandas(data.copy())
    else:
        raise ValueError("data must be a pandas DataFrame, pandas GroupBy object, or a Polars DataFrame")

    # Define the function to calculate MACD for a single DataFrame
    def calculate_macd_single(pl_df):
        # Calculate Fast and Slow EMAs
        fast_ema = pl_df[close_column].ewm_mean(span=fast_period, adjust=False, min_periods=0)
        slow_ema = pl_df[close_column].ewm_mean(span=slow_period, adjust=False, min_periods=0)

        # Calculate MACD Line
        macd_line = fast_ema - slow_ema

        # Calculate Signal Line
        signal_line = macd_line.ewm_mean(span=signal_period, adjust=False, min_periods=0)

        # Calculate MACD Histogram
        macd_histogram = macd_line - signal_line

        return pl_df.with_columns([
            macd_line.alias(
                f'{close_column}_macd_line_{fast_period}_{slow_period}_{signal_period}'
            ),
            signal_line.alias(
                f'{close_column}_signal_line_{fast_period}_{slow_period}_{signal_period}'
            ),
            macd_histogram.alias(
                f'{close_column}_macd_histogram_{fast_period}_{slow_period}_{signal_period}'
            )
        ])

    # Apply the calculation to each group if data is grouped, otherwise apply directly
    if 'groupby' in str(type(data)):
        result_df = pl_df.groupby(
            group_names, maintain_order=True
        ).apply(calculate_macd_single).to_pandas()
        
    else:
        result_df = calculate_macd_single(pl_df).to_pandas()
        result_df = result_df.sort_values(by=date_column)

    return result_df


