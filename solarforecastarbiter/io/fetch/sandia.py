"""Collection of code for requesting and parsing Data from Sandia National
Laboratories.
"""
import logging


import pandas as pd
import requests

SANDIA_API_URL = "https://pv-dashboard.sandia.gov/api/v1.0/location/{location}/data/{data_type}/start/{start}/end/{end}/key/{api_key}" # NOQA
logger = logging.getLogger(__name__)


def request_sandia_data(location, data_type, start, end, api_key):
    """Makes a request to sandia with the provided parameters.

    Parameters
    ----------
    location: string
        Name of the Sandia location.
    data_type: string
        'system' or 'weather'
    api_key: string
        The Api key for accessing the Sandia API.
    start: datetime
        Beginning of the period for which to request data.
    end: datetime
        End of the period for which to request data.

    Returns
    -------
    DataFrame
        DataFrame parsed from the json response.
    """
    request_url = SANDIA_API_URL.format(
        location=location,
        start=start.strftime('%Y-%m-%d'),
        end=end.strftime('%Y-%m-%d'),
        data_type=data_type,
        api_key=api_key)
    r = requests.get(request_url)
    resp = r.json()
    if 'access' in resp and resp['access'] == 'denied':
        raise ValueError('Invalid Sandia API key')
    else:
        return pd.DataFrame(resp)


def fetch_sandia(location, api_key, start, end):
    """
    Requests and concatenates data from the Sandia API into a single dataframe.

    Parameters
    ----------
    location: string
        Name of the Sandia location.
    api_key: string
        The Api key for accessing the Sandia API.
    start: datetime
        Beginning of the period for which to request data.
    end: datetime
        End of the period for which to request data.

    Returns
    -------
    pandas.DataFrame
        With data from start to end. Index is a datetime-index NOT localized
        but in the timezone for the location
    """
    data_types = ['system', 'weather']
    dfs = []
    for data_type in data_types:
        df = request_sandia_data(location, data_type, start, end, api_key)
        if df.empty:
            continue
        df.index = pd.to_datetime(df['TmStamp'], unit='ms', utc=False)
        df = df.drop('TmStamp', axis=1)
        # Append the datatype to the end of AmbientTemp so we can differentiate
        # system from weather temperatures
        df = df.rename(columns={'AmbientTemp': f'AmbientTemp_{data_type}'})
        dfs.append(df)
    try:
        data = pd.concat(dfs, axis=1)
    except ValueError:
        # empty data
        return pd.DataFrame()
    return data
