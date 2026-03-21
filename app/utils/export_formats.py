"""
Export format utilities for historical data.

Provides optimized serialization formats for large datasets:
- Arrow: Zero-copy binary format (10-100x faster than JSON)
- Parquet: Compressed columnar format (80-95% smaller than JSON)
- MessagePack: Binary JSON (2-5x faster than JSON)
- CSV: Universal text format (40-60% smaller than JSON)
"""

import io
import csv
from typing import List, Dict, Any
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.feather as feather
import msgpack


def data_to_dataframe(data: List[Dict], metadata: Dict[str, Any]) -> pd.DataFrame:
    """
    Convert list of OHLCV dictionaries to pandas DataFrame.
    
    Args:
        data: List of dicts with keys: date, open, high, low, close, volume
        metadata: Metadata dict (ticker, exchange, date/year ranges, etc.)
    
    Returns:
        DataFrame with proper types and metadata attributes
    """
    if not data:
        # Return empty DataFrame with correct schema
        df = pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
    else:
        df = pd.DataFrame(data)
    
    # Set proper data types
    df['date'] = pd.to_datetime(df['date'])
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].astype('float64')
    df['volume'] = df['volume'].astype('int64')
    
    # Attach metadata as attributes (for Arrow/Parquet)
    df.attrs.update(metadata)
    
    return df


def export_to_arrow(data: List[Dict], metadata: Dict[str, Any]) -> bytes:
    """
    Export data to Apache Arrow IPC (Feather V2) format.
    
    Best for: API-to-API communication, zero-copy reads, maximum speed
    Performance: ~10-100x faster deserialization than JSON
    
    Args:
        data: List of OHLCV dictionaries
        metadata: Request metadata (ticker, exchange, etc.)
    
    Returns:
        Arrow IPC binary data
    """
    df = data_to_dataframe(data, metadata)
    
    # Convert to Arrow Table
    table = pa.Table.from_pandas(df)
    
    # Add metadata to schema
    metadata_bytes = {k.encode(): str(v).encode() for k, v in metadata.items()}
    table = table.replace_schema_metadata(metadata_bytes)
    
    # Serialize to Arrow IPC format (Feather V2)
    sink = pa.BufferOutputStream()
    feather.write_feather(table, sink, compression='lz4')
    
    return sink.getvalue().to_pybytes()


def export_to_parquet(data: List[Dict], metadata: Dict[str, Any]) -> bytes:
    """
    Export data to Apache Parquet format.
    
    Best for: Maximum compression, archival storage, analytics workflows
    Performance: ~5-10x faster than JSON, 80-95% smaller
    
    Args:
        data: List of OHLCV dictionaries
        metadata: Request metadata (ticker, exchange, etc.)
    
    Returns:
        Parquet binary data
    """
    df = data_to_dataframe(data, metadata)
    
    # Convert to Arrow Table
    table = pa.Table.from_pandas(df)
    
    # Add metadata to schema
    metadata_bytes = {k.encode(): str(v).encode() for k, v in metadata.items()}
    table = table.replace_schema_metadata(metadata_bytes)
    
    # Serialize to Parquet with Snappy compression
    sink = pa.BufferOutputStream()
    pq.write_table(
        table, 
        sink, 
        compression='snappy',
        use_dictionary=True,
        write_statistics=True
    )
    
    return sink.getvalue().to_pybytes()


def export_to_msgpack(data: List[Dict], metadata: Dict[str, Any]) -> bytes:
    """
    Export data to MessagePack format.
    
    Best for: Binary JSON alternative, broad compatibility
    Performance: ~2-5x faster than JSON, 30-50% smaller
    
    Args:
        data: List of OHLCV dictionaries
        metadata: Request metadata (ticker, exchange, etc.)
    
    Returns:
        MessagePack binary data
    """
    payload = {
        **metadata,
        'data': data
    }
    
    return msgpack.packb(payload, use_bin_type=True)


def export_to_csv(data: List[Dict], metadata: Dict[str, Any]) -> str:
    """
    Export data to CSV format.
    
    Best for: Excel, universal compatibility, simple parsing
    Performance: ~2-3x faster than JSON, 40-60% smaller
    
    Args:
        data: List of OHLCV dictionaries
        metadata: Request metadata (ticker, exchange, etc.)
    
    Returns:
        CSV string with metadata in header comments
    """
    output = io.StringIO()
    
    # Write metadata as comments
    for key, value in metadata.items():
        output.write(f"# {key}: {value}\n")
    
    if not data:
        # Just headers if no data
        output.write("date,open,high,low,close,volume\n")
        return output.getvalue()
    
    # Write CSV data
    writer = csv.DictWriter(
        output, 
        fieldnames=['date', 'open', 'high', 'low', 'close', 'volume'],
        lineterminator='\n'
    )
    writer.writeheader()
    writer.writerows(data)
    
    return output.getvalue()


def get_content_type(format: str) -> str:
    """Get HTTP Content-Type header for a given format."""
    content_types = {
        'json': 'application/json',
        'arrow': 'application/vnd.apache.arrow.file',
        'parquet': 'application/vnd.apache.parquet',
        'msgpack': 'application/msgpack',
        'csv': 'text/csv'
    }
    return content_types.get(format, 'application/octet-stream')


def get_file_extension(format: str) -> str:
    """Get file extension for a given format."""
    extensions = {
        'json': 'json',
        'arrow': 'arrow',
        'parquet': 'parquet',
        'msgpack': 'msgpack',
        'csv': 'csv'
    }
    return extensions.get(format, 'bin')
