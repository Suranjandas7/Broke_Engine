"""
Example client code demonstrating multi-format export from /get_history endpoint.

Shows how to consume Arrow, Parquet, MessagePack, CSV, and JSON formats.
"""

import requests
import pandas as pd
import pyarrow.feather as feather
import msgpack
from io import BytesIO, StringIO
import time

# Configuration
BASE_URL = "http://localhost:5010"
API_KEY = "test"
TICKER = "SBIN:NSE"
FROM_YEAR = 2024
TO_YEAR = 2024


def benchmark_format(format_name: str):
    """Fetch data in specified format and measure performance."""
    print(f"\n{'='*60}")
    print(f"Testing {format_name.upper()} format")
    print(f"{'='*60}")
    
    params = {
        'apikey': API_KEY,
        'ticker': TICKER,
        'from_year': FROM_YEAR,
        'to_year': TO_YEAR,
        'format': format_name
    }
    
    # Measure download time
    start = time.time()
    response = requests.get(f"{BASE_URL}/get_history", params=params)
    download_time = time.time() - start
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return
    
    # Measure parsing time
    parse_start = time.time()
    
    if format_name == 'json':
        data = response.json()
        df = pd.DataFrame(data['data'])
        metadata = {k: v for k, v in data.items() if k != 'data'}
    
    elif format_name == 'arrow':
        df = feather.read_feather(BytesIO(response.content))
        metadata = df.attrs
    
    elif format_name == 'parquet':
        df = pd.read_parquet(BytesIO(response.content))
        metadata = df.attrs
    
    elif format_name == 'msgpack':
        data = msgpack.unpackb(response.content)
        df = pd.DataFrame(data['data'])
        metadata = {k: v for k, v in data.items() if k != 'data'}
    
    elif format_name == 'csv':
        df = pd.read_csv(StringIO(response.text), comment='#')
        metadata = {}  # Metadata in CSV comments, not parsed here
    
    parse_time = time.time() - parse_start
    total_time = download_time + parse_time
    
    # Results
    response_size = len(response.content)
    print(f"Response size: {response_size:,} bytes ({response_size / 1024 / 1024:.2f} MB)")
    print(f"Download time: {download_time:.3f} seconds")
    print(f"Parse time: {parse_time:.3f} seconds")
    print(f"Total time: {total_time:.3f} seconds")
    print(f"Records: {len(df):,}")
    
    if metadata:
        print(f"\nMetadata:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
    
    print(f"\nDataFrame preview:")
    print(df.head())
    print(f"\nDataFrame info:")
    print(df.dtypes)
    
    return {
        'format': format_name,
        'size_bytes': response_size,
        'download_time': download_time,
        'parse_time': parse_time,
        'total_time': total_time,
        'records': len(df)
    }


def main():
    """Run benchmarks for all formats."""
    print("="*60)
    print("Multi-Format Export Benchmark")
    print(f"Ticker: {TICKER}, Years: {FROM_YEAR}-{TO_YEAR}")
    print("="*60)
    
    formats = ['json', 'csv', 'msgpack', 'parquet', 'arrow']
    results = []
    
    for fmt in formats:
        try:
            result = benchmark_format(fmt)
            if result:
                results.append(result)
            time.sleep(0.5)  # Small delay between requests
        except Exception as e:
            print(f"Error testing {fmt}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary comparison
    if results:
        print("\n" + "="*60)
        print("PERFORMANCE COMPARISON SUMMARY")
        print("="*60)
        
        # Use JSON as baseline
        json_result = next(r for r in results if r['format'] == 'json')
        json_size = json_result['size_bytes']
        json_time = json_result['total_time']
        
        print(f"\n{'Format':<12} {'Size':<15} {'Size %':<10} {'Time (s)':<12} {'Speedup':<10}")
        print("-" * 60)
        
        for r in results:
            size_pct = (r['size_bytes'] / json_size) * 100
            speedup = json_time / r['total_time'] if r['total_time'] > 0 else 0
            
            print(f"{r['format']:<12} "
                  f"{r['size_bytes']:>10,} B   "
                  f"{size_pct:>5.1f}%    "
                  f"{r['total_time']:>8.3f}    "
                  f"{speedup:>5.1f}x")


if __name__ == '__main__':
    main()
