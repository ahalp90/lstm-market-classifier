"""
Shared utilities for market data scraping.

Exchange-agnostic helpers for time/datetime conversions, file naming and saving, HTTP response interpretation.
"""

import datetime
import json
import logging
import os
import re
import warnings
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from pandas import DataFrame

from .constants import JSON_FILENAME_FORMAT, MAX_FILE_VERSIONS

logger = logging.getLogger(__name__)


# TIME CONVERSION UTILITIES
#******

def calendar_datetime_to_utc_and_unix(date_input: str,
                                      time_input: str | None = None,
                                      tz: ZoneInfo = ZoneInfo("UTC")) -> tuple[datetime.datetime, int]:
    """
    Convert calendar date/time to UTC datetime and Unix ms timestamp.

    Day starts from midnight in input timezone if no time provided.
    Handles dash separator errors in time_input.
    """
    date_formatted = datetime.date.fromisoformat(date_input)

    if time_input is not None:
        time_input = time_input.replace("-", ":")

    # Default midnight if no time provided
    time_formatted = datetime.time.fromisoformat(time_input) if time_input else datetime.time.min
    dt = datetime.datetime.combine(date_formatted, time_formatted, tzinfo=tz)

    dt_utc = dt.astimezone(datetime.timezone.utc)
    unix_timestamp = int(dt_utc.timestamp() * 1000)

    return dt_utc, unix_timestamp


def unix_ms_to_utc_datetime(unix_ms: int) -> datetime.datetime:
    """Convert unix milliseconds to UTC-aware datetime."""
    return datetime.datetime.fromtimestamp(unix_ms / 1000, tz=datetime.timezone.utc)


def unix_ms_to_filename_str(unix_ms: int) -> str:
    """Convert unix ms to filesystem-safe datetime string (colons replaced with dashes)"""
    dt = unix_ms_to_utc_datetime(unix_ms)
    return dt.isoformat(timespec='seconds').replace(':', '-')


def get_current_unix_ms() -> int:
    """Return current time as Unix timestamp in milliseconds."""
    return int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)


# FILE NAMING AND SAVING UTILITIES
#******

def create_timestamped_json_filepath(base_dir: str,
                                     exchange: str,
                                     symbol: str,
                                     data_type: str,
                                     interval: str,
                                     timestamps: tuple[int, int]) -> str:
    """
    Create a full filepath for timestamped JSON data.
    
    :param base_dir: Base directory for this data type (e.g., DIR_MARKET_DATA)
    :param exchange: Exchange name (e.g., "binance", "bybit")
    :param symbol: Trading pair symbol
    :param data_type: Data type (e.g., "kline", "open-interest")
    :param interval: Time interval string
    :param timestamps: Tuple of (first_timestamp_ms, last_timestamp_ms)
    :return: Full filepath string
    """
    # clean data_type for filename (open_interest to open-interest), so underscores don't break filename regex parser
    data_type_slug = data_type.replace("_", "-")

    folder_path = os.path.join(base_dir,
                               exchange,
                               symbol,
                               data_type,
                               interval)

    start_time_str = unix_ms_to_filename_str(timestamps[0])
    end_time_str = unix_ms_to_filename_str(timestamps[1])

    filename = JSON_FILENAME_FORMAT.format(
        exchange=exchange,
        symbol=symbol,
        data_type=data_type_slug,
        interval=interval,
        start_time_str=start_time_str,
        end_time_str=end_time_str
    )

    return os.path.join(folder_path, filename)


def save_json_data(data: list | dict,
                   filepath: str,
                   metadata: dict[str, Any] | None = None,
                   create_numbered_version_if_exists: bool = False) -> bool:
    """
    Save data to JSON file with optional metadata header.
    
    :param data: The data to save (typically a list of records)
    :param filepath: Full path to save the file
    :param metadata: Optional dict of metadata to include in the file
    :param create_numbered_version_if_exists: If True, create numbered version (_1, _2, etc.)
                                               instead of skipping when file exists
    :return: True if file was saved successfully, False if skipped
    :raises FileExistsError: If more than MAX_FILE_VERSIONS numbered versions exist
    """
    needs_versioning = False
    if os.path.exists(filepath):
        if not create_numbered_version_if_exists:
            logger.info("File %s already exists. Skipping save.", filepath)
            return False
        else:
            needs_versioning = True

    # Build output structure
    if metadata:
        output_data = {**metadata, "data": data}
    else:
        output_data = {"data": data}

    # Handle versioning if needed
    final_filepath = filepath
    if needs_versioning:
        filepath_base, _ = filepath.rsplit(".", 1)
        for i in range(1, MAX_FILE_VERSIONS + 1):
            final_filepath = f"{filepath_base}_{i}.json"
            if not os.path.exists(final_filepath):
                break
        else:
            raise FileExistsError(f"More than {MAX_FILE_VERSIONS} versions of {filepath} already exist.\n"
                                  f"File could not be saved.")

    # Create directory if needed
    dir_path = os.path.dirname(final_filepath)
    os.makedirs(dir_path, exist_ok=True)

    # Save file
    with open(final_filepath, 'w') as file:
        json.dump(output_data, file, indent=2)

    logger.info("Data saved to: %s", final_filepath)
    return True


# FILE LOADING HELPERS
#******

FILENAME_PATTERN = re.compile(
    r"^(?P<exchange>[^_]+)_"
    r"(?P<symbol>[^_]+)_"
    r"(?P<data_type>[^_]+)_"
    r"(?P<interval>[^_]+)_"
    r"(?P<start_time>.+)_to_"
    r"(?P<end_time>.+)\.json$"
)


def parse_market_data_filename(filename: str) -> dict[str, str]:
    """
    Parse market data filenames out to their components

    Expected format: {exchange}_{symbol}_{interval}_{start}_to_{end}.json

    :param filename: Filename to parse
    :return: Dict with keys: exchange, symbol, interval, start_time, end_time
    :raises ValueError: If filename doesn't match expected format
    """
    match = FILENAME_PATTERN.match(filename)
    if not match:
        raise ValueError(f"Filename doesn't match expected format: {filename}")
    return match.groupdict()


def build_market_data_filepath(base_dir: str, filename: str) -> str:
    """
    Build full filepath from base dir and filename.

    :param base_dir: Base directory for this data type (e.g., DIR_MARKET_DATA)
    :param filename: Filename matching format {exchange}_{symbol}_{interval}_{start}_to_{end}.json
    :return: Full filepath
    """
    parts = parse_market_data_filename(filename)
    return os.path.join(
        base_dir,
        parts["exchange"],
        parts["symbol"],
        parts["data_type"].replace("-", "_"),  # Convert back to underscore for folder name req
        parts["interval"],
        filename
    )


def load_json_file(filepath: str) -> tuple[list | dict, dict[str, str | int]]:
    """Load JSON market data file, returning (data, metadata) separated"""
    with open(filepath) as json_file:
        whole_json_dict: dict = json.load(json_file)

    metadata: dict[str, str | int] = {}
    for key, value in whole_json_dict.items():
        if key != "data":
            metadata[key] = value

    return whole_json_dict["data"], metadata

def find_duplicates_and_time_gaps(df: DataFrame,
                                  time_col: str,
                                  interval: int,
                                  show: str = 'all',
                                  df_name: str | None = None) -> tuple[DataFrame, DataFrame]:
    """
    Find duplicate rows and time gaps in a DataFrame.

    :param df: DataFrame to analyse
    :param time_col: Name of the timestamp column
    :param interval: Expected interval between records in milliseconds
    :param show: How much to log - 'head', 'tail', or 'all'
    :param df_name: Optional name for logging
    :return: Tuple of (duplicates_df, gaps_df)
    """
    show_options = {'head', 'tail', 'all'}
    if show not in show_options:
        warnings.warn(
            f'Arg for "show" must be one of {show_options}. If any duplicates or gaps, all will be shown.',
            stacklevel=2)

    df_name = df_name or "DataFrame"

    # Check for duplicate rows
    duplicates = df[df.duplicated(keep=False)]
    logger.info("Duplicate rows in %s: %d", df_name, len(duplicates))

    if len(duplicates) > 0:
        if show == 'head':
            logger.debug("Duplicates (head 10):\n%s", duplicates.head(10))
        elif show == 'tail':
            logger.debug("Duplicates (tail 10):\n%s", duplicates.tail(10))
        else:
            logger.debug("Duplicates:\n%s", duplicates)

    # Find gaps
    df_diff = df.sort_values(time_col).reset_index(drop=True)
    df_diff['time_diff'] = df_diff[time_col].astype(int).diff()
    # ignore the first row, which is necessarily NaN because it can't be compared
    # df_gaps = df_diff[(df_diff['time_diff'] != interval) & (df_diff['time_diff'].notna())].copy()
    df_gaps = df_diff[(df_diff['time_diff'] != interval)].copy()


    # Convert timestamps to readable dates to see when gaps occur
    df_gaps['date'] = pd.to_datetime(df_gaps[time_col], unit='ms')
    df_gaps['gap_minutes'] = df_gaps['time_diff'] / 60000
    df_gaps['candles_missing'] = df_gaps['time_diff'] / interval - 1 #

    if len(df_gaps) == 0:
        logger.info("%s gaps: None", df_name)
    else:
        logger.info("%s gaps: %d", df_name, len(df_gaps))
        gap_summary = df_gaps[['date', 'gap_minutes', 'candles_missing']]
        if show == 'head':
            logger.debug("Gaps (head 10):\n%s", gap_summary.head(10))
        elif show == 'tail':
            logger.debug("Gaps (tail 10):\n%s", gap_summary.tail(10))
        else:
            logger.debug("Gaps:\n%s", gap_summary)

    return duplicates, df_gaps


