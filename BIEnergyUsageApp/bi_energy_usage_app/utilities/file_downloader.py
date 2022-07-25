import requests


def download_file(url: str, local_file_path: str, chunk_size: int = 262144):
    """
    Download a file from the internet to the specified file path.

    Data is streamed - i.e. large files are not downloaded into memory but rather read/written in chunks to reduce
    memory consumption.

    Parameters
    ----------
    url : str
        Full URL of file to download.
    local_file_path : str
        Path to save downloaded file.
    chunk_size : int
        The size of the chunk.  Leave as default value under most circumstances.

    Returns
    -------
    None
        No return value
    """
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_file_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                f.write(chunk)
