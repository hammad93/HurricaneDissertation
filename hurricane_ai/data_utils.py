import datetime
from os import path
import pickle as pkl

import numpy as np

from sklearn.preprocessing import RobustScaler

from hurricane_ai import TRAIN_TEST_NPZ_FILE, is_source_modified, HURRICANE_SOURCE_FILE, SCALED_TRAIN_TEST_NPZ_FILE, \
    SCALER_FILE
from hurricane_ai.container.hurricane_data_container import HurricaneDataContainer


def subset_features(data, feature_idx: int) -> np.array:
    """
    Extracts a feature subset from data at the given position.
    :param data: Dataset containing all features.
    :param feature_idx: Index of feature to extract.
    :return: Array of subsetted feature values.
    """

    return np.array([[[features[feature_idx]] for features in y] for y in data], dtype=np.float64)


def build_scaled_ml_dataset(timesteps=1, remove_missing=True, train_test_data: dict = None) -> (dict, RobustScaler):
    """
    PURPOSE: Scale our data using the RobustScaler method from the sklearn library
    METHOD: Generate data using 1 timesteps and then remove the NaN or None types to use the scaler methods

    :param timesteps: Number of timesteps for the dataset (defaults to 1)
    :param remove_missing: Boolean indicating whether the algorithm will disregard missing values
    :param train_test_data: Unscaled training/testing dataset (optional)
    :return: 1) Scaled processed_data using RobustScaler
             2) RobustScaler object fit with appropriate data
    """

    # Load the scaled train/test data and the scaler if they exists and are not stale
    if path.exists(SCALED_TRAIN_TEST_NPZ_FILE) and path.exists(SCALER_FILE) and not is_source_modified(
            HURRICANE_SOURCE_FILE, SCALED_TRAIN_TEST_NPZ_FILE):
        # Load serialized scaled data
        data = np.load(SCALED_TRAIN_TEST_NPZ_FILE)
        scaled_data = {'x': data['x'], 'y': data['y']}

        # Load scaler
        with open(SCALER_FILE, 'rb') as in_file:
            feature_scaler = pkl.load(in_file)

        return scaled_data, feature_scaler

    # Get the training/testing dataset
    train_test_data = build_ml_dataset(timesteps, remove_missing) if train_test_data is None else train_test_data

    # Reshape training data to fit scaler
    x = np.reshape(train_test_data['x'], (train_test_data['x'].shape[0], -1))
    x = np.delete(x, np.where(np.isnan(x))[0], 0)

    # Create and fit scaler
    feature_scaler = RobustScaler()
    feature_scaler.fit(x)

    # Scale our data
    for index in range(len(train_test_data['x'])):
        # Scale our training dataset
        train_test_data['x'][index] = feature_scaler.transform(train_test_data['x'][index])
        # Scale our testing dataset
        train_test_data['y'][index] = feature_scaler.transform(train_test_data['y'][index])

    # Serialize the scaled data
    np.savez(SCALED_TRAIN_TEST_NPZ_FILE, x=train_test_data['x'], y=train_test_data['y'])

    # Serialize the feature scaler
    with open(SCALER_FILE, 'wb') as out_file:
        pkl.dump(feature_scaler, out_file)

    return train_test_data, feature_scaler


def build_ml_dataset(timesteps, remove_missing) -> dict:
    """
    PURPOSE: Build train/test dataset of the appropriate shape for input into machine learning models
    METHOD: Use a numpy array to shape into (samples, timesteps, features)

    :param timesteps: Number of timesteps for the dataset
    :param remove_missing: Boolean indicating whether the algorithm will disregard missing values
    :return: Numpy array of shape (samples, timesteps, 11) where 11 is the number of predictors in a hurricane object
    """

    # Load train/test data from serialized npz file if it exists and is not stale
    if path.exists(TRAIN_TEST_NPZ_FILE) and not is_source_modified(HURRICANE_SOURCE_FILE, TRAIN_TEST_NPZ_FILE):
        data = np.load(TRAIN_TEST_NPZ_FILE)
        return {'x': data['x'], 'y': data['y']}

    x = []
    y = []

    # Lag time in hours
    lag = 24

    # Defines the precision of all hurricane measurements
    precision = np.float64

    # Begin at the first (24 hour) lag with lag increments up to 120h inclusive
    times = [time * lag for time in
             range(1, (120 // lag) + 1)]

    # Get the full hurricane dataset
    hurricanes = HurricaneDataContainer()

    count = 0
    for hurricane in hurricanes:

        # Extract sequenced observations for the current hurricane
        result = _get_hurricane_observations(hurricane, timesteps, lag)

        # Skip to the next hurricane if there are no observations
        if result is None:
            continue

        # Extract only the values from the strom features using our specified precision
        hurricane_x = np.array(
            [[list(sample[1][0].values()) for sample in x] for x in result['x']],
            dtype=precision)
        hurricane_y = np.array(
            [[list(result['y'][time][index].values()) for time in times] for index in range(len(result['y'][lag]))],
            dtype=precision)

        # Disregard if algorithm requires no missing values
        if remove_missing:
            if (len(np.where(np.isnan(hurricane_x))[0]) > 0) or (len(np.where(np.isnan(hurricane_y))[0]) > 0):
                continue

        # Increment the number of feature-engineered hurricanes
        count += 1

        # Add to our results
        x.extend(hurricane_x)
        y.extend(hurricane_y)

    print("Feature engineered {}/{} hurricanes for {} timestep(s)".format(count, len(hurricanes), timesteps),
          end="\r")

    # Convert training and testing datasets to numpy arrays
    x, y = np.array(x), np.array(y)

    # Serialize train and test data
    np.savez(TRAIN_TEST_NPZ_FILE, x=x, y=y)

    return {'x': x, 'y': y}


def _get_hurricane_observations(storm: HurricaneDataContainer, timesteps=1, lag=24) -> dict:
    """
    PURPOSE: Create independent and dependent samples for a machine learning model based on the timesteps
    METHOD: Use the HURDAT2 database and a hurricane object as defined in hurricane-net for feature extraction

    :param storm: Hurricane object
    :param timesteps: Number of timesteps to calculate (default = 1)
    :param lag: Lag in hours for the dependent variables up to 5 days (default = 24)
    :return: Dictionary with independent (x) and dependent (y) values.
    """

    x = []
    # Create testing data structure with a dictionary
    times = [time * lag for time in
             range(1, (120 // lag) + 1)]  # Begin at lag hours with lag increments up to 120h inclusive
    y = dict([(time, []) for time in times])

    # Sort by entry time
    entries = [entry[1] for entry in sorted(storm.entries.items())]

    for index in range(len(entries)):
        if index < timesteps:  # Flag for insufficient initial time steps
            continue

        # If we're not including None values, check to see if there will be any
        if None in [storm.entries.get(entries[index]['entry_time'] +
                                      datetime.timedelta(hours=future)) for future in times]: break

        # Calculate time steps and their features for independent values
        sample = []
        for step in range(timesteps):
            # Training sample
            timestep = entries[index - step]
            previous = entries[index - step - 1]
            sample.append([timestep['entry_time']] + [[_extract_features(timestep, previous)]])
        x.append(sample)  # Add our constructed sample

        # Calculate time steps and their features for dependent values
        for future in times:
            timestep = storm.entries.get(entries[index]['entry_time'] + datetime.timedelta(hours=future))
            previous = storm.entries.get(entries[index]['entry_time'] + datetime.timedelta(hours=future - lag))

            if timestep and previous:
                y[future].append(_extract_features(timestep, previous))
            else:
                y[future].append(None)

    # Return output, if there is no output, return None.
    if len(x) is 0:
        return None
    else:
        return {'x': x, 'y': y}


def _extract_features(timestep, previous):
    """
    PURPOSE: Calculate the features for a machine learning model within the context of hurricane-net
    METHOD: Use the predictors and the calculation methodology defined in Knaff 2013

    Timestep format:
    timestep = {
      'lat' : float,
      'long' : float,
      'max-wind' : float,
      'entry-time' : datetime
    }

    :param timestep: Current dictionary of features in the hurricane object format
    :param previous: Previous timestep dictionary of features in the hurricane object format
    :return: Dictionary of features
    """

    features = {
        'lat': timestep['lat'],
        'long': timestep['long'],
        'max_wind': timestep['max_wind'],
        'delta_wind': (timestep['max_wind'] - previous['max_wind']) /  # Calculated from track (12h)
                      ((timestep['entry_time'] - previous['entry_time']).total_seconds() / 43200),
        'min_pressure': timestep['min_pressure'],
        'zonal_speed': (timestep['lat'] - previous['lat']) /  # Calculated from track (per hour)
                       ((timestep['entry_time'] - previous['entry_time']).total_seconds() / 3600),
        'meridonal_speed': (timestep['long'] - previous['long']) /  # Calculated from track (per hour)
                           ((timestep['entry_time'] - previous['entry_time']).total_seconds() / 3600),
        'year': timestep['entry_time'].year,
        'month': timestep['entry_time'].month,
        'day': timestep['entry_time'].day,
        'hour': timestep['entry_time'].hour,
    }

    return features
